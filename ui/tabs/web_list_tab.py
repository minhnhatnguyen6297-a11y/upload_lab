from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from playwright_uploader import default_export_from_date, default_export_to_date, download_contract_book_export
from ui.services.web_list_service import (
    ContractListRow,
    find_missing_contract_numbers,
    lookup_exported_contract_no,
    read_exported_contract_rows,
)
from ui.widgets import StatusLine, set_tree_rows


class WebListTab(ttk.Frame):
    row_columns = ("row_index", "contract_no", "raw_value")
    missing_columns = ("contract_no", "year", "ordinal")

    def __init__(self, master, app):
        super().__init__(master, padding=12)
        self.app = app
        self.export_path_var = tk.StringVar()
        self.from_date_var = tk.StringVar(value=default_export_from_date())
        self.to_date_var = tk.StringVar(value=default_export_to_date())
        self.lookup_var = tk.StringVar()
        self.rows: list[ContractListRow] = []
        self._build()

    def _build(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Cau hinh", command=self.app.open_upload_config_dialog).pack(side="left")
        ttk.Label(toolbar, text="Tu").pack(side="left", padx=(12, 4))
        ttk.Entry(toolbar, textvariable=self.from_date_var, width=12).pack(side="left")
        ttk.Label(toolbar, text="Den").pack(side="left", padx=(8, 4))
        ttk.Entry(toolbar, textvariable=self.to_date_var, width=12).pack(side="left")
        ttk.Button(toolbar, text="Tai Excel", command=self.download_export).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Chon file", command=self.browse_export).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Doc file", command=self.load_export).pack(side="left", padx=(8, 0))

        path_row = ttk.Frame(self)
        path_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Entry(path_row, textvariable=self.export_path_var).pack(side="left", fill="x", expand=True)

        lookup_row = ttk.Frame(self)
        lookup_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(lookup_row, text="Tra so").pack(side="left")
        ttk.Entry(lookup_row, textvariable=self.lookup_var, width=22).pack(side="left", padx=(8, 0))
        ttk.Button(lookup_row, text="Tra", command=self.lookup_contract_no).pack(side="left", padx=(8, 0))
        self.status = StatusLine(lookup_row, text="Chua doc Excel.")
        self.status.pack(side="left", padx=(12, 0), fill="x", expand=True)

        panes = ttk.PanedWindow(self, orient="vertical")
        panes.grid(row=3, column=0, sticky="nsew", pady=(10, 0))

        rows_frame = ttk.Frame(panes)
        ttk.Label(rows_frame, text="Danh sach Excel").pack(anchor="w")
        self.rows_tree = ttk.Treeview(rows_frame, columns=self.row_columns, show="headings", height=14)
        self._setup_tree(
            self.rows_tree,
            {
                "row_index": ("Dong", 80),
                "contract_no": ("So cong chung", 160),
                "raw_value": ("Gia tri goc", 360),
            },
        )
        self.rows_tree.pack(fill="both", expand=True, pady=(4, 0))
        panes.add(rows_frame, weight=3)

        missing_frame = ttk.Frame(panes)
        ttk.Label(missing_frame, text="So bi ho").pack(anchor="w")
        self.missing_tree = ttk.Treeview(missing_frame, columns=self.missing_columns, show="headings", height=8)
        self._setup_tree(
            self.missing_tree,
            {
                "contract_no": ("So thieu", 160),
                "year": ("Nam", 80),
                "ordinal": ("STT", 80),
            },
        )
        self.missing_tree.pack(fill="both", expand=True, pady=(4, 0))
        panes.add(missing_frame, weight=1)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

    @staticmethod
    def _setup_tree(tree: ttk.Treeview, headings: dict[str, tuple[str, int]]) -> None:
        for column, (label, width) in headings.items():
            tree.heading(column, text=label)
            tree.column(column, width=width, anchor="w")

    def get_export_path(self) -> Path | None:
        value = self.export_path_var.get().strip()
        return Path(value) if value else None

    def get_existing_contract_nos(self) -> set[str]:
        return {row.contract_no for row in self.rows}

    def browse_export(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chon Excel so cong chung",
            filetypes=[("Excel files", ("*.xlsx", "*.xlsm", "*.xls"))],
        )
        if selected:
            self.export_path_var.set(selected)
            self.load_export()

    def download_export(self) -> None:
        from_date = self.from_date_var.get().strip()
        to_date = self.to_date_var.get().strip()
        self.status.set("Dang tai Excel...")
        self.app.log(f"[WEB] Tai Excel from={from_date} to={to_date}")

        def work():
            export_path = download_contract_book_export(
                from_date=from_date,
                to_date=to_date,
                working_dir=self.app.working_dir,
                log_callback=lambda msg: self.app.after(0, lambda m=msg: self.app.log(m)),
            )
            self.app.after(0, lambda: self.export_path_var.set(str(export_path)))
            self.app.after(0, self.load_export)

        self.app.run_in_thread(work, on_error_prefix="[WEB] Loi tai Excel")

    def load_export(self) -> None:
        export_path = self.get_export_path()
        if not export_path:
            self.status.set("Chua chon Excel.")
            return
        try:
            self.rows = read_exported_contract_rows(
                export_path,
                from_date=self.from_date_var.get().strip(),
                to_date=self.to_date_var.get().strip(),
            )
            missing = find_missing_contract_numbers(self.rows)
        except Exception as exc:
            self.status.set(f"Loi doc Excel: {exc}")
            self.app.log(f"[WEB] Loi doc Excel {export_path}: {exc}")
            messagebox.showerror(self.app.title(), str(exc))
            return

        set_tree_rows(
            self.rows_tree,
            [
                {"row_index": row.row_index, "contract_no": row.contract_no, "raw_value": row.raw_value}
                for row in self.rows
            ],
            self.row_columns,
        )
        set_tree_rows(
            self.missing_tree,
            [
                {"contract_no": item.contract_no, "year": item.year, "ordinal": item.ordinal}
                for item in missing
            ],
            self.missing_columns,
        )
        self.status.set(f"Excel={len(self.rows)} so | ho={len(missing)}")
        self.app.log(f"[WEB] Da doc Excel: rows={len(self.rows)} missing={len(missing)}")

    def lookup_contract_no(self) -> None:
        result = lookup_exported_contract_no(self.rows, self.lookup_var.get())
        self.status.set(result.message)
        if result.found:
            for item_id in self.rows_tree.get_children():
                values = self.rows_tree.item(item_id, "values")
                if len(values) > 1 and values[1] == result.contract_no:
                    self.rows_tree.selection_set(item_id)
                    self.rows_tree.see(item_id)
                    break
