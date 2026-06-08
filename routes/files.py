from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from services.file_manager import create_file, deleted_file, list_files, read_file
from services.logger import add_log

files = Blueprint('files', __name__)


@files.route('/files')
@login_required
def get_files():
    path = request.args.get('path', '.')
    return jsonify(list_files(path))


@files.route('/read-file')
@login_required
def get_file():
    path = request.args.get('path')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    return jsonify({'content': read_file(path)})


@files.route('/create-file', methods=['POST'])
@login_required
def new_file():
    path = request.form.get('path')
    content = request.form.get('content', '')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    return jsonify({'message': create_file(path, content)})


@files.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    uploaded_file = request.files.get('file')
    path = request.form.get('path')
    if not uploaded_file or not path:
        return jsonify({'message': 'File and path are required'}), 400
    return jsonify({'message': create_file(path, uploaded_file.read())})


@files.route('/delete-file', methods=['POST'])
@login_required
def delete_file_route():
    path = request.form.get('path')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    add_log(current_user.id, f'Deleted file: {path}')
    return jsonify({'message': deleted_file(path)})
