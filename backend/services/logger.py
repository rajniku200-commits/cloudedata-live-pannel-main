from backend.models.activity_log import ActivityLog


def add_log(user_id, action):
    ActivityLog.log(user_id=user_id, action=action, category='system')

