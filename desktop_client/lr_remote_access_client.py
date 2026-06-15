import json
import os
import threading
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.cookiejar import CookieJar
from tkinter import BOTH, END, LEFT, X, Button, Entry, Frame, Label, Text, Tk, filedialog, messagebox


DEFAULT_SERVER_URL = os.getenv('LR_SERVER_URL', 'http://127.0.0.1:5000')


class LRApi:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def post_json(self, path, payload):
        body = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        return self._open(request)

    def post_file(self, path, file_path):
        boundary = '----LRRemoteAccessBoundary'
        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        with open(file_path, 'rb') as handle:
            content = handle.read()
        body = b''.join([
            f'--{boundary}\r\n'.encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f'Content-Type: {content_type}\r\n\r\n'.encode(),
            content,
            f'\r\n--{boundary}--\r\n'.encode(),
        ])
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
            method='POST',
        )
        return self._open(request)

    def get_json(self, path):
        request = urllib.request.Request(self.base_url + path, method='GET')
        return self._open(request)

    def _open(self, request):
        try:
            with self.opener.open(request, timeout=20) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as error:
            try:
                data = json.loads(error.read().decode('utf-8'))
            except Exception:
                data = {'message': str(error)}
            raise RuntimeError(data.get('error') or data.get('message') or str(error))
        except Exception as error:
            raise RuntimeError(str(error))


