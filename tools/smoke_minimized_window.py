import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from playwright_uploader import NamDinhUploaderSession, load_uploader_settings


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context()
        anchor = context.new_page()
        anchor.goto("about:blank")

        session = NamDinhUploaderSession(
            load_uploader_settings(Path.cwd()),
            log_callback=lambda msg: print("[LOG]", msg),
        )
        session.context = context
        session.anchor_page = anchor

        cdp, window_id, state = session._browser_window_state()
        print("initial:", {"window_id": window_id, "state": state})
        assert window_id is not None, "FAIL: no window id"

        # simulate the user minimizing Chromium
        cdp.send("Browser.setWindowBounds", {"windowId": window_id, "bounds": {"windowState": "minimized"}})
        time.sleep(0.6)
        _, _, state = session._browser_window_state()
        print("after manual minimize:", state)
        assert state == "minimized", f"FAIL: could not minimize ({state})"

        # simulate prepare_manifest capturing the minimized state
        cdp2, window_id2, state = session._browser_window_state()
        if state == "minimized":
            session._minimized_cdp = cdp2
            session._minimized_window_id = window_id2

        # simulate _prepare_record: new tab may raise the window
        page = context.new_page()
        session._keep_browser_window_minimized()
        time.sleep(0.8)
        _, _, state = session._browser_window_state()
        print("after new_page:", state)

        page.goto("about:blank")
        session._keep_browser_window_minimized()
        time.sleep(0.5)
        _, _, state = session._browser_window_state()
        print("final:", state)

        browser.close()
        assert state == "minimized", f"FAIL: window ended in state {state}"
        print("PASS: Chromium stayed minimized through new_page + goto")


if __name__ == "__main__":
    main()
