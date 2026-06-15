import os
import uuid
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required

from backend.extensions import db
from backend.models.activity_log import ActivityLog
from backend.models.ticket import ClipboardItem, Ticket
from backend.services.alerting import send_alert
from backend.services.monitoring import get_full_status
from backend.services.stream_manager import stream_manager
from backend.services.two_factor import generate_secret, provisioning_uri, verify_totp

admin_features = Blueprint('admin_features', __name__, url_prefix='/api')


def _data():
    return request.get_json(silent=True) or request.form.to_dict()


def _admin_required():
    return current_user.is_authenticated and current_user.has_role('Admin')


def _manager_required():
    return current_user.is_authenticated and current_user.has_role('Admin', 'Manager')


@admin_features.route('/2fa/setup', methods=['POST'])
@login_required
def setup_2fa():
    secret = current_user.two_factor_secret or generate_secret()
    current_user.two_factor_secret = secret
    db.session.commit()
    issuer = current_app.config.get('TWO_FACTOR_ISSUER', 'LR Remote Access')
    ActivityLog.log(current_user.id, '2fa_setup_started', 'auth', ip_address=request.remote_addr)
    return jsonify({'success': True, 'secret': secret, 'provisioning_uri': provisioning_uri(current_user.username, issuer, secret)})


@admin_features.route('/2fa/enable', methods=['POST'])
@login_required
def enable_2fa():
    token = _data().get('token')
    if not verify_totp(current_user.two_factor_secret, token):
        return jsonify({'success': False, 'error': 'Invalid 2FA code'}), 400
    current_user.two_factor_enabled = True
    db.session.commit()
    ActivityLog.log(current_user.id, '2fa_enabled', 'auth', ip_address=request.remote_addr)
    return jsonify({'success': True, 'message': 'Two-factor authentication enabled'})


@admin_features.route('/2fa/disable', methods=['POST'])
@login_required
def disable_2fa():
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    db.session.commit()
    ActivityLog.log(current_user.id, '2fa_disabled', 'auth', ip_address=request.remote_addr)
    return jsonify({'success': True, 'message': 'Two-factor authentication disabled'})


@admin_features.route('/tickets', methods=['GET', 'POST'])
@login_required
def tickets():
    if request.method == 'GET':
        query = Ticket.query
        if not _manager_required():
            query = query.filter_by(created_by=current_user.id)
        status = request.args.get('status')
        if status and status != 'all':
            query = query.filter_by(status=status)
        rows = query.order_by(Ticket.updated_at.desc()).limit(200).all()
        return jsonify({'success': True, 'tickets': [ticket.to_dict() for ticket in rows]})

    payload = _data()
    title = (payload.get('title') or '').strip()
    if not title:
        return jsonify({'success': False, 'error': 'Ticket title is required'}), 400
    ticket = Ticket(
        title=title,
        description=payload.get('description') or '',
        priority=payload.get('priority') or 'normal',
        created_by=current_user.id,
        assigned_to=payload.get('assigned_to') or None,
    )
    db.session.add(ticket)
    db.session.commit()
    ActivityLog.log(current_user.id, f'ticket_created #{ticket.id}', 'ticket', ip_address=request.remote_addr)
    return jsonify({'success': True, 'message': 'Ticket created', 'ticket': ticket.to_dict()}), 201


@admin_features.route('/tickets/<int:ticket_id>', methods=['PATCH', 'POST'])
@login_required
def update_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'success': False, 'error': 'Ticket not found'}), 404
    if not _manager_required() and ticket.created_by != current_user.id:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403

    payload = _data()
    for field in ('title', 'description', 'priority', 'status'):
        if field in payload:
            setattr(ticket, field, payload[field])
    if 'assigned_to' in payload and _manager_required():
        ticket.assigned_to = payload.get('assigned_to') or None
    if ticket.status == 'closed' and not ticket.closed_at:
        ticket.closed_at = datetime.utcnow()
    db.session.commit()
    ActivityLog.log(current_user.id, f'ticket_updated #{ticket.id}', 'ticket', ip_address=request.remote_addr)
    return jsonify({'success': True, 'ticket': ticket.to_dict()})


@admin_features.route('/clipboard', methods=['GET', 'POST'])
@login_required
def clipboard():
    if request.method == 'GET':
        session_id = request.args.get('session_id', type=int)
        query = ClipboardItem.query.filter_by(user_id=current_user.id)
        if session_id:
            query = query.filter_by(session_id=session_id)
        items = query.order_by(ClipboardItem.created_at.desc()).limit(20).all()
        return jsonify({'success': True, 'items': [item.to_dict() for item in items]})

    payload = _data()
    content = payload.get('content') or ''
    if not content:
        return jsonify({'success': False, 'error': 'Clipboard content is required'}), 400
    item = ClipboardItem(
        user_id=current_user.id,
        session_id=payload.get('session_id') or None,
        direction=payload.get('direction') or 'web_to_remote',
        content=content[:200000],
    )
    db.session.add(item)
    db.session.commit()
    ActivityLog.log(current_user.id, 'clipboard_synced', 'clipboard', session_id=item.session_id, ip_address=request.remote_addr)
    return jsonify({'success': True, 'item': item.to_dict()}), 201


