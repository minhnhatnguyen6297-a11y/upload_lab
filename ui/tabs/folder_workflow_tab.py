from __future__ import annotations

import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from playwright_uploader import NamDinhUploaderSession, load_uploader_settings
from ui.services.folder_workflow_service import (
    extract_one_file,
    finalize_selected_records,
    load_queue_state,
    run_folder_scan,
)
from ui.widgets import StatusLine, set_tree_rows


DATE_PLACEHOLDER = "dd/mm/yyyy"


class FolderWorkflowTab(ttk.Frame):
    queue_columns = ("record_id", "contract_no", "status", "missing", "source_file")
    duplicate_columns = ("record_id", "contract_no", "status", "source_file")

    def __init__(self, master, app):
        super().__init__(master, padding=12)
        self.app = app
        self.folder_var = tk.StringVar()
        self.modified_since_var = tk.StringVar(value=DATE_PLACEHOLDER)
        self.full_rescan_var = tk.BooleanVar(value=False)
        self.extract_file_var = tk.StringVar()
        self.manifest_var = tk.StringVar()
        self.progress_var = tk.DoubleVar(value=0.0)
        self.stop_event = threading.Event()
        self.duplicate_contract_nos: set[str] = set()
        self._build()

    def _build(self) -> None:
        folder_row = ttk.Frame(self)
        folder_row.grid(row=0, column=0, sticky="ew")
        ttk.Button(folder_row, text="Chon folder", command=self.browse_folder).pack(side="left")
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True, padx=(8, 0))

        scan_row = ttk.Frame(self)
        scan_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(scan_row, text="Modified").pack(side="left")
        self.modified_entry = ttk.Entry(scan_row, textvariable=self.modified_since_var, width=14)
        self.modified_entry.pack(side="left", padx=(8, 0))
        ttk.Checkbutton(scan_row, text="Full rescan", variable=self.full_rescan_var).pack(side="left", padx=(12, 0))
        ttk.Button(scan_row, text="Scan", command=self.run_scan).pack(side="left", padx=(12, 0))
        ttk.Button(scan_row, text="Refresh queue", command=self.refresh_queue).pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.status = StatusLine(self, text="San sang.")
        self.status.grid(row=3, column=0, sticky="ew", pady=(4, 0))

        extract_row = ttk.Frame(self)
        extract_row.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(extract_row, text="Extract thu").pack(side="left")
        ttk.Entry(extract_row, textvariable=self.extract_file_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Button(extract_row, text="Chon file", command=self.browse_extract_file).pack(side="left", padx=(8, 0))
        ttk.Button(extract_row, text="Extract", command=self.run_extract).pack(side="left", padx=(8, 0))

        manifest_row = ttk.Frame(self)
        manifest_row.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(manifest_row, text="Manifest").pack(side="left")
        ttk.Entry(manifest_row, textvariable=self.manifest_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Button(manifest_row, text="Chon", command=self.browse_manifest).pack(side="left", padx=(8, 0))
        ttk.Button(manifest_row, text="Dry-run", command=self.start_upload).pack(side="left", padx=(8, 0))
        ttk.Button(manifest_row, text="Stop", command=self.stop_upload).pack(side="left", padx=(8, 0))
        ttk.Button(manifest_row, text="Finalize", command=self.finalize_selected).pack(side="left", padx=(8, 0))

        panes = ttk.PanedWindow(self, orient="vertical")
        panes.grid(row=6, column=0, sticky="nsew", pady=(10, 0))

        queue_frame = ttk.Frame(panes)
        ttk.Label(queue_frame, text="Queue local").pack(anchor="w")
        self.queue_tree = ttk.Treeview(queue_frame, columns=self.queue_columns, show="headings", selectmode="extended")
        self._setup_tree(
            self.queue_tree,
            {
                "record_id": ("ID", 70),
                "contract_no": ("So", 150),
                "status": ("Trang thai", 140),
                "missing": ("Thieu", 180),
                "source_file": ("File", 520),
            },
        )
        self.queue_tree.pack(fill="both", expand=True, pady=(4, 0))
        self.queue_tree.bind("<Double-1>", lambda _event: self.open_selected_source(self.queue_tree))
        panes.add(queue_frame, weight=3)

        duplicate_frame = ttk.Frame(panes)
        ttk.Label(duplicate_frame, text="Da co tren web").pack(anchor="w")
        self.duplicate_tree = ttk.Treeview(duplicate_frame, columns=self.duplicate_columns, show="headings", selectmode="browse")
        self._setup_tree(
            self.duplicate_tree,
            {
                "record_id": ("ID", 70),
                "contract_no": ("So", 150),
                "status": ("Local", 140),
                "source_file": ("File", 650),
            },
        )
        self.duplicate_tree.pack(fill="both", expand=True, pady=(4, 0))
        self.duplicate_tree.bind("<Double-1>", lambda _event: self.open_selected_source(self.duplicate_tree))
        panes.add(duplicate_frame, weight=1)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)

    @staticmethod
    def _setup_tree(tree: ttk.Treeview, headings: dict[str, tuple[str, int]]) -> None:
        for column, (label, width) in headings.items():
            tree.heading(column, text=label)
            tree.column(column, width=width, anchor="w")

    def browse_folder(self) -> None:
        selected = filedialog.askdirectory(title="Chon folder tong ho so")
        if selected:
            self.folder_var.set(selected)

    def browse_extract_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chon file hop dong",
            filetypes=[("Word files", ("*.doc", "*.docx"))],
        )
        if selected:
            self.extract_file_var.set(selected)

    def browse_manifest(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chon manifest",
            initialdir=str(self.app.working_dir / "runs"),
            filetypes=[("JSON files", "*.json")],
        )
        if selected:
            self.manifest_var.set(selected)
            self.refresh_queue()

    def run_scan(self) -> None:
        folder_path = Path(self.folder_var.get().strip())
        if not folder_path.exists() or not folder_path.is_dir():
            messagebox.showwarning(self.app.title(), "Folder khong hop le.")
            return
        modified_since = self.modified_since_var.get().strip()
        if modified_since.lower() == DATE_PLACEHOLDER:
            modified_since = ""
        self.progress_var.set(0.0)
        self.status.set("Dang scan...")
        self.app.log(f"[BATCH] Bat dau: {folder_path}")

        def progress(snapshot: dict) -> None:
            self.app.after(0, lambda s=snapshot: self._update_progress(s))

        def work():
            manifest, manifest_path = run_folder_scan(
                folder_path,
                modified_since=modified_since or None,
                full_rescan=bool(self.full_rescan_var.get()),
                progress_callback=progress,
                working_dir=self.app.working_dir,
            )
            self.app.after(0, lambda: self.manifest_var.set(str(manifest_path)))
            self.app.after(0, lambda: self.status.set(f"Scan xong: {manifest['stats'].get('processed_files', 0)} file"))
            self.app.after(0, self.refresh_queue)
            self.app.log(f"[BATCH] Manifest: {manifest_path}")

        self.app.run_in_thread(work, on_error_prefix="[BATCH] Loi")

    def _update_progress(self, snapshot: dict) -> None:
        processed = int(snapshot.get("processed_files") or 0)
        total = int(snapshot.get("total_files") or 0)
        stats = dict(snapshot.get("stats") or {})
        self.progress_var.set((processed / total * 100.0) if total else 0.0)
        self.status.set(
            f"processed={processed}/{total} | candidates={stats.get('candidates_found', 0)} | partial={stats.get('extract_partial', 0)}"
        )

    def run_extract(self) -> None:
        file_path = Path(self.extract_file_var.get().strip())
        if not file_path.exists() or file_path.suffix.lower() not in {".doc", ".docx"}:
            messagebox.showwarning(self.app.title(), "File Word khong hop le.")
            return
        self.status.set("Dang extract...")

        def work():
            payload, output_path = extract_one_file(file_path)
            contract_no = payload.get("web_form", {}).get("so_cong_chung", "")
            self.app.log(f"[EXTRACT] {contract_no or '(khong so)'} -> {output_path}")
            self.app.after(0, lambda: self.status.set(f"Extract xong: {output_path.name}"))

        self.app.run_in_thread(work, on_error_prefix="[EXTRACT] Loi")

    def refresh_queue(self) -> None:
        manifest_path = Path(self.manifest_var.get().strip())
        if not manifest_path.exists():
            self.status.set("Chua chon manifest.")
            set_tree_rows(self.queue_tree, [], self.queue_columns)
            set_tree_rows(self.duplicate_tree, [], self.duplicate_columns)
            return
        export_path = self.app.get_web_export_path()
        try:
            state = load_queue_state(manifest_path, export_path=export_path, working_dir=self.app.working_dir)
        except Exception as exc:
            self.status.set(f"Loi queue: {exc}")
            self.app.log(f"[UPLOAD] Loi queue: {exc}")
            return

        self.duplicate_contract_nos = state.existing_contract_nos
        set_tree_rows(self.queue_tree, state.rows, self.queue_columns)
        set_tree_rows(self.duplicate_tree, state.duplicate_rows, self.duplicate_columns)
        self.status.set(
            f"pending={len(state.rows)}/{state.total_pending} | duplicate_web={len(state.duplicate_rows)} | web_list={len(state.existing_contract_nos)}"
        )

    def start_upload(self) -> None:
        manifest_path = Path(self.manifest_var.get().strip())
        if not manifest_path.exists():
            messagebox.showwarning(self.app.title(), "Chua chon manifest.")
            return
        if not self.app.ensure_upload_runtime_ready(show_dialog=True):
            return
        self.stop_event.clear()
        exclude_contract_nos = set(self.duplicate_contract_nos or self.app.get_existing_contract_nos())
        self.status.set("Dang dry-run...")

        def work():
            session = NamDinhUploaderSession(
                load_uploader_settings(self.app.working_dir),
                working_dir=self.app.working_dir,
                log_callback=lambda msg: self.app.after(0, lambda m=msg: self.app.log(m)),
            )
            try:
                summary = session.prepare_manifest(
                    manifest_path,
                    self.stop_event,
                    exclude_contract_nos=exclude_contract_nos,
                )
            finally:
                session.close()
            self.app.after(0, lambda: self.status.set(f"Dry-run xong: prepared={summary.get('prepared_count', 0)}"))
            self.app.after(0, self.refresh_queue)

        self.app.run_in_thread(work, on_error_prefix="[UPLOAD] Loi dry-run")

    def stop_upload(self) -> None:
        self.stop_event.set()
        self.status.set("Dang dung sau record hien tai...")

    def finalize_selected(self) -> None:
        record_ids = []
        for item_id in self.queue_tree.selection():
            values = self.queue_tree.item(item_id, "values")
            if values:
                record_ids.append(int(values[0]))
        if not record_ids:
            messagebox.showwarning(self.app.title(), "Chua chon record.")
            return

        def work():
            count = finalize_selected_records(record_ids, working_dir=self.app.working_dir)
            self.app.log(f"[UPLOAD] Finalized {count} record")
            self.app.after(0, self.refresh_queue)

        self.app.run_in_thread(work, on_error_prefix="[UPLOAD] Loi finalize")

    @staticmethod
    def open_selected_source(tree: ttk.Treeview) -> None:
        selection = tree.selection()
        if not selection:
            return
        values = tree.item(selection[0], "values")
        if not values:
            return
        source_file = values[-1]
        if source_file and Path(source_file).exists() and hasattr(os, "startfile"):
            os.startfile(source_file)  # type: ignore[attr-defined]
