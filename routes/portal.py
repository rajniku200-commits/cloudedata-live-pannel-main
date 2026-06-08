"""
routes/portal.py
User portal — serves login page, app launcher, and RDP launch endpoint.
Matches structure of: routes/auth.py, routes/rdp.py
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user

from models.server import Server
from services.session_manager import SessionManager
from services.guacamole_client import get_guac_client
from models.activity_log import ActivityLog

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")
mgr = SessionManager()


# ── Portal home — user app launcher ──────────────────────────────────────────

@portal_bp.route("/", methods=["GET"])
@login_required
def portal_home():
    """
    GET /portal/
    Renders the user-facing portal with all servers the user can connect to.
    """
    servers = Server.query.filter_by(is_active=True).all()
    return render_template(
        "portal.html",
        user    = current_user,
        servers = [s.to_dict() for s in servers],
    )


# ── Admin dashboard — active sessions ────────────────────────────────────────

@portal_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """
    GET /portal/dashboard
    Renders the admin sessions dashboard.
    """
    mgr.cleanup_stale_sessions()
    stats   = mgr.get_stats()
    servers = Server.query.all()
    return render_template(
        "dashboard.html",
        user    = current_user,
        stats   = stats,
        servers = [s.to_dict() for s in servers],
    )


# ── API: list servers for the portal ─────────────────────────────────────────

@portal_bp.route("/api/servers", methods=["GET"])
@login_required
def get_portal_servers():
    """GET /portal/api/servers — servers the current user can access."""
    servers = Server.query.filter_by(is_active=True).all()
    return jsonify({
        "success": True,
        "servers": [s.to_dict() for s in servers],
    }), 200


# ── API: launch RDP from portal ───────────────────────────────────────────────

@portal_bp.route("/api/launch", methods=["POST"])
@login_required
def portal_launch():
    """
    POST /portal/api/launch
    Body: { "server_id": 1, "connection_type": "rdp" }
    Returns the Guacamole client URL to open in a new tab / iframe.
    """
    data          = request.get_json(silent=True) or {}
    server_id     = data.get("server_id")
    conn_type     = data.get("connection_type", "rdp")

    if not server_id:
        return jsonify({"success": False, "error": "server_id required"}), 400

    server = Server.query.get(server_id)
    if not server:
        return jsonify({"success": False, "error": "Server not found"}), 404

    guac = get_guac_client()

    conn_result = guac.create_rdp_connection(
        name         = f"{server.name}-u{current_user.id}",
        host         = server.ip_address,
        port         = getattr(server, "rdp_port", 3389),
        rdp_username = getattr(server, "rdp_username", ""),
        rdp_password = getattr(server, "rdp_password", ""),
    )
    if not conn_result["success"]:
        return jsonify({"success": False, "error": conn_result.get("error")}), 500

    from flask import current_app
    token_result = guac.get_user_token(
        current_app.config.get("GUACAMOLE_USER", "guacadmin"),
        current_app.config.get("GUACAMOLE_PASSWORD", "guacadmin"),
    )
    if not token_result["success"]:
        return jsonify({"success": False, "error": token_result.get("error")}), 500

    connection_id = conn_result["connection_id"]
    user_token    = token_result["token"]

    session = mgr.create_session(
        user_id            = current_user.id,
        server_id          = server_id,
        guac_token         = user_token,
        guac_connection_id = connection_id,
        connection_type    = conn_type,
        ip_address         = request.remote_addr,
        user_agent         = request.headers.get("User-Agent"),
    )

    ActivityLog.log(
        action     = f"{conn_type}_launch",
        category   = conn_type,
        user_id    = current_user.id,
        server_id  = server_id,
        session_id = session.id,
        ip_address = request.remote_addr,
    )

    client_url = guac.build_client_url(connection_id, user_token)

    return jsonify({
        "success":    True,
        "session_id": session.id,
        "client_url": client_url,
    }), 201


# ── API: user's own session history ──────────────────────────────────────────

@portal_bp.route("/api/my-sessions", methods=["GET"])
@login_required
def my_sessions():
    """GET /portal/api/my-sessions"""
    sessions = mgr.get_user_sessions(current_user.id)
    return jsonify({
        "success":  True,
        "sessions": [s.to_dict() for s in sessions],
    }), 200


# ── API: session statistics ──────────────────────────────────────────────────

@portal_bp.route("/api/sessions/stats", methods=["GET"])
@login_required
def sessions_stats():
    """GET /api/sessions/stats — session statistics for the dashboard"""
    from models.rdp_session import RdpSession
    active_count = RdpSession.query.filter_by(user_id=current_user.id, status='active').count()
    total_count = RdpSession.query.filter_by(user_id=current_user.id).count()
    return jsonify({
        "success": True,
        "active": active_count,
        "total": total_count
    }), 200