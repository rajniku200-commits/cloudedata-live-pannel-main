import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .api_client import ApiError
from .styles import PRIMARY, button


class MonitorTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=12, pady=12)
        button(toolbar, 'Refresh Monitor', self.refresh, PRIMARY).pack(side=tk.LEFT)

        self.summary = ttk.LabelFrame(self, text='Backend And Streaming Status')
        self.summary.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.summary_label = ttk.Label(self.summary, text='Login and refresh to check status.', justify=tk.LEFT)
        self.summary_label.pack(fill=tk.X, padx=12, pady=10)

        panes = ttk.Frame(self)
        panes.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.sessions = self._tree(panes, 'Active Sessions', ('id', 'user', 'app', 'duration'), {
            'id': ('ID', 60),
            'user': ('User ID', 90),
            'app': ('App', 220),
            'duration': ('Duration Sec', 120),
        })
        self.streams = self._tree(panes, 'Streams', ('agent', 'active', 'viewers', 'last_frame'), {
            'agent': ('Agent', 180),
            'active': ('Active', 90),
            'viewers': ('Viewers', 90),
            'last_frame': ('Last Frame', 180),
        })
        self.agents = self._tree(panes, 'Agents', ('agent', 'host', 'status', 'last_seen'), {
            'agent': ('Agent', 160),
            'host': ('Host', 160),
            'status': ('Status', 90),
            'last_seen': ('Last Seen', 180),
        })

    def _tree(self, parent, title, columns, meta):
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=12)
        for key in columns:
            label, width = meta[key]
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        return tree

    def refresh(self):
        if not self.app.require_login():
            return
        try:
            monitoring = self.app.client.monitoring()
            sessions = self.app.client.sessions()
            agents = self.app.client.agents()
            streams = self.app.client.streams()
            self._fill_summary(monitoring, sessions, agents, streams)
            self._fill_sessions(sessions)
            self._fill_agents(agents)
            self._fill_streams(streams)
            self.app.set_status('Monitor refreshed')
        except ApiError as error:
            messagebox.showerror('Monitor', str(error))

    def _fill_summary(self, monitoring, sessions, agents, streams):
        health = monitoring.get('health', {})
        agent_status = monitoring.get('agents', {})
        active_streams = sum(1 for item in streams if item.get('active'))
        self.summary_label.config(text=(
            f"CPU: {health.get('cpu_percent', 0)}%    "
            f"Memory: {health.get('memory_percent', 0)}%    "
            f"Disk: {health.get('disk_percent', 0)}%\n"
            f"Sessions: {len(sessions)} active    "
            f"Agents: {agent_status.get('online', 0)} online / {agent_status.get('total', len(agents))} total    "
            f"Streams: {active_streams} active / {len(streams)} known\n"
            f"Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ))

    def _fill_sessions(self, sessions):
        self.sessions.delete(*self.sessions.get_children())
        for item in sessions:
            self.sessions.insert('', tk.END, values=(
                item.get('id'),
                item.get('user_id'),
                item.get('published_app_name') or 'Desktop',
                item.get('duration_seconds') or 0,
            ))

    def _fill_agents(self, agents):
        self.agents.delete(*self.agents.get_children())
        for item in agents:
            self.agents.insert('', tk.END, values=(
                item.get('agent_id'),
                item.get('hostname') or item.get('ip_address') or '',
                item.get('status', ''),
                item.get('last_seen') or '',
            ))

    def _fill_streams(self, streams):
        self.streams.delete(*self.streams.get_children())
        for item in streams:
            self.streams.insert('', tk.END, values=(
                item.get('agent_id'),
                'Yes' if item.get('active') else 'No',
                item.get('viewer_count', 0),
                item.get('last_frame_at') or '',
            ))

