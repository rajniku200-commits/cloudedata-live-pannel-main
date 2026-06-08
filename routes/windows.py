import os
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required
from services.windows_manager import get_drives, browse_path, create_folder, delete_path, rename_file, move_file, copy_file

windows = Blueprint('windows', __name__)


@windows.route('/drives', methods=['GET'])
@login_required
def drives():
    return jsonify(get_drives())


@windows.route('/browse', methods=['GET'])
@login_required
def browse():
    path = request.args.get('path')
    return jsonify(browse_path(path))


@windows.route('/create-folder', methods=['POST'])
@login_required
def create_new_folder():
    path = request.form.get('path')
    return jsonify(create_folder(path))


@windows.route('/delete-path', methods=['POST'])
@login_required
def delete():
    path = request.form.get('path')
    return jsonify(delete_path(path))


@windows.route('/rename-file', methods=['POST'])
@login_required
def rename():
    old_path = request.form.get('old_path')
    new_path = request.form.get('new_path')
    return jsonify(rename_file(old_path, new_path))


@windows.route('/move-file', methods=['POST'])
@login_required
def move():
    source = request.form.get('source')
    destination = request.form.get('destination')
    return jsonify(move_file(source, destination))


@windows.route('/copy-file', methods=['POST'])
@login_required
def copy():
    source = request.form.get('source')
    destination = request.form.get('destination')
    return jsonify(copy_file(source, destination))


@windows.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    path = request.form.get('path')
    if not file or not path:
        return jsonify({'message': 'File and path are required'}), 400
    file.save(os.path.join(path, file.filename))
    return jsonify({'message': 'File uploaded successfully'})


@windows.route('/download-file', methods=['GET'])
@login_required
def download_file():
    path = request.args.get('path')
    return send_file(path, as_attachment=True)
