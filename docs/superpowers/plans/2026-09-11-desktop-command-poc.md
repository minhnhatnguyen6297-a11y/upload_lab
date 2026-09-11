# DesktopCommand POC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify Electron main process can issue authenticated localhost commands
to an isolated Python FastAPI sidecar without changing the PySide6 production UI
or breaking UploadWorker/Playwright thread ownership.

**Architecture:** The POC lives in `poc/desktop_command/`, separately from
`ui_qt/`. FastAPI owns an in-memory command registry and calls a queue-only
bridge around `UploadWorker`; Electron main owns the sidecar token and exposes
narrow context-isolated IPC. Chromium remains headed and Python-owned.

**Tech Stack:** Python 3.10+, FastAPI/uvicorn in POC-only requirements, PySide6,
pytest/httpx, Electron/Node in a POC-only package.

**Spec:** `D:\systemdocs\MIN50_IMPLEMENTATION_SPEC.md` W4 and
`D:\systemdocs\SYSTEM_ARCHITECTURE.md` §6.4.

## Global Constraints

- Bind only `127.0.0.1`; port is explicit/configurable; no CORS middleware.
- Startup token belongs only to Python sidecar and Electron main, never renderer,
  logs, URL/query, storage, request/response, or diagnostic output.
- Do not modify `ui_qt/app.py`, `ui_runner.py`, or production startup.
- HTTP handlers never invoke Playwright or a private worker method. The bridge
  only uses public worker slots and signals.
- Reject credential/cookie/password/access-token payload keys recursively.
- This POC does not embed the provincial website, auto-Save/Finalize, or create
  a production API/contract.

## File structure

| File | Responsibility |
|---|---|
| `requirements-poc-desktop-command.txt` | POC-only FastAPI/uvicorn dependencies |
| `poc/desktop_command/models.py` | Command, job, status and structured error models |
| `poc/desktop_command/registry.py` | Idempotent command/job registry |
| `poc/desktop_command/bridge.py` | Queue-only UploadWorker adapter |
| `poc/desktop_command/server.py` | Authenticated loopback FastAPI sidecar |
| `poc/desktop_command/electron/package.json` | Electron scripts/dependencies |
| `poc/desktop_command/electron/main.js` | Sidecar lifecycle, token holder and IPC |
| `poc/desktop_command/electron/preload.js` | Narrow context-isolated API |
| `poc/desktop_command/electron/renderer.js` | Status-only POC renderer |
| `tests/test_desktop_command_poc.py` | Python API/security/bridge tests |
| `poc/desktop_command/electron/main.test.mjs` | Node main-process boundary tests |

### Task 1: Command models and idempotent registry

**Files:**

- Create: `requirements-poc-desktop-command.txt`
- Create: `poc/desktop_command/__init__.py`
- Create: `poc/desktop_command/models.py`
- Create: `poc/desktop_command/registry.py`
- Test: `tests/test_desktop_command_poc.py`

**Interfaces:** `CommandRegistry.submit(request: CommandRequest) -> Job`; valid
commands are exactly `start_upload`, `cancel_upload`, `scan_document`, and
`get_status`.

- [ ] **Step 1: Write the failing idempotency test**

```python
def test_duplicate_command_returns_same_job_without_second_enqueue():
    enqueue = Mock()
    registry = CommandRegistry(enqueue)
    request = CommandRequest(command_id="c-1", command="scan_document", payload={})
    assert registry.submit(request).job_id == registry.submit(request).job_id
    assert enqueue.call_count == 1
```

- [ ] **Step 2: Run it to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k duplicate -q`

Expected: FAIL with import error for the missing POC registry.

- [ ] **Step 3: Implement models and registry**

Create UUID job IDs and UTC timestamps. Limit status to `accepted`,
`waiting_user`, `running`, `failed`, `completed`, `canceled`. Recursively reject
payload keys `credential`, `cookie`, `password`, `access_token` with
`sensitive_payload_forbidden`; reject unknown commands.

- [ ] **Step 4: Run focused test**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k duplicate -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add requirements-poc-desktop-command.txt poc/desktop_command tests/test_desktop_command_poc.py
git commit -m "test: add desktop command POC registry"
```

### Task 2: Queue-only UploadWorker bridge

**Files:**

- Create: `poc/desktop_command/bridge.py`
- Modify: `tests/test_desktop_command_poc.py`

**Interfaces:** `UploadWorkerBridge.submit(command: str, payload: dict) -> None`;
`UploadWorkerBridge.status(job_id: str) -> JobUpdate | None`.

- [ ] **Step 1: Write failing public-slot tests**

```python
def test_start_upload_uses_public_slot_not_session():
    worker = Mock(spec=["start_login", "request_stop"])
    bridge = UploadWorkerBridge(worker, scan_callback=Mock())
    bridge.submit("start_upload", {})
    worker.start_login.assert_called_once_with()

def test_cancel_uses_existing_safe_stop_method():
    worker = Mock(spec=["start_login", "request_stop"])
    UploadWorkerBridge(worker, scan_callback=Mock()).submit("cancel_upload", {})
    worker.request_stop.assert_called_once_with()
```

