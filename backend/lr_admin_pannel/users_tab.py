import tkinter as tk
from tkinter import messagebox, ttk

from .api_client import ApiError
from .dialogs import FormDialog
from .styles import DANGER, PRIMARY, SUCCESS, WARNING, button, plain_button


class UsersTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.users = []
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=12, pady=12)
        button(toolbar, 'Add User', self.add_user, SUCCESS).pack(side=tk.LEFT, padx=(0, 8))
        button(toolbar, 'Edit', self.edit_user, WARNING).pack(side=tk.LEFT, padx=(0, 8))
        button(toolbar, 'Delete', self.delete_user, DANGER).pack(side=tk.LEFT, padx=(0, 8))
        plain_button(toolbar, 'Refresh', self.refresh).pack(side=tk.LEFT)

        columns = ('id', 'username', 'role', 'active', 'last_login')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', selectmode='browse')
        headings = {
            'id': ('ID', 70),
            'username': ('Username', 230),
            'role': ('Role', 120),
            'active': ('Active', 100),
            'last_login': ('Last Login', 210),
        }
        for key, (label, width) in headings.items():
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12), side=tk.LEFT)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 12))
        self.tree.configure(yscrollcommand=scrollbar.set)

    def refresh(self):
        if not self.app.require_login():
            return
        try:
            self.users = self.app.client.users()
            self._fill()
            self.app.on_users_loaded(self.users)
            self.app.set_status(f'Loaded {len(self.users)} users')
        except ApiError as error:
            messagebox.showerror('Users', str(error))

    def selected_user(self):
        selection = self.tree.selection()
        if not selection:
            return None
        user_id = int(self.tree.item(selection[0], 'values')[0])
        return next((user for user in self.users if int(user.get('id')) == user_id), None)

    def add_user(self):
        dialog = FormDialog(self, 'Add User', [
            {'key': 'username', 'label': 'Username'},
            {'key': 'password', 'label': 'Password', 'show': '*'},
            {'key': 'role', 'label': 'Role', 'values': ['User', 'Manager', 'Admin']},
        ])
        if not dialog.result:
            return
        try:
            self.app.client.create_user(dialog.result)
            self.refresh()
            messagebox.showinfo('Users', 'User created successfully')
        except ApiError as error:
            messagebox.showerror('Users', str(error))

    def edit_user(self):
        user = self.selected_user()
        if not user:
            messagebox.showwarning('Users', 'Select a user first')
            return
        dialog = FormDialog(self, 'Edit User', [
            {'key': 'username', 'label': 'Username'},
            {'key': 'password', 'label': 'New Password'},
            {'key': 'role', 'label': 'Role', 'values': ['User', 'Manager', 'Admin']},
            {'key': 'is_active', 'label': 'Active', 'values': ['true', 'false']},
        ], {
            'username': user.get('username', ''),
            'role': user.get('role', 'User'),
            'is_active': 'true' if user.get('is_active') else 'false',
        })
        if not dialog.result:
            return
        payload = dict(dialog.result)
        if not payload.get('password'):
            payload.pop('password', None)
        try:
            self.app.client.update_user(user['id'], payload)
            self.refresh()
            messagebox.showinfo('Users', 'User updated')
        except ApiError as error:
            messagebox.showerror('Users', str(error))

    def delete_user(self):
        user = self.selected_user()
        if not user:
            messagebox.showwarning('Users', 'Select a user first')
            return
        if not messagebox.askyesno('Delete User', f"Delete user {user.get('username')}?"):
            return
        try:
            self.app.client.delete_user(user['id'])
            self.refresh()
            messagebox.showinfo('Users', 'User deleted')
        except ApiError as error:
            messagebox.showerror('Users', str(error))

    def _fill(self):
        self.tree.delete(*self.tree.get_children())
        for user in self.users:
            self.tree.insert('', tk.END, values=(
                user.get('id'),
                user.get('username', ''),
                user.get('role', ''),
                'Yes' if user.get('is_active') else 'No',
                user.get('last_login_at') or '',
            ))

