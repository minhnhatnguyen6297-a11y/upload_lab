from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def clear_tree(tree: ttk.Treeview) -> None:
    for item_id in tree.get_children():
        tree.delete(item_id)


def set_tree_rows(tree: ttk.Treeview, rows: list[dict], columns: tuple[str, ...]) -> None:
    clear_tree(tree)
    for row in rows:
        values = [str(row.get(column, "")) for column in columns]
        tree.insert("", "end", values=values)


class LogPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="Log").pack(anchor="w")
        self.text = tk.Text(self, height=8, wrap="word")
        self.text.pack(fill="both", expand=True, pady=(4, 0))
        self.text.configure(state="disabled")

    def append(self, message: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", message.rstrip() + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")


class StatusLine(ttk.Label):
    def __init__(self, master, *, text: str = ""):
        self.var = tk.StringVar(value=text)
        super().__init__(master, textvariable=self.var, anchor="w")

    def set(self, text: str) -> None:
        self.var.set(text)
