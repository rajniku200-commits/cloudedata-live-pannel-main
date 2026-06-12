from flask import Blueprint, request
from flask_login import current_user, login_required
from backend.services.logger import add_log
from backend.services.terminal import run_command

terminal = Blueprint("terminal", __name__)


@terminal.route("/terminal", methods=["POST"])
@login_required
def execute():
    command = request.form.get("command")
    add_log(current_user.id, f"Executed command: {command}")
    return run_command(command)
