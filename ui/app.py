from __future__ import annotations

import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from batch_scan import BASE_DIR
from playwright_uploader import (
    NamDinhUploaderSession,
    ensure_uploader_env_file,
    get_uploader_setup_status,
    load_uploader_settings,
    probe_playwright_runtime,
    read_uploader_env,
    save_uploader_env,
)
from ui.tabs import FolderWorkflowTab, WebListTab
from ui.widgets import LogPanel


APP_TITLE = "Upload Lab"


class UploadLabApp(tk.Tk):
    def __init__(self, *, working_dir: Path = BASE_DIR):
        super().__init__()
        self.working_dir = Path(working_dir)
        self._busy = False
        self._main_thread = threading.current_thread()
        self.playwright_ready = False
        self.playwright_message = ""
        self.uploader_status: dict[str, object] = {}

        self.title(APP_TITLE)
        self.geometry("1160x820")
        self.minsize(980, 680)
        ensure_uploader_env_file(self.working_dir)
        self.refresh_runtime_status()
        self._build()

    def _build(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        self.tabs = ttk.Notebook(container)
        self.tabs.pack(fill="both", expand=True)
        self.web_tab = WebListTab(self.tabs, self)
        self.folder_tab = FolderWorkflowTab(self.tabs, self)
        self.tabs.add(self.web_tab, text="Web & Danh sach")
        self.tabs.add(self.folder_tab, text="Folder dang chon")

        self.log_panel = LogPanel(container)
        self.log_panel.pack(fill="both", expand=False, pady=(10, 0))
        self.log(self.runtime_summary())

    def runtime_summary(self) -> str:
        ready = bool(self.playwright_ready and self.uploader_status.get("ready"))
        status = "ready" if ready else "not_ready"
        message = str(self.uploader_status.get("message") or self.playwright_message or "")
        return f"[SETUP] {status} | {message}"

    def refresh_runtime_status(self) -> None:
        self.playwright_ready, self.playwright_message = probe_playwright_runtime()
        self.uploader_status = get_uploader_setup_status(self.working_dir)

    def log(self, message: str) -> None:
        if threading.current_thread() is not self._main_thread:
            self.after(0, lambda: self.log(message))
            return
        self.log_panel.append(message)

    def run_in_thread(self, target, *, on_error_prefix: str) -> None:
        if self._busy:
            self.log("[UI] Dang co tac vu dang chay.")
            return
        self._set_busy(True)

        def worker():
            try:
                target()
            except Exception as exc:  # pragma: no cover - UI plumbing
                detail = f"{on_error_prefix}: {exc}\n{traceback.format_exc()}"
                self.log(detail)
                self.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc)))
            finally:
                self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.configure(cursor="watch" if value else "")

    def get_web_export_path(self) -> Path | None:
        return self.web_tab.get_export_path()

    def get_existing_contract_nos(self) -> set[str]:
        return self.web_tab.get_existing_contract_nos()

    def ensure_upload_runtime_ready(self, *, show_dialog: bool = False) -> bool:
        self.refresh_runtime_status()
        ready = bool(self.playwright_ready and self.uploader_status.get("ready"))
        if ready:
            return True
        message = self.runtime_summary()
        self.log(message)
        if show_dialog:
            messagebox.showwarning(APP_TITLE, message)
        return False

    def open_upload_config_dialog(self) -> None:
        self.refresh_runtime_status()
        values = read_uploader_env(self.working_dir, ensure_exists=True)
        dialog = tk.Toplevel(self)
        dialog.title("Cau hinh uploader")
        dialog.transient(self)
        dialog.grab_set()
        dialog.columnconfigure(1, weight=1)

        keys = [
            "ND_BASE_URL",
            "ND_LOGIN_URL",
            "ND_CREATE_URL",
            "ND_USERNAME",
            "ND_PASSWORD",
            "ND_STORAGE_STATE_PATH",
            "ND_BROWSER_CHANNEL",
            "ND_MAX_PREPARED_TABS",
        ]
        field_vars: dict[str, tk.StringVar] = {}
        for row_index, key in enumerate(keys):
            ttk.Label(dialog, text=key).grid(row=row_index, column=0, sticky="w", padx=10, pady=4)
            var = tk.StringVar(value=str(values.get(key, "")))
            field_vars[key] = var
            entry = ttk.Entry(dialog, textvariable=var, show="*" if key == "ND_PASSWORD" else "")
            entry.grid(row=row_index, column=1, sticky="ew", padx=10, pady=4)

        status_var = tk.StringVar(value=self.runtime_summary())
        ttk.Label(dialog, textvariable=status_var).grid(row=len(keys), column=0, columnspan=2, sticky="ew", padx=10, pady=(8, 4))

        button_row = ttk.Frame(dialog)
        button_row.grid(row=len(keys) + 1, column=0, columnspan=2, sticky="e", padx=10, pady=10)

        def save_only() -> None:
            save_uploader_env({key: var.get() for key, var in field_vars.items()}, base_dir=self.working_dir)
            self.refresh_runtime_status()
            status_var.set(self.runtime_summary())
            self.log("[SETUP] Da luu cau hinh uploader.")

        def save_and_login() -> None:
            save_only()

            def work():
                session = NamDinhUploaderSession(load_uploader_settings(self.working_dir), working_dir=self.working_dir, log_callback=self.log)
                try:
                    session.ensure_authenticated()
                finally:
                    session.close()
                self.refresh_runtime_status()
                self.after(0, lambda: status_var.set(self.runtime_summary()))
                self.log("[SETUP] Dang nhap xong.")

            self.run_in_thread(work, on_error_prefix="[SETUP] Loi dang nhap")

        ttk.Button(button_row, text="Luu", command=save_only).pack(side="left")
        ttk.Button(button_row, text="Luu va dang nhap", command=save_and_login).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Dong", command=dialog.destroy).pack(side="left", padx=(8, 0))


def main() -> int:
    app = UploadLabApp()
    app.mainloop()
    return 0