- [ ] **Step 2: Run them to verify failure**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k "public_slot or safe_stop" -q`

Expected: FAIL because bridge does not exist.

- [ ] **Step 3: Implement bridge**

The bridge holds no Playwright/session reference. Map `start_upload` only to
`worker.start_login()` and status `waiting_user`; map cancel to
`worker.request_stop()`; use a supplied callback for `scan_document`. Subscribe
to public Qt signals for updates. Do not create automatic save/finalize behavior.

- [ ] **Step 4: Run focused tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k "public_slot or safe_stop" -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add poc/desktop_command/bridge.py tests/test_desktop_command_poc.py
git commit -m "feat: add queue-only UploadWorker POC bridge"
```

### Task 3: Authenticated FastAPI loopback sidecar

**Files:**

- Create: `poc/desktop_command/server.py`
- Modify: `tests/test_desktop_command_poc.py`

**Interfaces:** `create_app(registry: CommandRegistry, token: str) -> FastAPI`;
`POST /v0/commands`, `GET /v0/jobs/{job_id}`, `GET /healthz`.

- [ ] **Step 1: Write failing authentication/security tests**

```python
def test_command_endpoint_requires_bearer_token(client):
    assert client.post("/v0/commands", json=command_payload()).status_code == 401

def test_cookie_payload_is_rejected_when_authenticated(client):
    response = client.post("/v0/commands", headers=auth(),
                           json=command_payload(payload={"cookie": "secret"}))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "sensitive_payload_forbidden"
```

- [ ] **Step 2: Run them to verify failure**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k "bearer or cookie" -q`

Expected: FAIL because server factory does not exist.

- [ ] **Step 3: Implement sidecar**

Use constant-time bearer comparison. CLI defaults host to `127.0.0.1`, rejects
non-loopback host, requires explicit port, and uses a short-lived startup token.
No CORS. Return serialised job/error data only; no traceback. `healthz` contains
version/status only.

- [ ] **Step 4: Run test and CLI smoke**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k "bearer or cookie or healthz" -q`

Expected: PASS.

Run: `venv\Scripts\python.exe -m poc.desktop_command.server --help`

Expected: help output and no browser launch.

- [ ] **Step 5: Commit**

```powershell
git add poc/desktop_command/server.py tests/test_desktop_command_poc.py
git commit -m "feat: add authenticated localhost command POC"
```

### Task 4: Electron main/preload boundary

**Files:**

- Create: `poc/desktop_command/electron/package.json`
- Create: `poc/desktop_command/electron/main.js`
- Create: `poc/desktop_command/electron/preload.js`
- Create: `poc/desktop_command/electron/renderer.js`
- Test: `poc/desktop_command/electron/main.test.mjs`

**Interfaces:** Renderer receives only `window.desktopCommand.submit(command,
payload)` and `window.desktopCommand.getStatus(jobId)` through `contextBridge`.

- [ ] **Step 1: Write failing Node security test**

```javascript
test('sensitive renderer payload is rejected before main fetch', async () => {
  await assert.rejects(() => validatePayload({ cookie: 'secret' }), /sensitive/);
});
```

- [ ] **Step 2: Run it to verify failure**

Run: `npm test --prefix poc/desktop_command/electron`

Expected: FAIL because Electron POC package does not exist.

- [ ] **Step 3: Implement minimal shell**

Use `contextIsolation: true`, `nodeIntegration: false`, and preload-only IPC.
Main starts/stops sidecar on loopback, holds the token, and uses `fetch` with a
bearer header. Renderer cannot choose URL or read token. Do not add `<webview>`,
website embedding, or credential persistence.

- [ ] **Step 4: Run Node test**

Run: `npm test --prefix poc/desktop_command/electron`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add poc/desktop_command/electron
git commit -m "feat: add constrained Electron desktop command POC"
```

### Task 5: Resilience tests and POC report

**Files:**

- Create: `docs/superpowers/specs/2026-09-11-desktop-command-poc.md`
- Modify: `tests/test_desktop_command_poc.py`
- Modify: `poc/desktop_command/electron/main.test.mjs`

**Interfaces:** Report includes baseline commit, software versions, happy path,
duplicate command, server restart, timeout, login pending, cancel, browser error,
secret inspection, CPU/RAM/open-time and adopt/reject/iterate conclusion.

- [ ] **Step 1: Write failing resilience test**

```python
def test_unknown_job_is_404_and_health_never_exposes_token(client):
    assert client.get("/v0/jobs/nope", headers=auth()).status_code == 404
    assert "token" not in client.get("/healthz").text.lower()
```

- [ ] **Step 2: Run it to verify failure**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -k "unknown_job or health" -q`

Expected: FAIL until endpoint behavior exists.

- [ ] **Step 3: Implement result record and missing behavior**

Return structured 404 for unknown jobs. Add the report template. Manual
Electron/Playwright runs require a disposable environment and must not capture
cookies, customer data or screenshots containing them.

- [ ] **Step 4: Run all POC tests**

Run: `venv\Scripts\python.exe -m pytest tests/test_desktop_command_poc.py -q`

Expected: PASS.

Run: `npm test --prefix poc/desktop_command/electron`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add docs/superpowers/specs/2026-09-11-desktop-command-poc.md tests/test_desktop_command_poc.py poc/desktop_command
git commit -m "test: add desktop command POC resilience coverage"
```

## Self-review

- Spec coverage: command/idempotency = Task 1; worker ownership/manual login =
  Task 2; loopback/token boundary = Task 3/4; resilience/measurements = Task 5.
- No placeholders: every task has an exact path, test, verification command, and
  expected result. Production UI and browser automation remain out of scope.
- Interface consistency: registry produces `Job`, bridge emits job updates,
  server serialises jobs, and Electron handles only command/status dictionaries.
