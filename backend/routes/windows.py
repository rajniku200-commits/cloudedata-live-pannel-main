import os
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required
from backend.services.windows_manager import get_drives, browse_path, create_folder, delete_path, rename_file, move_file, copy_file

windows = Blueprint('windows', __name__)


@windows.route('/drives', methods=['GET'])
@login_required
def drives():
    return jsonify(get_drives())


@windows.route('/browse', methods=['GET'])
@login_required
def browse():
    path = request.args.get('path')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    try:
        return jsonify(browse_path(path))
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        return jsonify({'message': str(exc)}), 400


@windows.route('/create-folder', methods=['POST'])
@login_required
def create_new_folder():
    path = request.form.get('path')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    try:
        return jsonify(create_folder(path))
    except OSError as exc:
        return jsonify({'message': str(exc)}), 400


@windows.route('/delete-path', methods=['POST'])
@login_required
def delete():
    path = request.form.get('path')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    try:
        return jsonify(delete_path(path))
    except OSError as exc:
        return jsonify({'message': str(exc)}), 400


@windows.route('/rename-file', methods=['POST'])
@login_required
def rename():
    old_path = request.form.get('old_path')
    new_path = request.form.get('new_path')
    if not old_path or not new_path:
        return jsonify({'message': 'old_path and new_path are required'}), 400
    try:
        return jsonify(rename_file(old_path, new_path))
    except OSError as exc:
        return jsonify({'message': str(exc)}), 400


@windows.route('/move-file', methods=['POST'])
@login_required
def move():
    source = request.form.get('source')
    destination = request.form.get('destination')
    if not source or not destination:
        return jsonify({'message': 'source and destination are required'}), 400
    try:
        return jsonify(move_file(source, destination))
    except OSError as exc:
        return jsonify({'message': str(exc)}), 400


@windows.route('/copy-file', methods=['POST'])
@login_required
def copy():
    source = request.form.get('source')
    destination = request.form.get('destination')
    if not source or not destination:
        return jsonify({'message': 'source and destination are required'}), 400
    try:
        return jsonify(copy_file(source, destination))
    except OSError as exc:
        return jsonify({'message': str(exc)}), 400


@windows.route('/windows/upload-file', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    path = request.form.get('path')
    if not file or not path:
        return jsonify({'message': 'File and path are required'}), 400
    try:
        file.save(os.path.join(path, file.filename))
    except OSError as exc:
        return jsonify({'message': str(exc)}), 400
    return jsonify({'message': 'File uploaded successfully'})


@windows.route('/download-file', methods=['GET'])
@login_required
def download_file():
    path = request.args.get('path')
    if not path:
        return jsonify({'message': 'Path is required'}), 400
    if not os.path.isfile(path):
        return jsonify({'message': 'File not found'}), 404
    return send_file(path, as_attachment=True)