@admin_features.route('/transfers', methods=['GET', 'POST'])
@login_required
def transfers():
    transfer_dir = _transfer_dir()
    if request.method == 'GET':
        files = []
        for name in sorted(os.listdir(transfer_dir), reverse=True)[:100]:
            path = os.path.join(transfer_dir, name)
            if os.path.isfile(path):
                files.append({'name': name, 'size': os.path.getsize(path), 'url': f'/api/transfers/{name}'})
        return jsonify({'success': True, 'files': files})

    uploaded = request.files.get('file')
    if not uploaded:
        return jsonify({'success': False, 'error': 'file is required'}), 400
    safe_name = os.path.basename(uploaded.filename or 'upload.bin')
    stored_name = f'{datetime.utcnow().strftime("%Y%m%d%H%M%S")}-{uuid.uuid4().hex[:8]}-{safe_name}'
    path = os.path.join(transfer_dir, stored_name)
    uploaded.save(path)
    ActivityLog.log(current_user.id, f'file_uploaded {safe_name}', 'file_transfer', ip_address=request.remote_addr)
    return jsonify({'success': True, 'file': {'name': stored_name, 'size': os.path.getsize(path), 'url': f'/api/transfers/{stored_name}'}}), 201


@admin_features.route('/transfers/<path:name>', methods=['GET'])
@login_required
def download_transfer(name):
    path = os.path.join(_transfer_dir(), os.path.basename(name))
    if not os.path.isfile(path):
        return jsonify({'success': False, 'error': 'File not found'}), 404
    ActivityLog.log(current_user.id, f'file_downloaded {os.path.basename(path)}', 'file_transfer', ip_address=request.remote_addr)
    return send_file(path, as_attachment=True)


@admin_features.route('/recordings', methods=['GET'])
@login_required
def recordings():
    if not _manager_required():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    return jsonify({'success': True, 'recordings': stream_manager.recordings()})


@admin_features.route('/recordings/<agent_id>/start', methods=['POST'])
@login_required
def start_recording(agent_id):
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    result = stream_manager.start_recording(agent_id, _recording_dir(), current_user.id)
    ActivityLog.log(current_user.id, f'recording_started {agent_id}', 'recording', ip_address=request.remote_addr)
    return jsonify({'success': True, 'recording': result})


@admin_features.route('/recordings/<agent_id>/stop', methods=['POST'])
@login_required
def stop_recording(agent_id):
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    result = stream_manager.stop_recording(agent_id)
    ActivityLog.log(current_user.id, f'recording_stopped {agent_id}', 'recording', ip_address=request.remote_addr)
    return jsonify({'success': True, 'recording': result})


@admin_features.route('/monitoring', methods=['GET'])
@login_required
def monitoring():
    if not _manager_required():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    return jsonify({'success': True, **get_full_status()})


@admin_features.route('/alerts/test', methods=['POST'])
@login_required
def test_alert():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    payload = _data()
    subject = payload.get('subject') or 'LR Remote Access test alert'
    message = payload.get('message') or 'Alerting is configured.'
    results = send_alert(subject, message, payload.get('severity') or 'info')
    ActivityLog.log(current_user.id, 'alert_test_sent', 'alert', ip_address=request.remote_addr)
    return jsonify({'success': any(item.get('success') for item in results), 'results': results})


@admin_features.route('/agents/install-script', methods=['GET'])
@login_required
def agent_install_script():
    if not _admin_required():
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    server_url = request.args.get('server_url') or request.host_url.rstrip('/')
    files = 'agent.py screen_agent.py system_info.py keyboard_control.py mouse_control.py'
    script = f"""#!/usr/bin/env bash
set -e
mkdir -p lr-agent-src
python3 -m venv lr-agent-venv
./lr-agent-venv/bin/pip install python-socketio requests psutil mss opencv-python-headless numpy pyautogui
for file in {files}; do
  curl -fsSL {server_url}/api/agents/source/$file -o lr-agent-src/$file
done
LIVEPANEL_SERVER_URL={server_url} ./lr-agent-venv/bin/python lr-agent-src/agent.py
"""
    return jsonify({'success': True, 'server_url': server_url, 'linux_script': script})


@admin_features.route('/agents/source/<path:name>', methods=['GET'])
def download_agent_source(name):
    allowed = {'agent.py', 'screen_agent.py', 'system_info.py', 'keyboard_control.py', 'mouse_control.py'}
    if name not in allowed:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return send_file(os.path.join(root, 'agent', name), as_attachment=True, download_name=name)


def _transfer_dir():
    path = os.path.join(current_app.instance_path, 'transfers')
    os.makedirs(path, exist_ok=True)
    return path


def _recording_dir():
    path = os.path.join(current_app.instance_path, 'recordings')
    os.makedirs(path, exist_ok=True)
    return path
