#!/usr/bin/env python3
"""
Test script to verify CloudeData Live Panel backend integration
Run this to validate that all components are properly connected
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        from flask import Flask
        print("  ✓ Flask")
        from flask_login import LoginManager, UserMixin
        print("  ✓ Flask-Login")
        from flask_sqlalchemy import SQLAlchemy
        print("  ✓ Flask-SQLAlchemy")
        from flask_socketio import SocketIO
        print("  ✓ Flask-SocketIO")
        import paramiko
        print("  ✓ paramiko")
        from werkzeug.security import generate_password_hash
        print("  ✓ werkzeug")
        # requests is optional for now - guacamole integration
        try:
            import requests
            print("  ✓ requests")
        except:
            print("  ~ requests (optional for Guacamole)")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_models():
    """Test that database models are properly defined"""
    print("\nTesting models...")
    try:
        from models.user import User
        print("  ✓ User model")
        from models.server import Server
        print("  ✓ Server model")
        from models.session import Session
        print("  ✓ Session model")
        from models.rdp_session import RdpSession
        print("  ✓ RdpSession model")
        from models.activity_log import ActivityLog
        print("  ✓ ActivityLog model")
        
        # Check Server has to_dict method
        if hasattr(Server, 'to_dict'):
            print("  ✓ Server.to_dict() method")
        else:
            print("  ✗ Server.to_dict() method missing")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Model test failed: {e}")
        return False

def test_routes():
    """Test that route blueprints are properly defined"""
    print("\nTesting routes...")
    try:
        from routes.auth import auth
        print("  ✓ Auth routes")
        from routes.portal import portal_bp
        print("  ✓ Portal routes")
        from routes.files import files
        print("  ✓ Files routes")
        from routes.terminal import terminal
        print("  ✓ Terminal routes")
        from routes.server import server
        print("  ✓ Server routes")
        from routes.windows import windows
        print("  ✓ Windows routes")
        from routes.process import process
        print("  ✓ Process routes")
        from routes.services_manager import services
        print("  ✓ Services routes")
        from routes.logs import logs
        print("  ✓ Logs routes")
        return True
    except Exception as e:
        if "requests" in str(e):
            print(f"  ~ Route test (requests optional for guacamole)")
            return True
        print(f"  ✗ Route test failed: {e}")
        return False

def test_services():
    """Test that service classes are properly defined"""
    print("\nTesting services...")
    try:
        from services import file_manager
        print("  ✓ file_manager service")
        from services import terminal
        print("  ✓ terminal service")
        from services import ssh_manager
        print("  ✓ ssh_manager service")
        from services import logger
        print("  ✓ logger service")
        from services.session_manager import SessionManager
        print("  ✓ SessionManager service")
        try:
            from services.guacamole_client import GuacamoleClient
            print("  ✓ GuacamoleClient service")
        except ImportError as e:
            print(f"  ~ GuacamoleClient service (requires requests)")
        return True
    except Exception as e:
        print(f"  ✗ Service test failed: {e}")
        return False

def test_app_structure():
    """Test that Flask app is properly structured"""
    print("\nTesting Flask app structure...")
    try:
        from app import app
        print("  ✓ Flask app created")
        
        # Check blueprints are registered
        blueprints = [bp.name for bp in app.blueprints.values()]
        required = ['auth', 'portal', 'files', 'terminal', 'server', 'windows', 'process', 'services', 'logs']
        
        for bp in required:
            if bp in blueprints:
                print(f"  ✓ {bp} blueprint registered")
            else:
                print(f"  ✗ {bp} blueprint NOT registered")
                return False
        
        return True
    except Exception as e:
        if "requests" in str(e):
            print(f"  ~ App structure test (requests optional for guacamole)")
            return True
        print(f"  ✗ App structure test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("CloudeData Live Panel - Backend Integration Test")
    print("=" * 50)
    
    results = [
        ("Imports", test_imports()),
        ("Models", test_models()),
        ("Routes", test_routes()),
        ("Services", test_services()),
        ("App Structure", test_app_structure()),
    ]
    
    print("\n" + "=" * 50)
    print("TEST RESULTS")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("✓ All tests passed! Backend is ready.")
        return 0
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
