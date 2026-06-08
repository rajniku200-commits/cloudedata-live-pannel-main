"""
services/session_manager.py
Tracks active RDP sessions — create, update, close, cleanup.
Matches structure of: services/rdp_manager.py, services/process_manager.py
"""

import logging
from datetime import datetime, timedelta
from extensions import db
from models.rdp_session import RdpSession

logger = logging.getLogger(__name__)

# Sessions inactive for more than this many minutes are auto-closed
SESSION_TIMEOUT_MINUTES = 60


class SessionManager:

    # ── create ───────────────────────────────────────────────────────────────

    def create_session(
        self,
        user_id: int,
        server_id: int,
        guac_token: str = None,
        guac_connection_id: str = None,
        connection_type: str = "rdp",
        ip_address: str = None,
        user_agent: str = None,
    ) -> RdpSession:
        """Open a new RDP session record."""
        session = RdpSession(
            user_id            = user_id,
            server_id          = server_id,
            guac_token         = guac_token,
            guac_connection_id = guac_connection_id,
            connection_type    = connection_type,
            status             = "active",
            ip_address         = ip_address,
            user_agent         = user_agent,
        )
        db.session.add(session)
        db.session.commit()
        logger.info(f"Session created: id={session.id} user={user_id} server={server_id}")
        return session

    # ── read ─────────────────────────────────────────────────────────────────

    def get_all_active(self) -> list[RdpSession]:
        return RdpSession.get_active()

    def get_session(self, session_id: int) -> RdpSession | None:
        return RdpSession.query.get(session_id)

    def get_user_sessions(self, user_id: int, active_only: bool = False) -> list[RdpSession]:
        if active_only:
            return RdpSession.query.filter_by(user_id=user_id, status="active").all()
        return RdpSession.get_by_user(user_id)

    def get_server_sessions(self, server_id: int, active_only: bool = True) -> list[RdpSession]:
        q = RdpSession.query.filter_by(server_id=server_id)
        if active_only:
            q = q.filter_by(status="active")
        return q.order_by(RdpSession.started_at.desc()).all()

    def get_stats(self) -> dict:
        """Summary stats for the dashboard."""
        total   = RdpSession.query.count()
        active  = RdpSession.query.filter_by(status="active").count()
        closed  = RdpSession.query.filter_by(status="closed").count()
        errors  = RdpSession.query.filter_by(status="error").count()
        return {
            "total":  total,
            "active": active,
            "closed": closed,
            "errors": errors,
        }

    # ── update ────────────────────────────────────────────────────────────────

    def ping_session(self, session_id: int) -> bool:
        """Keep-alive ping — update last_seen_at."""
        session = self.get_session(session_id)
        if session and session.status == "active":
            session.ping()
            return True
        return False

    def update_token(self, session_id: int, new_token: str) -> bool:
        session = self.get_session(session_id)
        if session:
            session.guac_token = new_token
            db.session.commit()
            return True
        return False

    # ── close ─────────────────────────────────────────────────────────────────

    def close_session(self, session_id: int) -> dict:
        """Close a session by ID."""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        if session.status != "active":
            return {"success": False, "error": "Session already closed"}
        session.close()
        logger.info(f"Session closed: id={session_id}")
        return {"success": True, "message": f"Session {session_id} closed"}

    def close_user_sessions(self, user_id: int) -> dict:
        """Close all active sessions for a user."""
        sessions = self.get_user_sessions(user_id, active_only=True)
        for s in sessions:
            s.close()
        logger.info(f"Closed {len(sessions)} sessions for user {user_id}")
        return {"success": True, "closed": len(sessions)}

    def mark_error(self, session_id: int, detail: str = "") -> bool:
        session = self.get_session(session_id)
        if session:
            session.status   = "error"
            session.ended_at = datetime.utcnow()
            db.session.commit()
            logger.warning(f"Session {session_id} marked error: {detail}")
            return True
        return False

    # ── cleanup ───────────────────────────────────────────────────────────────

    def cleanup_stale_sessions(self) -> int:
        """
        Auto-close sessions that haven't pinged in SESSION_TIMEOUT_MINUTES.
        Call this from a scheduled job or on each dashboard load.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        stale = RdpSession.query.filter(
            RdpSession.status == "active",
            RdpSession.last_seen_at < cutoff
        ).all()
        for s in stale:
            s.status   = "closed"
            s.ended_at = datetime.utcnow()
        db.session.commit()
        if stale:
            logger.info(f"Auto-closed {len(stale)} stale sessions")
        return len(stale)