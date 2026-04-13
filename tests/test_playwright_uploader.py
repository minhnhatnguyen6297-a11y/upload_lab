from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from openpyxl import Workbook

from batch_scan import connect_registry, get_row_by_id, upsert_registry_record
from playwright_uploader import (
    NamDinhUploaderSession,
    build_upload_form_data,
    field_value_matches,
    finalize_uploaded_records,
    get_uploader_setup_status,
    get_field_value_candidates,
    load_upload_queue,
    load_uploader_settings,
    normalize_contract_no_for_compare,
    parse_requester_sheet_csv,
    read_exported_contract_numbers,
    save_uploader_env,
    split_records_by_existing_contract_nos,
)


def make_output_json(path: Path, *, contract_no: str, file_goc: str, ten_hop_dong: str = "Hợp đồng chuyển nhượng") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "web_form": {
            "ten_hop_dong": ten_hop_dong,
            "ngay_cong_chung": "06/04/2026",
            "so_cong_chung": contract_no,
            "nhom_hop_dong": "Chuyển nhượng - Mua bán",
            "loai_tai_san": "Đất đai không có tài sản",
            "cong_chung_vien": "Phạm Minh Chi",
            "thu_ky": "Nguyễn Nhật Minh",
            "nguoi_yeu_cau": "Ông A",
            "duong_su": "BÊN A ...",
            "tai_san": "Thửa đất ...",
        },
        "raw": {
            "file_goc": file_goc,
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class _EmptyLocator:
    @property
    def first(self):
        return self

    def count(self):
        return 0


class _FakeSelectLocator:
    def __init__(self, accepted_label: str):
        self.accepted_label = accepted_label
        self.selected_label = ""

    def count(self):
        return 1

    def evaluate(self, script: str):
        if "tagName" in script:
            return "select"
        if "type" in script:
            return ""
        if "role" in script:
            return ""
        if "contenteditable" in script:
            return ""
        if "aria-disabled" in script:
            return False
        return ""

    def is_visible(self):
        return True

    def select_option(self, *, label: str):
        if label != self.accepted_label:
            raise ValueError("unexpected option")
        self.selected_label = label

    def press(self, _key: str):
        return None


class _FakePreparePage:
    def __init__(self):
        self.url = "https://example.test/create"
        self.goto_calls: list[tuple[str, str | None]] = []
        self.wait_states: list[str] = []
        self.wait_timeouts: list[int] = []
        self.screenshots: list[tuple[str, bool]] = []
        self.close_calls = 0

    def goto(self, url: str, wait_until: str | None = None):
        self.url = url
        self.goto_calls.append((url, wait_until))

    def wait_for_load_state(self, state: str):
        self.wait_states.append(state)

    def wait_for_timeout(self, timeout_ms: int):
        self.wait_timeouts.append(int(timeout_ms))

    def screenshot(self, *, path: str, full_page: bool = False):
        Path(path).write_text("img", encoding="utf-8")
        self.screenshots.append((path, full_page))

    def close(self):
        self.close_calls += 1


class PlaywrightUploaderQueueTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.workdir = self.root / "upload_lab"
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.conn = connect_registry(self.workdir / "registry.sqlite3")
        self.addCleanup(self.conn.close)
        self.env_patch = patch.dict(
            os.environ,
            {key: value for key, value in os.environ.items() if not key.startswith("ND_")},
            clear=True,
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def _seed_record(self, *, file_key: str, run_id: str, contract_no: str, status: str, output_json_path: Path) -> int:
        source_file = self.root / f"{file_key}.docx"
        source_file.write_text("dummy", encoding="utf-8")
        stat_result = source_file.stat()
        upsert_registry_record(
            self.conn,
            file_key=file_key,
            file_path=source_file,
            stat_result=stat_result,
            customer_folder="KhachA",
            contract_no=contract_no,
            status=status,
            run_id=run_id,
            output_json_path=str(output_json_path),
            reason="seed",
        )
        row = self.conn.execute("SELECT id FROM file_registry WHERE file_key = ?", (file_key,)).fetchone()
        return int(row[0])

    def test_load_upload_queue_uses_manifest_run_id_and_excludes_uploaded_success(self):
        run_id = "run123"
        other_run = "run999"
        file_goc = str(self.root / "goc1.docx")
        Path(file_goc).write_text("dummy", encoding="utf-8")
        output1 = make_output_json(self.workdir / "output" / "1.json", contract_no="111/2026/CCGD", file_goc=file_goc)
        output2 = make_output_json(self.workdir / "output" / "2.json", contract_no="222/2026/CCGD", file_goc=file_goc)
        output3 = make_output_json(self.workdir / "output" / "3.json", contract_no="333/2026/CCGD", file_goc=file_goc)

        self._seed_record(file_key="k1", run_id=run_id, contract_no="111/2026/CCGD", status="extracted", output_json_path=output1)
        self._seed_record(file_key="k2", run_id=run_id, contract_no="222/2026/CCGD", status="prepared_dry_run", output_json_path=output2)
        self._seed_record(file_key="k3", run_id=run_id, contract_no="333/2026/CCGD", status="uploaded_success", output_json_path=output3)
        self._seed_record(file_key="k4", run_id=other_run, contract_no="444/2026/CCGD", status="extracted", output_json_path=output1)

        manifest_path = self.workdir / "runs" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")

        manifest, records, total_pending = load_upload_queue(manifest_path, working_dir=self.workdir)

        self.assertEqual(manifest["run_id"], run_id)
        self.assertEqual(total_pending, 2)
        self.assertEqual([record.contract_no for record in records], ["111/2026/CCGD", "222/2026/CCGD"])

    def test_finalize_uploaded_records_marks_selected_rows(self):
        run_id = "run123"
        file_goc = str(self.root / "goc2.docx")
        Path(file_goc).write_text("dummy", encoding="utf-8")
        output_path = make_output_json(self.workdir / "output" / "x.json", contract_no="555/2026/CCGD", file_goc=file_goc)
        record_id = self._seed_record(
            file_key="finalize-key",
            run_id=run_id,
            contract_no="555/2026/CCGD",
            status="prepared_partial",
            output_json_path=output_path,
        )

        count = finalize_uploaded_records([record_id], working_dir=self.workdir)
        row = get_row_by_id(self.conn, record_id)

        self.assertEqual(count, 1)
        self.assertEqual(row["status"], "uploaded_success")
        self.assertTrue(row["uploaded_success_at"])

    def test_contract_group_aliases_match_for_dropdown_values(self):
        candidates = get_field_value_candidates("nhom_hop_dong", "Cam kết - Thỏa thuận")

        self.assertIn("Thoả thuận - Cam kết", candidates)
        self.assertIn("Cam kết - Thỏa thuận", candidates)
        self.assertIn("Thỏa thuận - Cam kết", candidates)
        self.assertTrue(
            field_value_matches("nhom_hop_dong", "Cam kết - Thỏa thuận", "Thoả thuận - Cam kết")
        )

    def test_parse_requester_sheet_csv_builds_lookup_keys(self):
        csv_text = (
            '"STT","Số CC","Ngày CC","Tên khách hàng"\n'
            '"","11","7/1/2026","Phùng Đình Việt"\n'
            '"","405","09/04/2026","Nguyễn Thị Hoa"\n'
        )

        lookup = parse_requester_sheet_csv(csv_text)

        self.assertEqual(lookup["11"], "Phùng Đình Việt")
        self.assertEqual(lookup["11/2026"], "Phùng Đình Việt")
        self.assertEqual(lookup["405/2026"], "Nguyễn Thị Hoa")

    def test_build_upload_form_data_overrides_requester_from_lookup(self):
        payload = {
            "web_form": {
                "ten_hop_dong": "Hợp đồng chuyển nhượng",
                "ngay_cong_chung": "09/04/2026",
                "so_cong_chung": "405/2026/CCGD",
                "nhom_hop_dong": "Chuyển nhượng - Mua bán",
                "loai_tai_san": "Đất đai không có tài sản",
                "nguoi_yeu_cau": "Ông A",
                "duong_su": "BÊN A ...",
                "tai_san": "Thửa đất ...",
            },
            "raw": {
                "file_goc": str(self.root / "goc_lookup.docx"),
                "ben_b": {
                    "nguoi": [
                        {
                            "gioi_tinh": "Ông",
                            "ho_ten": "Nguyễn Văn B",
                            "ngay_sinh": "01/01/1980",
                            "cccd": "012345678901",
                            "noi_cap": "CA Nam Định",
                            "ngay_cap_cccd": "01/01/2024",
                            "dia_chi": "xã A, huyện B",
                        },
                        {
                            "gioi_tinh": "Bà",
                            "ho_ten": "Nguyễn Thị Hoa",
                            "ngay_sinh": "02/02/1985",
                            "cccd": "123456789012",
                            "noi_cap": "CA Nam Định",
                            "ngay_cap_cccd": "02/02/2024",
                            "dia_chi": "xã C, huyện D",
                        },
                    ]
                },
            },
        }

        form_data = build_upload_form_data(
            payload,
            requester_lookup={"405/2026": "Nguyễn Thị Hoa"},
        )

        self.assertIn("Nguyễn Thị Hoa", form_data["nguoi_yeu_cau"])
        self.assertIn("Can cuoc so:", form_data["nguoi_yeu_cau"])

    def test_read_exported_contract_numbers_reads_column_a(self):
        export_path = self.root / "So_cong_chung.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet["A1"] = "SỐ CÔNG CHỨNG"
        sheet["A2"] = "405/2026"
        sheet["A3"] = " 413/2026/CCGD "
        sheet["A4"] = None
        sheet["A5"] = "414/2026"
        sheet["B2"] = "bo qua cot khac"
        workbook.save(export_path)
        workbook.close()

        contract_nos = read_exported_contract_numbers(export_path)

        self.assertEqual(contract_nos, {"405/2026", "413/2026", "414/2026"})

    def test_split_records_by_existing_contract_nos_filters_duplicates(self):
        run_id = "run-dup"
        file_goc = str(self.root / "goc3.docx")
        Path(file_goc).write_text("dummy", encoding="utf-8")
        output1 = make_output_json(self.workdir / "output" / "dup1.json", contract_no="405/2026/CCGD", file_goc=file_goc)
        output2 = make_output_json(self.workdir / "output" / "dup2.json", contract_no="999/2026/CCGD", file_goc=file_goc)

        self._seed_record(file_key="dup-k1", run_id=run_id, contract_no="405/2026/CCGD", status="extracted", output_json_path=output1)
        self._seed_record(file_key="dup-k2", run_id=run_id, contract_no="999/2026/CCGD", status="prepared_partial", output_json_path=output2)

        manifest_path = self.workdir / "runs" / "dup_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")

        _, records, _ = load_upload_queue(manifest_path, working_dir=self.workdir)
        filtered, duplicates = split_records_by_existing_contract_nos(records, {"405/2026"})

        self.assertEqual([record.contract_no for record in duplicates], ["405/2026/CCGD"])
        self.assertEqual([record.contract_no for record in filtered], ["999/2026/CCGD"])

    def test_normalize_contract_no_for_compare_strips_inheritance_suffixes(self):
        self.assertEqual(normalize_contract_no_for_compare("2233/2025/TCDS/CCGD"), "2233/2025")
        self.assertEqual(normalize_contract_no_for_compare("2433.2025/PCDS/CCGD"), "2433/2025")

    def test_save_and_load_uploader_env_roundtrip(self):
        save_uploader_env(
            {
                "ND_BASE_URL": "https://example.test",
                "ND_LOGIN_URL": "https://example.test/login",
                "ND_CREATE_URL": "https://example.test/create",
                "ND_USERNAME": "operator",
                "ND_PASSWORD": "secret",
                "ND_STORAGE_STATE_PATH": "nd_storage_state.json",
                "ND_MAX_PREPARED_TABS": "7",
                "ND_POST_PREPARE_DELAY_MS": "2500",
            },
            base_dir=self.workdir,
        )

        settings = load_uploader_settings(self.workdir)

        self.assertEqual(settings.base_url, "https://example.test")
        self.assertEqual(settings.login_url, "https://example.test/login")
        self.assertEqual(settings.create_url, "https://example.test/create")
        self.assertEqual(settings.username, "operator")
        self.assertEqual(settings.password, "secret")
        self.assertEqual(settings.max_prepared_tabs, 7)
        self.assertEqual(settings.post_prepare_delay_ms, 2500)
        self.assertEqual(settings.storage_state_path, (self.workdir / "nd_storage_state.json").resolve())

    def test_get_uploader_setup_status_tracks_storage_state(self):
        save_uploader_env(
            {
                "ND_BASE_URL": "https://example.test",
                "ND_LOGIN_URL": "https://example.test/login",
                "ND_CREATE_URL": "https://example.test/create",
                "ND_USERNAME": "operator",
                "ND_PASSWORD": "secret",
                "ND_STORAGE_STATE_PATH": "nd_storage_state.json",
            },
            base_dir=self.workdir,
        )

        status = get_uploader_setup_status(self.workdir)
        self.assertFalse(status["ready"])
        self.assertFalse(status["storage_state_exists"])

        storage_state = self.workdir / "nd_storage_state.json"
        storage_state.write_text("{}", encoding="utf-8")

        status = get_uploader_setup_status(self.workdir)
        self.assertTrue(status["ready"])
        self.assertTrue(status["storage_state_exists"])
        self.assertEqual(status["storage_state_path"], storage_state.resolve())

    def test_prepare_manifest_emits_structured_progress_and_updates_registry(self):
        run_id = "run-progress"
        source_path = self.root / "source.docx"
        source_path.write_text("dummy", encoding="utf-8")
        duplicate_source = self.root / "duplicate.docx"
        duplicate_source.write_text("dummy", encoding="utf-8")
        output_ok = make_output_json(
            self.workdir / "output" / "ok.json",
            contract_no="501/2026/CCGD",
            file_goc=str(source_path),
        )
        output_dup = make_output_json(
            self.workdir / "output" / "dup.json",
            contract_no="999/2026/CCGD",
            file_goc=str(duplicate_source),
        )
        record_id = self._seed_record(
            file_key="prepare-ok",
            run_id=run_id,
            contract_no="501/2026/CCGD",
            status="extracted",
            output_json_path=output_ok,
        )
        self._seed_record(
            file_key="prepare-dup",
            run_id=run_id,
            contract_no="999/2026/CCGD",
            status="extracted",
            output_json_path=output_dup,
        )

        manifest_path = self.workdir / "runs" / "prepare_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")

        save_uploader_env(
            {
                "ND_BASE_URL": "https://example.test",
                "ND_LOGIN_URL": "https://example.test/login",
                "ND_CREATE_URL": "https://example.test/create",
                "ND_USERNAME": "operator",
                "ND_PASSWORD": "secret",
                "ND_STORAGE_STATE_PATH": "nd_storage_state.json",
                "ND_MAX_PREPARED_TABS": "5",
                "ND_POST_PREPARE_DELAY_MS": "0",
            },
            base_dir=self.workdir,
        )
        (self.workdir / "nd_storage_state.json").write_text("{}", encoding="utf-8")
        session = NamDinhUploaderSession(
            load_uploader_settings(self.workdir),
            working_dir=self.workdir,
            log_callback=lambda _msg: None,
        )

        def fake_prepare(record, artifact_dir):
            contract_key = record.contract_no.replace("/", "_")
            screenshot = artifact_dir / f"before_save_{contract_key}.png"
            debug_json = artifact_dir / f"debug_{contract_key}.json"
            screenshot.write_text("img", encoding="utf-8")
            debug_json.write_text("{}", encoding="utf-8")
            return {
                "status": "prepared_dry_run",
                "verify_json": json.dumps({"fields": {"so_cong_chung": {"success": True}}}),
                "artifact_dir": str(artifact_dir),
                "screenshot": str(screenshot),
                "debug_json": str(debug_json),
            }

        progress_events: list[dict] = []
        with patch.object(NamDinhUploaderSession, "ensure_authenticated", return_value=None), patch.object(
            NamDinhUploaderSession,
            "_prepare_record",
            side_effect=fake_prepare,
        ):
            summary = session.prepare_manifest(
                manifest_path,
                Event(),
                exclude_contract_nos={"999/2026"},
                progress_callback=progress_events.append,
            )

        self.assertEqual(summary["prepared_count"], 1)
        self.assertEqual(summary["excluded_duplicates"], 1)
        self.assertTrue((Path(summary["artifact_dir"]) / "upload_manifest.json").exists())

        events_by_name = [event["event"] for event in progress_events]
        self.assertEqual(events_by_name[0], "queue_loaded")
        self.assertIn("record_started", events_by_name)
        self.assertIn("record_prepared", events_by_name)
        self.assertEqual(events_by_name[-1], "finished")

        row = get_row_by_id(self.conn, record_id)
        self.assertEqual(row["status"], "prepared_dry_run")
        self.assertEqual(row["reason"], "Dry-run prepared")
        self.assertTrue(row["artifact_dir"])
        self.assertTrue(json.loads(row["verify_json"]))
        self.assertIn("Hay ra soat, luu, finalize", summary["message"])
        self.assertNotIn("dong browser", summary["message"])

    def test_prepare_record_keeps_page_open_for_manual_review(self):
        source_path = self.root / "prepare_keep_open.docx"
        source_path.write_text("dummy", encoding="utf-8")
        artifact_dir = self.workdir / "upload_runs" / "keep_open"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        save_uploader_env(
            {
                "ND_BASE_URL": "https://example.test",
                "ND_LOGIN_URL": "https://example.test/login",
                "ND_CREATE_URL": "https://example.test/create",
                "ND_USERNAME": "operator",
                "ND_PASSWORD": "secret",
                "ND_STORAGE_STATE_PATH": "nd_storage_state.json",
                "ND_POST_PREPARE_DELAY_MS": "0",
            },
            base_dir=self.workdir,
        )
        (self.workdir / "nd_storage_state.json").write_text("{}", encoding="utf-8")

        session = NamDinhUploaderSession(
            load_uploader_settings(self.workdir),
            working_dir=self.workdir,
            log_callback=lambda _msg: None,
        )

        page = _FakePreparePage()
        session.context = SimpleNamespace(new_page=lambda: page)
        record = SimpleNamespace(
            contract_no="888/2026/CCGD",
            source_file=source_path,
            upload_form={
                "so_cong_chung": "888/2026/CCGD",
                "ten_hop_dong": "Hợp đồng demo",
                "nhom_hop_dong": "Chuyển nhượng - Mua bán",
                "loai_tai_san": "Đất đai không có tài sản",
                "tai_san": "Thửa đất demo",
            },
        )

        with patch.object(session, "_is_login_page", return_value=False), patch.object(
            session,
            "_fill_text",
            return_value=True,
        ), patch.object(
            session,
            "_fill_dropdown",
            return_value=True,
        ), patch.object(
            session,
            "_fill_editor",
            return_value=True,
        ), patch.object(
            session,
            "_verify_record",
            return_value=({"fields": {"so_cong_chung": {"success": True}}}, False),
        ):
            result = session._prepare_record(record, artifact_dir)

        self.assertEqual(result["status"], "prepared_dry_run")
        self.assertEqual(page.close_calls, 0)
        self.assertTrue(Path(result["screenshot"]).exists())
        self.assertTrue(Path(result["debug_json"]).exists())

    def test_fill_dropdown_supports_native_select(self):
        session = NamDinhUploaderSession(
            load_uploader_settings(self.workdir),
            working_dir=self.workdir,
            log_callback=lambda _msg: None,
        )
        locator = _FakeSelectLocator("Hợp đồng chuyển nhượng")
        page = SimpleNamespace(
            wait_for_timeout=lambda _ms: None,
            keyboard=SimpleNamespace(press=lambda _key: None),
            get_by_role=lambda *args, **kwargs: _EmptyLocator(),
            get_by_text=lambda *args, **kwargs: _EmptyLocator(),
        )

        with patch.object(session, "_resolve_control_locator", return_value=(locator, "fake_select")), patch.object(
            session,
            "_read_field_value",
            side_effect=lambda *_args, **_kwargs: locator.selected_label,
        ):
            self.assertTrue(session._fill_dropdown(page, "ten_hop_dong", "Hợp đồng chuyển nhượng"))


if __name__ == "__main__":
    unittest.main()
