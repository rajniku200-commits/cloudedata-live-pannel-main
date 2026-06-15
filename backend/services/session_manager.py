import logging
from datetime import datetime, timedelta

from backend.extensions import db
from backend.models.rdp_session import RdpSession

logger = logging.getLogger(__name__)

SESSION_TIMEOUT_MINUTES = 60


class SessionManager:

    def create_session(
        self,
        user_id,
        server_id,
        guac_token=None,
        guac_connection_id=None,
        connection_type='rdp',
        published_app_id=None,
        ip_address=None,
        user_agent=None,
    ):
        session = RdpSession(
            user_id=user_id,
            server_id=server_id,
            published_app_id=published_app_id,
            guac_token=guac_token,
            guac_connection_id=guac_connection_id,
            connection_type=connection_type,
            status='active',
            ip_address=ip_address,
            user_agent=user_agent,
        ).save()
        logger.info(f'Session created: id={session.id} user={user_id} server={server_id}')
        return session

    def get_all_active(self):
        return RdpSession.get_active()

    def get_session(self, session_id):
        if session_id is None:
            return None
        try:
            return db.session.get(RdpSession, int(session_id))
        except (TypeError, ValueError):
            return None

    def get_user_sessions(self, user_id, active_only=False):
        if active_only:
            return RdpSession.query.filter_by(user_id=user_id, status='active').order_by(RdpSession.started_at.desc()).all()
        return RdpSession.get_by_user(user_id)

    def get_server_sessions(self, server_id, active_only=True):
        query = RdpSession.query.filter_by(server_id=server_id)
        if active_only:
            query = query.filter_by(status='active')
        return query.order_by(RdpSession.started_at.desc()).all()

    def get_stats(self):
        return {
            'total': RdpSession.query.count(),
            'active': RdpSession.query.filter_by(status='active').count(),
            'closed': RdpSession.query.filter_by(status='closed').count(),
            'errors': RdpSession.query.filter_by(status='error').count(),
        }

    def ping_session(self, session_id):
        session = self.get_session(session_id)
        if session and session.status == 'active':
            session.ping()
            return True
        return False

    def update_token(self, session_id, new_token):
        session = self.get_session(session_id)
        if session:
            session.guac_token = new_token
            db.session.commit()
            return True
        return False

    def close_session(self, session_id):
        session = self.get_session(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}
        if session.status != 'active':
            return {'success': False, 'error': 'Session already closed'}
        session.close()
        logger.info(f'Session closed: id={session_id}')
        return {'success': True, 'message': f'Session {session_id} closed'}

    def close_user_sessions(self, user_id):
        sessions = self.get_user_sessions(user_id, active_only=True)
        for s in sessions:
            s.close()
        logger.info(f'Closed {len(sessions)} sessions for user {user_id}')
        return {'success': True, 'closed': len(sessions)}

    def mark_error(self, session_id, detail=''):
        session = self.get_session(session_id)
        if session:
            session.status = 'error'
            session.ended_at = datetime.utcnow()
            db.session.commit()
            logger.warning(f'Session {session_id} marked error: {detail}')
            return True
        return False

    def cleanup_stale_sessions(self):
        cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        count = RdpSession.query.filter(
            RdpSession.status == 'active',
            RdpSession.last_seen_at < cutoff,
        ).update({
            RdpSession.status: 'closed',
            RdpSession.ended_at: datetime.utcnow(),
        }, synchronize_session=False)
        db.session.commit()
        if count:
            logger.info(f'Auto-closed {count} stale sessions')
        return count
