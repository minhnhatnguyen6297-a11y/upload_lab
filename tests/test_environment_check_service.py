from __future__ import annotations

import json
from contextlib import redirect_stdout
import io
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from playwright_uploader import NamDinhUploaderSession, UploaderSettings
from ui.services.environment_check_service import (
    BLOCKED,
    PASSED,
    WARNING,
    _check_disk_space,
    _check_operating_system,
    finalize_report,
    redact_text,
    run_environment_checks,
    safe_url,
)


class EnvironmentCheckServiceTests(unittest.TestCase):
    def test_safe_url_removes_query_and_fragment(self):
        value = safe_url("https://example.test/dang-nhap?token=secret#form")

        self.assertEqual(value, "https://example.test/dang-nhap")
        self.assertNotIn("secret", value)

    def test_safe_url_removes_userinfo_and_keeps_port(self):
        value = safe_url("https://operator:secret@example.test:8443/login?token=secret")

        self.assertEqual(value, "https://example.test:8443/login")
        self.assertNotIn("operator", value)
        self.assertNotIn("secret", value)

    def test_redact_text_removes_urls_and_secret_shaped_values(self):
        value = redact_text(
            "GET https://example.test/login?access_token=secret password=top-secret"
        )

        self.assertNotIn("secret", value)
        self.assertIn("https://example.test/login", value)
        self.assertIn("password=<redacted>", value)

    def test_run_environment_checks_returns_json_safe_report(self):
        class Response:
            status = 200

            def close(self):
                return None

        def finder(_module):
            return object()

        def resolver(_host, _port, **_kwargs):
            return [(None, None, None, None, None)]

        def opener(_url, **_kwargs):
            return Response()

        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            "os.environ", {}, clear=True
        ):
            report = run_environment_checks(
                Path(temp_dir),
                "https://example.test/dang-nhap?token=secret",
                finder=finder,
                resolver=resolver,
                opener=opener,
            )

        self.assertIn(report["overall"], {PASSED, WARNING})
        self.assertEqual(report["base_url"], "https://example.test/dang-nhap")
        self.assertEqual(
            {step["key"] for step in report["steps"]},
            {
                "operating_system",
                "workspace",
                "disk_space",
                "python_dependencies",
                "network",
                "proxy_policy",
            },
        )
        json.dumps(report)

    def test_network_failure_is_blocked_without_query_data(self):
        def resolver(_host, _port, **_kwargs):
            return [(None, None, None, None, None)]

        def opener(_url, **_kwargs):
            raise TimeoutError("timeout at https://example.test/?token=secret")

        with tempfile.TemporaryDirectory() as temp_dir:
            report = run_environment_checks(
                Path(temp_dir),
                "https://example.test/?token=secret",
                finder=lambda _module: object(),
                resolver=resolver,
                opener=opener,
            )

        network = next(step for step in report["steps"] if step["key"] == "network")
        self.assertEqual(network["status"], BLOCKED)
        self.assertNotIn("secret", json.dumps(network))

    def test_windows_10_is_compatibility_warning(self):
        with patch("ui.services.environment_check_service.platform.system", return_value="Windows"), patch(
            "ui.services.environment_check_service.platform.machine", return_value="AMD64"
        ), patch(
            "ui.services.environment_check_service.platform.release", return_value="10"
        ), patch("ui.services.environment_check_service._memory_gib", return_value=8.0):
            step = _check_operating_system()

        self.assertEqual(step.status, WARNING)
        self.assertIn("Windows 10", step.message)

    def test_low_disk_space_is_blocked(self):
        usage = SimpleNamespace(free=400 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "ui.services.environment_check_service.shutil.disk_usage", return_value=usage
        ):
            step = _check_disk_space(Path(temp_dir))

        self.assertEqual(step.status, BLOCKED)
        self.assertIn("500 MB", step.message)

    def test_finalize_report_writes_redacted_diagnostics(self):
        report = {
            "generated_at": "2026-09-05T00:00:00+00:00",
            "base_url": "https://example.test/login",
            "overall": WARNING,
            "steps": [],
            "diagnostics_path": "",
        }
        browser_result = {
            "status": PASSED,
            "message": "Opened https://example.test/login?token=secret",
            "guidance": "Continue login",
            "url": "https://example.test/login?token=secret",
            "browser_channel": "chromium",
            "reused_browser": True,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            final = finalize_report(report, browser_result, Path(temp_dir))
            diagnostic_path = Path(final["diagnostics_path"])
            content = diagnostic_path.read_text(encoding="utf-8")

        self.assertEqual(final["overall"], PASSED)
        self.assertTrue(diagnostic_path.name.startswith("environment-check-"))
        self.assertNotIn("secret", content)
        self.assertNotIn("?token", content)

    def test_preflight_reuses_existing_anchor_page(self):
        class FakePage:
            url = "https://example.test/dang-nhap"

            def __init__(self):
                self.goto_calls = []

            def is_closed(self):
                return False

            def goto(self, url, *, wait_until, timeout):
                self.goto_calls.append((url, wait_until, timeout))

            def on(self, *_args):
                return None

        page = FakePage()
        settings = UploaderSettings(
            base_url="https://example.test",
            login_url="https://example.test/dang-nhap?redirect=secret",
            create_url="https://example.test/create",
            storage_state_path=Path("nd_storage_state.json"),
        )
        session = NamDinhUploaderSession(settings, working_dir=Path(tempfile.gettempdir()), log_callback=lambda _msg: None)
        session.anchor_page = page

        with patch.object(session, "_ensure_context"), patch.object(
            session, "_begin_login_tracking"
        ) as tracking:
            result = session.preflight_login()

        self.assertEqual(result["status"], PASSED)
        self.assertTrue(result["reused_browser"])
        self.assertEqual(page.goto_calls[0][2], 15000)
        tracking.assert_called_once_with(page)
        self.assertNotIn("secret", json.dumps(result))

    def test_preflight_returns_browser_error_on_cp1252_console(self):
        class Cp1252Console:
            encoding = "cp1252"

            def __init__(self):
                self.text = io.StringIO()

            def write(self, value):
                value.encode(self.encoding)
                return self.text.write(value)

            def flush(self):
                return None

            def getvalue(self):
                return self.text.getvalue()

        settings = UploaderSettings(
            base_url="https://example.test",
            login_url="https://example.test/dang-nhap",
            create_url="https://example.test/create",
            storage_state_path=Path("nd_storage_state.json"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            session = NamDinhUploaderSession(settings, working_dir=Path(temp_dir))
            console = Cp1252Console()
            with patch.object(
                session,
                "_ensure_context",
                side_effect=RuntimeError(
                    "BrowserType.launch: Executable doesn't exist; run playwright install"
                ),
            ), redirect_stdout(console):
                result = session.preflight_login()

        self.assertEqual(result["status"], BLOCKED)
        self.assertEqual(result["error_code"], "browser_launch")
        self.assertIn("[ENV]", console.getvalue())

    def test_upload_worker_runs_preflight_on_browser_worker(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication

        from ui_qt.workers import UploadWorker

        app = QApplication.instance() or QApplication([])

        class FakeSession:
            def __init__(self):
                self.timeout_ms = None

            def preflight_login(self, *, timeout_ms):
                self.timeout_ms = timeout_ms
                return {
                    "status": PASSED,
                    "message": "ready",
                    "url": "https://example.test/login",
                    "browser_channel": "chromium",
                    "reused_browser": False,
                }

            def poll_manual_login(self):
                return {"status": "idle"}

            def poll_prepared_pages(self):
                return {"saved_record_ids": [], "closed_record_ids": [], "open_record_ids": []}

            def close(self):
                return None

        with tempfile.TemporaryDirectory() as temp_dir:
            worker = UploadWorker(Path(temp_dir))
            fake_session = FakeSession()
            worker._ensure_session = lambda: fake_session
            loop = QEventLoop()
            results = []
            worker.preflightChecked.connect(lambda result: (results.append(result), loop.quit()))
            worker.preflight_environment()
            QTimer.singleShot(3000, loop.quit)
            loop.exec()
            worker.close_session()

        self.assertIsNotNone(app)
        self.assertEqual(results[0]["status"], PASSED)
        self.assertEqual(fake_session.timeout_ms, 15000)


if __name__ == "__main__":
    unittest.main()
