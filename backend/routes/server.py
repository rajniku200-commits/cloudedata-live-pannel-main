from flask import Blueprint, request, jsonify
from flask_login import login_required
from backend.models.server import Server
from backend.services.ssh_manager import connect_ssh

server = Blueprint('server', __name__)


@server.route('/add-server', methods=['POST'])
@login_required
def add_server():
    payload = request.get_json(silent=True) or request.form.to_dict()
    if not payload:
        return jsonify({'message': 'Request body is empty'}), 400

    required_fields = ['name', 'host', 'username', 'port', 'password']
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({'message': 'Missing required fields', 'missing': missing_fields}), 400

    try:
        port = int(payload.get('port'))
    except (TypeError, ValueError):
        return jsonify({'message': 'Port must be an integer'}), 400

    new_server = Server(
        name=payload.get('name'),
        host=payload.get('host'),
        username=payload.get('username'),
        port=port,
        password=payload.get('password')
    ).save()
    return jsonify({'message': 'Server added successfully', 'id': new_server.id}), 201


@server.route('/servers')
@login_required
def get_servers():
    all_servers = Server.find_all()
    return jsonify([{
        'id': server.id,
        'name': server.name,
        'host': server.host,
        'username': server.username,
        'port': server.port,
    } for server in all_servers])


@server.route('/servers/<id>')
@login_required
def get_server(id):
    server_obj = Server.get_by_id(id)
    if not server_obj:
        return jsonify({'message': 'Server not found'}), 404
    return jsonify({
        'id': server_obj.id,
        'name': server_obj.name,
        'host': server_obj.host,
        'username': server_obj.username,
        'port': server_obj.port,
    })


@server.route('/delete-server/<id>', methods=['POST', 'DELETE'])
@login_required
def delete_server(id):
    server_obj = Server.get_by_id(id)
    if not server_obj:
        return jsonify({'message': 'Server not found'}), 404
    server_obj.delete()
    return jsonify({'message': 'Server deleted successfully'})


@server.route('/connect-server/<id>', methods=['POST'])
@login_required
def connect_server(id):
    server_obj = Server.get_by_id(id)
    if not server_obj:
        return jsonify({'message': 'Server not found'}), 404
    payload = request.get_json(silent=True) or request.form.to_dict()
    if not payload or not payload.get('password'):
        return jsonify({'message': 'Password required'}), 400
    password = payload.get('password')

    ssh, error = connect_ssh(server_obj.host, server_obj.port, server_obj.username, password)
    if not ssh:
        return jsonify({'message': 'SSH connection failed', 'error': error}), 500

    try:
        stdin, stdout, stderr = ssh.exec_command("echo 'welcome to LR Remote Access'")
        output = stdout.read().decode() or ''
        error_output = stderr.read().decode() or ''
    except Exception as e:
        return jsonify({'message': 'Command execution failed', 'error': str(e)}), 500
    finally:
        try:
            ssh.close()
        except Exception:
            pass

    return jsonify({'output': output, 'error': error_output})
