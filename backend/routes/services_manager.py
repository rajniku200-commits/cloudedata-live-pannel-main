import platform
from flask import Blueprint, jsonify, request
from flask_login import login_required
from backend.services.windows_services import get_services, start_service, stop_service

services = Blueprint('services_manager', __name__)

@services.route('/services', methods=['GET'])
@login_required
def all_services():
    if platform.system() != 'Windows':
        return '<pre>Service management is only supported on Windows hosts.</pre>', 501
    return f"<pre>{get_services()}</pre>"

@services.route('/start-service', methods=['POST'])
@login_required
def start():
    service_name = request.form.get('service_name')
    if not service_name:
        return '<pre>service_name is required</pre>', 400
    if platform.system() != 'Windows':
        return '<pre>Service management is only supported on Windows hosts.</pre>', 501
    return f"<pre>{start_service(service_name)}</pre>"

@services.route('/stop-service', methods=['POST'])
@login_required
def stop():
    service_name = request.form.get('service_name')
    if not service_name:
        return '<pre>service_name is required</pre>', 400
    if platform.system() != 'Windows':
        return '<pre>Service management is only supported on Windows hosts.</pre>', 501
    return f"<pre>{stop_service(service_name)}</pre>"
