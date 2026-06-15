from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from backend.models.activity_log import ActivityLog

logs = Blueprint('logs', __name__)


@logs.route('/logs', methods=['GET'])
@login_required
def get_logs():
    if not current_user.has_role('Admin', 'Manager'):
        return jsonify({'message': 'Forbidden'}), 403
    data = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return jsonify([
        {
            'user_id': log.user_id,
            'action': log.action,
            'category': log.category,
            'server_id': log.server_id,
            'session_id': log.session_id,
            'ip_address': log.ip_address,
            'timestamp': log.timestamp.isoformat() if log.timestamp else None,
            'time': log.created_at.isoformat() if log.created_at else None,
        }
        for log in data
    ])
