import tkinter as tk
from tkinter import messagebox, ttk

from .api_client import ApiError
from .styles import DANGER, SUCCESS, button, plain_button


class AssignTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.users = []
        self.apps = []
        self.assigned_ids = set()
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=12)
        ttk.Label(top, text='User').pack(side=tk.LEFT)
        self.user_var = tk.StringVar()
        self.user_combo = ttk.Combobox(top, textvariable=self.user_var, state='readonly', width=38)
        self.user_combo.pack(side=tk.LEFT, padx=8)
        self.user_combo.bind('<<ComboboxSelected>>', lambda _event: self.load_for_user())
        plain_button(top, 'Refresh', self.refresh).pack(side=tk.LEFT, padx=8)

        lists = ttk.Frame(self)
        lists.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        left = ttk.LabelFrame(lists, text='Assigned Software')
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right = ttk.LabelFrame(lists, text='Available Software')
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.assigned_tree = self._tree(left)
        self.available_tree = self._tree(right)

        actions = ttk.Frame(self)
        actions.pack(fill=tk.X, padx=12, pady=(0, 12))
        button(actions, 'Assign Selected', self.assign_selected, SUCCESS).pack(side=tk.LEFT, padx=(0, 8))
        button(actions, 'Remove Selected', self.remove_selected, DANGER).pack(side=tk.LEFT)

    def _tree(self, parent):
        tree = ttk.Treeview(parent, columns=('id', 'name'), show='headings', selectmode='browse')
        tree.heading('id', text='ID')
        tree.heading('name', text='Software')
        tree.column('id', width=60, anchor=tk.W)
        tree.column('name', width=260, anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        return tree

    def refresh(self):
        if not self.app.require_login():
            return
        try:
            self.users = self.app.client.users()
            self.apps = self.app.client.apps()
            labels = [self._user_label(user) for user in self.users]
            self.user_combo['values'] = labels
            if labels and not self.user_var.get():
                self.user_var.set(labels[0])
                self.load_for_user()
            else:
                self._fill()
        except ApiError as error:
            messagebox.showerror('Assignments', str(error))

    def update_sources(self, users=None, apps=None):
        if users is not None:
            self.users = users
            self.user_combo['values'] = [self._user_label(user) for user in users]
        if apps is not None:
            self.apps = apps
        self._fill()

    def load_for_user(self):
        user = self.selected_user()
        if not user:
            return
        try:
            data = self.app.client.assignments_for_user(user['id'])
            self.assigned_ids = set(data.get('assigned_app_ids', []))
            self.apps = data.get('available_apps', self.apps)
            self._fill()
        except ApiError as error:
            messagebox.showerror('Assignments', str(error))

    def assign_selected(self):
        user = self.selected_user()
        app_id = self._selected_id(self.available_tree)
        if not user or not app_id:
            messagebox.showwarning('Assignments', 'Select user and software')
            return
        try:
            self.app.client.assign_app(app_id, user['id'])
            self.load_for_user()
            messagebox.showinfo('Assignments', 'Software assigned')
        except ApiError as error:
            messagebox.showerror('Assignments', str(error))

    def remove_selected(self):
        user = self.selected_user()
        app_id = self._selected_id(self.assigned_tree)
        if not user or not app_id:
            messagebox.showwarning('Assignments', 'Select assigned software')
            return
        try:
            self.app.client.unassign_app(app_id, user['id'])
            self.load_for_user()
            messagebox.showinfo('Assignments', 'Assignment removed')
        except ApiError as error:
            messagebox.showerror('Assignments', str(error))

    def selected_user(self):
        label = self.user_var.get()
        user_id = str(label).split(' - ', 1)[0]
        return next((user for user in self.users if str(user.get('id')) == user_id), None)

    def _selected_id(self, tree):
        selection = tree.selection()
        if not selection:
            return None
        return int(tree.item(selection[0], 'values')[0])

    def _fill(self):
        self.assigned_tree.delete(*self.assigned_tree.get_children())
        self.available_tree.delete(*self.available_tree.get_children())
        for item in self.apps:
            target = self.assigned_tree if item.get('id') in self.assigned_ids else self.available_tree
            target.insert('', tk.END, values=(item.get('id'), item.get('name', '')))

    def _user_label(self, user):
        return f"{user.get('id')} - {user.get('username')}"

