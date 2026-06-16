import tkinter as tk
from tkinter import ttk


BG = '#eef2f7'
SURFACE = '#ffffff'
TEXT = '#172033'
MUTED = '#637083'
PRIMARY = '#2454d6'
SUCCESS = '#218a4a'
DANGER = '#c93535'
WARNING = '#b96b00'


def apply_style(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    style.configure('.', font=('Segoe UI', 10), foreground=TEXT)
    style.configure('TFrame', background=BG)
    style.configure('Surface.TFrame', background=SURFACE)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('Muted.TLabel', background=BG, foreground=MUTED)
    style.configure('Header.TLabel', background='#14213d', foreground='white', font=('Segoe UI', 17, 'bold'))
    style.configure('Treeview', rowheight=28, fieldbackground=SURFACE, background=SURFACE)
    style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
    style.configure('TNotebook', background=BG, borderwidth=0)
    style.configure('TNotebook.Tab', padding=(14, 8), font=('Segoe UI', 10, 'bold'))


def button(parent, text, command, color=PRIMARY):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg='white',
        activebackground=color,
        activeforeground='white',
        relief=tk.FLAT,
        padx=14,
        pady=7,
        cursor='hand2',
        font=('Segoe UI', 9, 'bold'),
    )


def plain_button(parent, text, command):
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg='#d8dee9',
        fg=TEXT,
        activebackground='#c7d0df',
        relief=tk.FLAT,
        padx=12,
        pady=7,
        cursor='hand2',
        font=('Segoe UI', 9, 'bold'),
    )