class LRRemoteAccessClient:
    def __init__(self):
        self.root = Tk()
        self.root.title('LR Remote Access')
        self.root.geometry('420x520')
        self.root.minsize(360, 440)
        self.api = None
        self.server_entry = None
        self.username_entry = None
        self.password_entry = None
        self.two_factor_entry = None
        self.ticket_title_entry = None
        self.ticket_description = None
        self.clipboard_text = None
        self.app_frame = None
        self.status = None
        self.show_login()

    def show_login(self):
        self.clear()
        frame = Frame(self.root, padx=28, pady=28)
        frame.pack(fill=BOTH, expand=True)

        Label(frame, text='LR Remote Access', font=('Segoe UI', 20, 'bold')).pack(anchor='w', pady=(0, 8))
        Label(frame, text='Login to open your assigned apps.', font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 22))

        Label(frame, text='Server URL').pack(anchor='w')
        self.server_entry = Entry(frame)
        self.server_entry.insert(0, DEFAULT_SERVER_URL)
        self.server_entry.pack(fill=X, pady=(4, 12))

        Label(frame, text='Username').pack(anchor='w')
        self.username_entry = Entry(frame)
        self.username_entry.pack(fill=X, pady=(4, 12))

        Label(frame, text='Password').pack(anchor='w')
        self.password_entry = Entry(frame, show='*')
        self.password_entry.pack(fill=X, pady=(4, 18))

        Label(frame, text='2FA code').pack(anchor='w')
        self.two_factor_entry = Entry(frame)
        self.two_factor_entry.pack(fill=X, pady=(4, 18))

        Button(frame, text='Login', command=self.login, height=2).pack(fill=X)
        self.status = Label(frame, text='', fg='#666')
        self.status.pack(anchor='w', pady=(16, 0))

    def show_apps(self, apps):
        self.clear()
        frame = Frame(self.root, padx=24, pady=24)
        frame.pack(fill=BOTH, expand=True)

        top = Frame(frame)
        top.pack(fill=X, pady=(0, 18))
        Label(top, text='My Applications', font=('Segoe UI', 18, 'bold')).pack(side=LEFT)
        Button(top, text='Logout', command=self.show_login).pack(side='right')

        self.app_frame = Frame(frame)
        self.app_frame.pack(fill=BOTH, expand=True)

        if not apps:
            Label(self.app_frame, text='No applications assigned yet.').pack(anchor='w')
            return

        for app in apps:
            Button(
                self.app_frame,
                text=app.get('name', 'Application'),
                command=lambda item=app: self.launch_app(item),
                height=2,
            ).pack(fill=X, pady=6)

        tools = Frame(frame)
        tools.pack(fill=X, pady=(12, 0))
        Button(tools, text='Upload File', command=self.upload_file).pack(fill=X, pady=3)
        Button(tools, text='Clipboard', command=self.show_clipboard).pack(fill=X, pady=3)
        Button(tools, text='New Ticket', command=self.show_ticket).pack(fill=X, pady=3)

        self.status = Label(frame, text='', fg='#666')
        self.status.pack(anchor='w', pady=(12, 0))

    def login(self):
        base_url = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        token = self.two_factor_entry.get().strip()
        if not base_url or not username or not password:
            messagebox.showerror('LR Remote Access', 'Server URL, username, and password are required.')
            return

        self.status.config(text='Signing in...')
        self.api = LRApi(base_url)
        self.run_async(lambda: self._login(username, password, token))

    def _login(self, username, password, token):
        payload = {'username': username, 'password': password}
        if token:
            payload['token'] = token
        self.api.post_json('/login', payload)
        apps = self.api.get_json('/portal/api/apps').get('apps', [])
        self.root.after(0, lambda: self.show_apps(apps))

    def launch_app(self, app):
        self.status.config(text=f"Starting {app.get('name', 'application')}...")
        self.run_async(lambda: self._launch_app(app))

    def _launch_app(self, app):
        result = self.api.post_json(f"/portal/api/apps/{app['id']}/launch", {})
        client_url = result.get('client_url')
        if not client_url:
            raise RuntimeError('Launch URL was not returned by the server.')
        webbrowser.open(client_url)
        self.root.after(0, lambda: self.status.config(text='Remote app opened.'))

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        self.status.config(text='Uploading file...')
        self.run_async(lambda: self._upload_file(file_path))

    def _upload_file(self, file_path):
        self.api.post_file('/api/transfers', file_path)
        self.root.after(0, lambda: self.status.config(text='File uploaded.'))

    def show_clipboard(self):
        self.clear()
        frame = Frame(self.root, padx=24, pady=24)
        frame.pack(fill=BOTH, expand=True)
        Label(frame, text='Clipboard Sync', font=('Segoe UI', 18, 'bold')).pack(anchor='w', pady=(0, 12))
        self.clipboard_text = Text(frame, height=10)
        self.clipboard_text.pack(fill=BOTH, expand=True)
        Button(frame, text='Sync Clipboard', command=self.sync_clipboard).pack(fill=X, pady=(12, 6))
        Button(frame, text='Back', command=self.reload_apps).pack(fill=X)
        self.status = Label(frame, text='', fg='#666')
        self.status.pack(anchor='w', pady=(12, 0))

    def sync_clipboard(self):
        content = self.clipboard_text.get('1.0', END).strip()
        if not content:
            messagebox.showerror('LR Remote Access', 'Clipboard text is required.')
            return
        self.status.config(text='Syncing clipboard...')
        self.run_async(lambda: self._sync_clipboard(content))

    def _sync_clipboard(self, content):
        self.api.post_json('/api/clipboard', {'content': content, 'direction': 'client_to_remote'})
        self.root.after(0, lambda: self.status.config(text='Clipboard synced.'))

    def show_ticket(self):
        self.clear()
        frame = Frame(self.root, padx=24, pady=24)
        frame.pack(fill=BOTH, expand=True)
        Label(frame, text='New Support Ticket', font=('Segoe UI', 18, 'bold')).pack(anchor='w', pady=(0, 12))
        Label(frame, text='Title').pack(anchor='w')
        self.ticket_title_entry = Entry(frame)
        self.ticket_title_entry.pack(fill=X, pady=(4, 12))
        Label(frame, text='Description').pack(anchor='w')
        self.ticket_description = Text(frame, height=8)
        self.ticket_description.pack(fill=BOTH, expand=True)
        Button(frame, text='Create Ticket', command=self.create_ticket).pack(fill=X, pady=(12, 6))
        Button(frame, text='Back', command=self.reload_apps).pack(fill=X)
        self.status = Label(frame, text='', fg='#666')
        self.status.pack(anchor='w', pady=(12, 0))

    def create_ticket(self):
        title = self.ticket_title_entry.get().strip()
        description = self.ticket_description.get('1.0', END).strip()
        if not title:
            messagebox.showerror('LR Remote Access', 'Ticket title is required.')
            return
        self.status.config(text='Creating ticket...')
        self.run_async(lambda: self._create_ticket(title, description))

    def _create_ticket(self, title, description):
        self.api.post_json('/api/tickets', {'title': title, 'description': description, 'priority': 'normal'})
        self.root.after(0, lambda: self.status.config(text='Ticket created.'))

    def reload_apps(self):
        self.run_async(self._reload_apps)

    def _reload_apps(self):
        apps = self.api.get_json('/portal/api/apps').get('apps', [])
        self.root.after(0, lambda: self.show_apps(apps))

    def run_async(self, target):
        def wrapped():
            try:
                target()
            except Exception as error:
                self.root.after(0, lambda: messagebox.showerror('LR Remote Access', str(error)))
                self.root.after(0, lambda: self.status.config(text=''))

        threading.Thread(target=wrapped, daemon=True).start()

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    LRRemoteAccessClient().run()
