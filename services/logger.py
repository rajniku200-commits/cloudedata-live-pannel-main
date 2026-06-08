from models.activity_log import ActivityLog
from extensions import db


def add_log(user_id, action):
    log = ActivityLog(user_id=user_id, action=action)
    db.session.add(log)
    db.session.commit()

