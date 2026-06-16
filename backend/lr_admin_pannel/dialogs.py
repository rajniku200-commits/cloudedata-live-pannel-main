import tkinter as tk
from tkinter import ttk


class FormDialog(tk.Toplevel):
    def __init__(self, parent, title, fields, initial=None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self.entries = {}
        self.transient(parent)
        self.grab_set()

        initial = initial or {}
        body = ttk.Frame(self, padding=18)
        body.pack(fill=tk.BOTH, expand=True)

        for row, field in enumerate(fields):
            label = field['label']
            key = field['key']
            ttk.Label(body, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
            values = field.get('values')
            if values is not None:
                widget = ttk.Combobox(body, values=values, state=field.get('state', 'readonly'), width=34)
                widget.set(initial.get(key, field.get('default', values[0] if values else '')))
            elif field.get('multiline'):
                widget = tk.Text(body, width=36, height=4)
                widget.insert('1.0', initial.get(key, field.get('default', '')))
            else:
                widget = ttk.Entry(body, width=36, show=field.get('show', ''))
                widget.insert(0, initial.get(key, field.get('default', '')))
            widget.grid(row=row, column=1, sticky=tk.EW, pady=6, padx=(12, 0))
            self.entries[key] = widget

        actions = ttk.Frame(body)
        actions.grid(row=len(fields), column=0, columnspan=2, sticky=tk.E, pady=(16, 0))
        ttk.Button(actions, text='Cancel', command=self.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(actions, text='Save', command=self._save).pack(side=tk.RIGHT)

        self.bind('<Return>', lambda _event: self._save())
        self.bind('<Escape>', lambda _event: self.destroy())
        self.wait_window(self)

    def _save(self):
        values = {}
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                values[key] = widget.get('1.0', tk.END).strip()
            else:
                values[key] = widget.get().strip()
        self.result = values
        self.destroy()

