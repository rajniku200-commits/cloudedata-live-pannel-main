import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .api_client import ApiClient
from .assign_tab import AssignTab
from .config import DEFAULT_BACKEND_URL, SettingsStore
from .monitor_tab import MonitorTab
from .settings_tab import SettingsTab
from .software_tab import SoftwareTab
from .styles import apply_style
from .urls_tab import UrlsTab
from .users_tab import UsersTab


class AdminPanel:
    def __init__(self, root):
        self.root = root
        self.root.title('LR Admin Panel')
        self.root.geometry('1180x760')
        self.store = SettingsStore()
        self.settings = self.store.load()
        self.client = ApiClient(self.settings.get('backend_url', DEFAULT_BACKEND_URL))
        self.logged_in = False

        apply_style(root)
        self._build()

    def _build(self):
        header = tk.Frame(self.root, bg='#14213d', height=66)
        header.pack(fill=tk.X)
        ttk.Label(header, text='LR ADMIN PANEL', style='Header.TLabel').pack(side=tk.LEFT, padx=18, pady=16)
        self.login_label = tk.Label(header, text='Not logged in', bg='#14213d', fg='white', font=('Segoe UI', 10))
        self.login_label.pack(side=tk.RIGHT, padx=18)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.users_tab = UsersTab(self.notebook, self)
        self.software_tab = SoftwareTab(self.notebook, self)
        self.assign_tab = AssignTab(self.notebook, self)
        self.urls_tab = UrlsTab(self.notebook, self)
        self.monitor_tab = MonitorTab(self.notebook, self)
        self.settings_tab = SettingsTab(self.notebook, self)

        self.notebook.add(self.users_tab, text='Users')
        self.notebook.add(self.software_tab, text='Software')
        self.notebook.add(self.assign_tab, text='Assign')
        self.notebook.add(self.urls_tab, text='URLs')
        self.notebook.add(self.monitor_tab, text='Monitor')
        self.notebook.add(self.settings_tab, text='Settings')

        footer = tk.Frame(self.root, bg='#d8dee9', height=30)
        footer.pack(fill=tk.X)
        self.status_label = tk.Label(footer, text='Ready', bg='#d8dee9', fg='#172033', anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=12, pady=5)

    def set_status(self, text):
        self.status_label.config(text=text)

    def set_logged_in(self, value, username=''):
        self.logged_in = value
        self.login_label.config(text=f'Logged in: {username}' if value else 'Not logged in')

    def require_login(self):
        if self.logged_in:
            return True
        messagebox.showwarning('Login Required', 'Open Settings tab and login as an Admin first.')
        self.notebook.select(self.settings_tab)
        return False

    def refresh_all(self):
        self.users_tab.refresh()
        self.software_tab.refresh()
        self.assign_tab.refresh()
        self.urls_tab.refresh()
        self.monitor_tab.refresh()

    def on_users_loaded(self, users):
        self.assign_tab.update_sources(users=users)
        self.urls_tab.update_users(users)

    def on_apps_loaded(self, apps):
        self.assign_tab.update_sources(apps=apps)


def main():
    root = tk.Tk()
    AdminPanel(root)
    root.mainloop()


if __name__ == '__main__':
    if os.environ.get('DISPLAY') or os.environ.get('LR_ADMIN_XVFB'):
        main()
    else:
        xvfb_run = shutil.which('xvfb-run')
        if xvfb_run:
            env = os.environ.copy()
            env['LR_ADMIN_XVFB'] = '1'
            raise SystemExit(subprocess.call([xvfb_run, '-a', sys.executable, '-m', 'backend.lr_admin_pannel.main'], env=env))
        raise SystemExit(
            'LR Admin Panel is a Tkinter desktop app, but no display is available.\n'
            'Install Xvfb, then run this command again:\n'
            '  sudo apt-get update && sudo apt-get install -y xvfb\n'
            'Or run it from a desktop/VNC session with DISPLAY set.'
        )
