from flask import Blueprint, jsonify, request
from flask_login import login_required
from services.windows_services import get_services, start_service, stop_service

services = Blueprint('services_manager', __name__)

@services.route('/services', methods=['GET'])
@login_required
def all_services():
    return f"<pre>{get_services()}</pre>"

@services.route('/start-service', methods=['POST'])
@login_required
def start():
    service_name = request.form.get('service_name')
    return f"<pre>{start_service(service_name)}</pre>"

@services.route('/stop-service', methods=['POST'])
@login_required
def stop():
    service_name = request.form.get('service_name')
    return f"<pre>{stop_service(service_name)}</pre>"
