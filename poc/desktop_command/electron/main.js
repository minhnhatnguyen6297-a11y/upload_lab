import { randomBytes } from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SENSITIVE_KEYS = new Set(['credential', 'cookie', 'password', 'access_token']);

export function validatePayload(value) {
  if (Array.isArray(value)) {
    value.forEach(validatePayload);
    return;
  }
  if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) {
      if (SENSITIVE_KEYS.has(key.toLowerCase())) {
        throw new Error('sensitive payload is forbidden');
      }
      validatePayload(item);
    }
  }
}

export function createClient({ baseUrl, token, fetchImpl = fetch }) {
  async function request(path, options = {}, timeoutMs = 5000) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetchImpl(`${baseUrl}${path}`, {
        ...options,
        signal: controller.signal,
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...options.headers },
      });
    } catch (error) {
      if (controller.signal.aborted) throw new Error('DesktopCommand timeout');
      throw error;
    } finally {
      clearTimeout(timeout);
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message || 'DesktopCommand request failed');
    return data;
  }
  return {
    healthz() { return request('/healthz', { method: 'GET', headers: {} }); },
    submit(command, payload = {}) {
      validatePayload(payload);
      const commandId = crypto.randomUUID();
      const body = JSON.stringify({ contract_version: 'v0.experimental', command_id: commandId, command, payload });
      return request('/v0/commands', { method: 'POST', body }).catch((error) => {
        const retryable = error?.name === 'AbortError' || /timeout|network/i.test(String(error?.message));
        if (!retryable) throw error;
        return request('/v0/commands', { method: 'POST', body });
      });
    },
    getStatus(jobId) { return request(`/v0/jobs/${encodeURIComponent(jobId)}`); },
  };
}

export async function waitForSidecar(client, { timeoutMs = 5000, intervalMs = 100 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const health = await client.healthz();
      if (health.status === 'ok') return health;
      lastError = new Error('DesktopCommand sidecar is unhealthy');
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw lastError || new Error('DesktopCommand sidecar did not become ready');
}

export function startSidecar({
  python = 'python',
  port,
  cwd = fileURLToPath(new URL('../../../', import.meta.url)),
  spawnImpl = spawn,
}) {
  const token = randomBytes(32).toString('base64url');
  const args = ['-m', 'poc.desktop_command.server', '--port', String(port)];
  if (process.env.DESKTOP_COMMAND_POC_FAKE_WORKER === '1') args.push('--fake-worker');
  const child = spawnImpl(python, args, {
    cwd,
    env: { ...process.env, DESKTOP_COMMAND_TOKEN: token },
    stdio: 'ignore',
    windowsHide: true,
  });
  return { child, client: createClient({ baseUrl: `http://127.0.0.1:${port}`, token }) };
}

async function startElectron() {
  const { app, BrowserWindow, ipcMain } = await import('electron');
  const port = Number(process.env.DESKTOP_COMMAND_PORT || 8765);
  const { child, client } = startSidecar({ port });
  app.on('before-quit', () => child.kill());
  try {
    await waitForSidecar(client);
  } catch (error) {
    child.kill();
    throw error;
  }
  ipcMain.handle('desktop-command:submit', (_event, command, payload) => client.submit(command, payload));
  ipcMain.handle('desktop-command:get-status', (_event, jobId) => client.getStatus(jobId));
  await app.whenReady();
  const window = new BrowserWindow({
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: fileURLToPath(new URL('./preload.js', import.meta.url)),
    },
  });
  await window.loadFile(fileURLToPath(new URL('./renderer.html', import.meta.url)));
}

if (process.versions.electron) {
  startElectron().catch((error) => {
    console.error(`DesktopCommand POC startup failed: ${error?.stack || error}`);
    process.exitCode = 1;
  });
}
