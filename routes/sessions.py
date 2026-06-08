"""
routes/sessions.py
Active sessions dashboard API — list, kill, ping, stats.
Matches structure of: routes/rdp.py, routes/files.py, routes/logs.py
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from services.session_manager import SessionManager
from services.guacamole_client import get_guac_client
from models.activity_log import ActivityLog

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/sessions")
mgr = SessionManager()


# ── GET all active sessions (admin dashboard) ────────────────────────────────

@sessions_bp.route("/", methods=["GET"])
@login_required
def list_sessions():
    """GET /api/sessions/ — all active sessions with optional filters."""
    mgr.cleanup_stale_sessions()

    server_id = request.args.get("server_id", type=int)
    user_id   = request.args.get("user_id",   type=int)
    status    = request.args.get("status", "active")

    from models.rdp_session import RdpSession
    query = RdpSession.query

    if status != "all":
        query = query.filter_by(status=status)
    if server_id:
        query = query.filter_by(server_id=server_id)
    if user_id:
        query = query.filter_by(user_id=user_id)

    sessions = query.order_by(RdpSession.started_at.desc()).limit(200).all()

    return jsonify({
        "success":  True,
        "sessions": [s.to_dict() for s in sessions],
        "count":    len(sessions),
    }), 200


# ── GET stats ────────────────────────────────────────────────────────────────

@sessions_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    """GET /api/sessions/stats — counts for dashboard cards."""
    return jsonify({"success": True, **mgr.get_stats()}), 200


# ── GET single session ────────────────────────────────────────────────────────

@sessions_bp.route("/<int:session_id>", methods=["GET"])
@login_required
def get_session(session_id):
    """GET /api/sessions/<id>"""
    s = mgr.get_session(session_id)
    if not s:
        return jsonify({"success": False, "error": "Session not found"}), 404
    return jsonify({"success": True, "session": s.to_dict()}), 200


# ── GET my sessions (current user) ───────────────────────────────────────────

@sessions_bp.route("/me", methods=["GET"])
@login_required
def my_sessions():
    """GET /api/sessions/me"""
    sessions = mgr.get_user_sessions(current_user.id)
    return jsonify({
        "success":  True,
        "sessions": [s.to_dict() for s in sessions],
    }), 200


# ── POST launch a new RDP session ─────────────────────────────────────────────

@sessions_bp.route("/launch", methods=["POST"])
@login_required
def launch_session():
    """
    POST /api/sessions/launch
    Body: { "server_id": 1 }
    Returns guacamole client URL to open in browser.
    """
    data = request.get_json(silent=True) or {}
    server_id = data.get("server_id")
    if not server_id:
        return jsonify({"success": False, "error": "server_id required"}), 400

    from models.server import Server
    server = Server.query.get(server_id)
    if not server:
        return jsonify({"success": False, "error": "Server not found"}), 404

    guac = get_guac_client()

    # 1. Create connection in Guacamole
    conn_result = guac.create_rdp_connection(
        name         = f"{server.name}-{current_user.id}",
        host         = server.ip_address,
        port         = getattr(server, "rdp_port", 3389),
        rdp_username = getattr(server, "rdp_username", ""),
        rdp_password = getattr(server, "rdp_password", ""),
    )
    if not conn_result["success"]:
        return jsonify({"success": False, "error": conn_result["error"]}), 500

    # 2. Get user token from Guacamole
    from flask import current_app
    guac_user = current_app.config.get("GUACAMOLE_USER", "guacadmin")
    guac_pass = current_app.config.get("GUACAMOLE_PASSWORD", "guacadmin")
    token_result = guac.get_user_token(guac_user, guac_pass)
    if not token_result["success"]:
        return jsonify({"success": False, "error": token_result["error"]}), 500

    connection_id = conn_result["connection_id"]
    user_token    = token_result["token"]

    # 3. Save session to DB
    session = mgr.create_session(
        user_id            = current_user.id,
        server_id          = server_id,
        guac_token         = user_token,
        guac_connection_id = connection_id,
        connection_type    = "rdp",
        ip_address         = request.remote_addr,
        user_agent         = request.headers.get("User-Agent"),
    )

    # 4. Log the activity
    ActivityLog.log(
        action     = "rdp_launch",
        category   = "rdp",
        user_id    = current_user.id,
        server_id  = server_id,
        session_id = session.id,
        ip_address = request.remote_addr,
    )

    # 5. Build client URL
    client_url = guac.build_client_url(connection_id, user_token)

    return jsonify({
        "success":     True,
        "session_id":  session.id,
        "client_url":  client_url,
        "guac_token":  user_token,
        "connection_id": connection_id,
    }), 201


# ── DELETE / kill a session ───────────────────────────────────────────────────

@sessions_bp.route("/<int:session_id>/kill", methods=["DELETE", "POST"])
@login_required
def kill_session(session_id):
    """DELETE /api/sessions/<id>/kill"""
    s = mgr.get_session(session_id)
    if not s:
        return jsonify({"success": False, "error": "Session not found"}), 404

    # Kill on Guacamole side too if we have the connection ID
    if s.guac_connection_id:
        try:
            guac = get_guac_client()
            guac.delete_connection(s.guac_connection_id)
        except Exception:
            pass

    result = mgr.close_session(session_id)
    ActivityLog.log(
        action     = "session_killed",
        category   = "rdp",
        user_id    = current_user.id,
        session_id = session_id,
        ip_address = request.remote_addr,
    )
    return jsonify(result), 200


# ── POST ping (keep-alive) ────────────────────────────────────────────────────

@sessions_bp.route("/<int:session_id>/ping", methods=["POST"])
@login_required
def ping_session(session_id):
    """POST /api/sessions/<id>/ping — called every ~30s from the client."""
    ok = mgr.ping_session(session_id)
    return jsonify({"success": ok}), 200 if ok else 404