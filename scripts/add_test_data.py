#!/usr/bin/env python3
"""Insert sample records into the app database for testing."""

import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.extensions import db
from backend.models.user import User
from backend.models.server import Server
from backend.models.activity_log import ActivityLog
from backend.models.session import Session
from backend.models.rdp_session import RdpSession


def main():
    with app.app_context():
        print('Creating test data...')

        # Create a user
        user = User(username='testuser', password='testpassword')
        user.save()
        print('Created user:', user.id)

        # Create a server
        server = Server(
            name='Test Server',
            host='127.0.0.1',
            username='admin',
            password='admin123',
            port=22,
        ).save()
        print('Created server:', server.id)

        # Create an activity log entry
        log = ActivityLog.log(
            user_id=user.id,
            action='test_insert',
            category='test',
            server_id=server.id,
            session_id=None,
            ip_address='127.0.0.1',
        )
        print('Created activity log:', log.id)

        # Create a session record
        session = RdpSession(
            user_id=user.id,
            server_id=server.id,
            connection_type='rdp',
            status='active',
            ip_address='127.0.0.1',
            user_agent='test-agent',
        ).save()
        print('Created rdp session:', session.id)

        test_session = Session(
            user_id=user.id,
            session_token='testtoken123',
            status='active',
        )
        db.session.add(test_session)
        db.session.commit()
        print('Created session record:', test_session.id)

        print('Test data insertion complete.')


if __name__ == '__main__':
    main()
