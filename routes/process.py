from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from services.logger import add_log
from services.process_manager import get_processes, kill_process

process = Blueprint('process', __name__)

@process.route('/processes', methods=['GET'])
@login_required
def processes():
    return f"<pre>{get_processes()}</pre>"

@process.route('/kill-process', methods=['POST'])
@login_required
def kill():
    pid = request.form.get('pid')
    add_log(current_user.id, f"Killed process with PID: {pid}")
    return f"<pre>{kill_process(pid)}</pre>"
