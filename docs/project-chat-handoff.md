# Project Chat Handoff

Date: 2026-06-13

## Current Request Context

The user wants to redesign the app UI and workflow. The current repository is a desktop automation/upload tool that needs direct local folder access, so the preferred direction is still a desktop app rather than a browser-based web UI.

## Key Findings From Repo Inspection

- Current UI code is Python desktop UI under `ui/`.
- The active UI observed during discussion is Tkinter/ttk-based:
  - `ui/app.py`
  - `ui/widgets.py`
  - `ui/tabs/web_list_tab.py`
  - `ui/tabs/folder_workflow_tab.py`
- Root launcher is `ui_runner.py`.
- Core automation and processing logic appears to remain outside the UI layer, including:
  - `batch_scan.py`
  - `extract_contract.py`
  - `playwright_uploader.py`
  - service modules under `ui/services/`

## Design Direction Discussed

Figma can be used as a design reference, but it is not a reliable round-trip editor for Python Tkinter desktop code. Exporting Figma back into maintainable Tkinter code is not recommended.

The recommended desktop-friendly path is:

1. Migrate the UI layer to PySide6/Qt.
2. Use Qt Designer `.ui` files for drag/drop layout editing.
3. Keep the existing business logic and services where possible.
4. Redesign the user workflow while migrating, rather than doing a purely mechanical Tkinter-to-Qt port.

## User Preference

The user confirmed:

- They need a desktop app because the tool must work heavily with local folders.
- They want to redesign the usage flow, not only change the UI toolkit.
- They want core questions collected into a spec so the redesign does not drift.
- They agreed to use a visual companion for mockups/flow comparisons when useful.

## Next Step

Continue brainstorming before implementation. Ask one core question at a time and use the answers to build a spec.

First core question already asked:

> Mot phien lam viec chuan cua ban voi app nay bat dau tu dau va ket thuc khi nao?

Suggested follow-up topics for the spec:

- Primary job-to-be-done: what task the app must make fastest and least error-prone.
- Inputs: folders, files, website list, credentials, config, existing contract numbers.
- Outputs: uploaded records, logs, reports, exports, failed-item retry list.
- Main workflow shape: wizard, dashboard with steps, or workspace with left navigation.
- Review/approval points: what the user must inspect before upload.
- Failure recovery: how upload errors, missing files, login expiry, duplicate contracts, and partial success should be shown.
- Background work: which tasks need progress, pause/cancel, retry, and logs.
- Local folder operations: browse, recent folders, drag/drop, validation, file preview.
- Settings: uploader credentials, Playwright/browser status, storage state, advanced options.
- Migration constraints: keep current logic, avoid risky rewrite of upload/extraction behavior unless needed.

## Implementation Has Not Started

No Qt/PySide6 implementation plan has been approved yet. Do not start coding until the workflow spec is reviewed and approved.
