from urllib.parse import urljoin

import requests


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.user = None

    def set_base_url(self, base_url):
        self.base_url = base_url.rstrip('/')

    def login(self, username, password, token=None):
        payload = {'username': username, 'password': password}
        if token:
            payload['token'] = token
        data = self.post('/login', payload)
        self.user = data.get('user')
        return data

    def logout(self):
        try:
            return self.post('/logout', {})
        finally:
            self.user = None

    def health(self):
        return self.get('/api/health')

    def monitoring(self):
        return self.get('/api/monitoring')

    def users(self):
        return self.get('/users').get('users', [])

    def create_user(self, payload):
        return self.post('/users', payload)

    def update_user(self, user_id, payload):
        return self.patch(f'/users/{user_id}', payload)

    def delete_user(self, user_id):
        return self.delete(f'/users/{user_id}')

    def servers(self):
        data = self.get('/servers')
        return data if isinstance(data, list) else data.get('servers', [])

    def apps(self):
        return self.get('/api/apps').get('apps', [])

    def create_app(self, payload):
        return self.post('/api/apps', payload)

    def update_app(self, app_id, payload):
        return self.patch(f'/api/apps/{app_id}', payload)

    def delete_app(self, app_id):
        return self.delete(f'/api/apps/{app_id}')

    def assignments_for_user(self, user_id):
        return self.get(f'/api/apps/assignments/user/{user_id}')

    def assign_app(self, app_id, user_id, enabled=True):
        return self.post(f'/api/apps/{app_id}/assign', {'user_id': user_id, 'is_enabled': enabled})

    def unassign_app(self, app_id, user_id):
        return self.delete(f'/api/apps/{app_id}/assign/{user_id}')

    def generate_url(self, user_id=None, expires_minutes=60, one_time=True):
        return self.post('/api/generate-url', {
            'user_id': user_id,
            'expires_minutes': expires_minutes,
            'one_time': one_time,
        })

    def sessions(self):
        return self.get('/api/sessions/').get('sessions', [])

    def session_stats(self):
        return self.get('/api/sessions/stats')

    def agents(self):
        data = self.get('/agents')
        return data if isinstance(data, list) else data.get('agents', [])

    def streams(self):
        return self.get('/api/streams').get('streams', [])

    def get(self, path):
        return self._request('GET', path)

    def post(self, path, payload=None):
        return self._request('POST', path, json=payload or {})

    def patch(self, path, payload=None):
        return self._request('PATCH', path, json=payload or {})

    def delete(self, path):
        return self._request('DELETE', path)

    def _request(self, method, path, **kwargs):
        url = urljoin(self.base_url + '/', path.lstrip('/'))
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
        except requests.RequestException as error:
            raise ApiError(f'Connection failed: {error}') from error

        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            data = response.json()
        else:
            data = {'message': response.text.strip()}

        if response.status_code >= 400:
            message = data.get('error') or data.get('message') or f'HTTP {response.status_code}'
            raise ApiError(message)
        return data

