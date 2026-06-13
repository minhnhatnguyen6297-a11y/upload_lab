from __future__ import annotations

from ui.app import UploadLabApp


def main() -> int:
    app = UploadLabApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
