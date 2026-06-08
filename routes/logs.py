from flask import Blueprint, jsonify
from flask_login import login_required
from models.activity_log import ActivityLog

logs = Blueprint('logs', __name__)


@logs.route('/logs', methods=['GET'])
@login_required
def get_logs():
    data = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(100).all()
    return jsonify([
        {
            'user_id': log.user_id,
            'action': log.action,
            'timestamp': log.timestamp.isoformat(),
            'time': str(log.created_at)
        }
        for log in data
    ])
