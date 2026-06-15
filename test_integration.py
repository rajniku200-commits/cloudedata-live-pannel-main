#!/usr/bin/env python3
"""
Test script to verify LR Remote Access backend integration
Run this to validate that all components are properly connected
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    print('Testing imports...')
    try:
        from flask import Flask
        print('  ✓ Flask')
        from flask_login import LoginManager, UserMixin
        print('  ✓ Flask-Login')
        from flask_sqlalchemy import SQLAlchemy
        print('  ✓ Flask-SQLAlchemy')
        from flask_socketio import SocketIO
        print('  ✓ Flask-SocketIO')
        import paramiko
        print('  ✓ paramiko')
        from werkzeug.security import generate_password_hash
        print('  ✓ werkzeug')
        try:
            import requests
            print('  ✓ requests')
        except ImportError:
            print('  ~ requests (optional for Guacamole)')
        return True
    except ImportError as e:
        print(f'  ✗ Import failed: {e}')
        return False


def test_models():
    print('\nTesting models...')
    try:
        from backend.models.user import User
        print('  ✓ User model')
        from backend.models.server import Server
        print('  ✓ Server model')
        from backend.models.session import Session
        print('  ✓ Session model')
        from backend.models.rdp_session import RdpSession
        print('  ✓ RdpSession model')
        from backend.models.activity_log import ActivityLog
        print('  ✓ ActivityLog model')
        if hasattr(Server, 'to_dict'):
            print('  ✓ Server.to_dict() method')
        else:
            print('  ✗ Server.to_dict() method missing')
            return False
        return True
    except Exception as e:
        print(f'  ✗ Model test failed: {e}')
        return False


def test_routes():
    print('\nTesting routes...')
    try:
        from backend.routes.auth import auth
        print('  ✓ Auth routes')
        from backend.routes.portal import portal_bp
        print('  ✓ Portal routes')
        from backend.routes.files import files
        print('  ✓ Files routes')
        from backend.routes.terminal import terminal
        print('  ✓ Terminal routes')
        from backend.routes.server import server
        print('  ✓ Server routes')
        from backend.routes.windows import windows
        print('  ✓ Windows routes')
        from backend.routes.process import process
        print('  ✓ Process routes')
        from backend.routes.services_manager import services
        print('  ✓ Services routes')
        from backend.routes.logs import logs
        print('  ✓ Logs routes')
        return True
    except Exception as e:
        if 'requests' in str(e):
            print('  ~ Route test (requests optional for guacamole)')
            return True
        print(f'  ✗ Route test failed: {e}')
        return False


def test_services():
    print('\nTesting services...')
    try:
        from backend.services import file_manager
        print('  ✓ file_manager service')
        from backend.services import terminal
        print('  ✓ terminal service')
        from backend.services import ssh_manager
        print('  ✓ ssh_manager service')
        from backend.services import logger
        print('  ✓ logger service')
        from backend.services.session_manager import SessionManager
        print('  ✓ SessionManager service')
        try:
            from backend.services.guacamole_client import GuacamoleClient
            print('  ✓ GuacamoleClient service')
        except ImportError:
            print('  ~ GuacamoleClient service (requires requests)')
        return True
    except Exception as e:
        print(f'  ✗ Service test failed: {e}')
        return False


def main():
    ok = test_imports() and test_models() and test_routes() and test_services()
    print('\nIntegration result:', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
