"""
services/guacamole_client.py
Bridge between Flask app and Apache Guacamole server.
Handles auth tokens, connection creation, session management.
"""

import requests
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class GuacamoleClient:
    """
    Talks to the Guacamole REST API.

    Set these in config.py:
        GUACAMOLE_URL      = "http://localhost:8080/guacamole"
        GUACAMOLE_USER     = "guacadmin"
        GUACAMOLE_PASSWORD = "guacadmin"
    """

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url  = base_url.rstrip("/")
        self.username  = username
        self.password  = password
        self._token    = None

    # ── internal ────────────────────────────────────────────────────────────

    def _get_admin_token(self) -> str | None:
        """Authenticate as admin and return token."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/tokens",
                data={"username": self.username, "password": self.password},
                timeout=10
            )
            if resp.status_code == 200:
                self._token = resp.json().get("authToken")
                return self._token
            logger.error(f"Guacamole admin auth failed: {resp.status_code} {resp.text}")
            return None
        except Exception as e:
            logger.error(f"Guacamole connection error: {e}")
            return None

    def _headers(self) -> dict:
        return {"Content-Type": "application/json"}

    def _params(self) -> dict:
        if not self._token:
            self._get_admin_token()
        return {"token": self._token}

    # ── public API ───────────────────────────────────────────────────────────

    def get_user_token(self, username: str, password: str) -> dict:
        """
        Authenticate an end-user against Guacamole and get their auth token.
        Returns {"success": True, "token": "...", "data_source": "..."}
        """
        try:
            resp = requests.post(
                f"{self.base_url}/api/tokens",
                data={"username": username, "password": password},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success":     True,
                    "token":       data.get("authToken"),
                    "data_source": data.get("dataSource"),
                    "username":    data.get("username"),
                }
            return {"success": False, "error": f"Auth failed: {resp.status_code}"}
        except Exception as e:
            logger.error(f"Guacamole get_user_token error: {e}")
            return {"success": False, "error": str(e)}

    def create_rdp_connection(
        self,
        name: str,
        host: str,
        port: int = 3389,
        rdp_username: str = "",
        rdp_password: str = "",
        domain: str = "",
        security: str = "any",
        ignore_cert: bool = True,
    ) -> dict:
        """
        Create a new RDP connection in Guacamole.
        Returns {"success": True, "connection_id": "..."}
        """
        token = self._get_admin_token()
        if not token:
            return {"success": False, "error": "Could not authenticate to Guacamole"}

        payload = {
            "name":           name,
            "protocol":       "rdp",
            "parentIdentifier": "ROOT",
            "parameters": {
                "hostname":         host,
                "port":             str(port),
                "username":         rdp_username,
                "password":         rdp_password,
                "domain":           domain,
                "security":         security,
                "ignore-cert":      "true" if ignore_cert else "false",
                "enable-drive":     "false",
                "create-drive-path": "false",
            },
            "attributes": {
                "max-connections":          "10",
                "max-connections-per-user": "1",
            }
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/session/data/mysql/connections",
                json=payload,
                params={"token": token},
                timeout=10
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return {"success": True, "connection_id": data.get("identifier")}
            return {"success": False, "error": f"{resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Guacamole create_rdp_connection error: {e}")
            return {"success": False, "error": str(e)}

    def delete_connection(self, connection_id: str) -> dict:
        """Delete a Guacamole connection."""
        token = self._get_admin_token()
        if not token:
            return {"success": False, "error": "Could not authenticate to Guacamole"}
        try:
            resp = requests.delete(
                f"{self.base_url}/api/session/data/mysql/connections/{connection_id}",
                params={"token": token},
                timeout=10
            )
            return {"success": resp.status_code in (200, 204)}
        except Exception as e:
            logger.error(f"Guacamole delete_connection error: {e}")
            return {"success": False, "error": str(e)}

    def list_active_connections(self) -> dict:
        """List all currently active Guacamole connections."""
        token = self._get_admin_token()
        if not token:
            return {"success": False, "error": "Could not authenticate to Guacamole"}
        try:
            resp = requests.get(
                f"{self.base_url}/api/session/data/mysql/activeConnections",
                params={"token": token},
                timeout=10
            )
            if resp.status_code == 200:
                return {"success": True, "connections": resp.json()}
            return {"success": False, "error": f"{resp.status_code}: {resp.text}"}
        except Exception as e:
            logger.error(f"Guacamole list_active_connections error: {e}")
            return {"success": False, "error": str(e)}

    def kill_connection(self, active_connection_id: str) -> dict:
        """Kill a specific active connection by its active connection ID."""
        token = self._get_admin_token()
        if not token:
            return {"success": False, "error": "Could not authenticate to Guacamole"}
        try:
            resp = requests.patch(
                f"{self.base_url}/api/session/data/mysql/activeConnections",
                json=[{"op": "remove", "path": f"/{active_connection_id}"}],
                params={"token": token},
                timeout=10
            )
            return {"success": resp.status_code in (200, 204)}
        except Exception as e:
            logger.error(f"Guacamole kill_connection error: {e}")
            return {"success": False, "error": str(e)}

    def build_client_url(self, connection_id: str, token: str) -> str:
        """
        Build the URL the browser opens to show the RDP desktop.
        Format: /guacamole/#/client/<b64_connection_id>?token=<user_token>
        """
        import base64
        encoded = base64.b64encode(
            f"{connection_id}\x00c\x00mysql".encode()
        ).decode()
        return f"{self.base_url}/#/client/{encoded}?token={token}"


# ── singleton factory (import this in routes) ────────────────────────────────

def get_guac_client() -> GuacamoleClient:
    from flask import current_app
    return GuacamoleClient(
        base_url  = current_app.config.get("GUACAMOLE_URL", "http://localhost:8080/guacamole"),
        username  = current_app.config.get("GUACAMOLE_USER", "guacadmin"),
        password  = current_app.config.get("GUACAMOLE_PASSWORD", "guacadmin"),
    )