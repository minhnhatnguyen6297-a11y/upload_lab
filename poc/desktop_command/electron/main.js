import { randomBytes } from 'node:crypto';
import { spawn } from 'node:child_process';

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

export function startSidecar({ python = 'python', port, spawnImpl = spawn }) {
  const token = randomBytes(32).toString('base64url');
  const child = spawnImpl(python, ['-m', 'poc.desktop_command.server', '--port', String(port)], {
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
  ipcMain.handle('desktop-command:submit', (_event, command, payload) => client.submit(command, payload));
  ipcMain.handle('desktop-command:get-status', (_event, jobId) => client.getStatus(jobId));
  await app.whenReady();
  const window = new BrowserWindow({
    webPreferences: { contextIsolation: true, nodeIntegration: false, preload: new URL('./preload.js', import.meta.url).pathname },
  });
  await window.loadFile(new URL('./renderer.html', import.meta.url).pathname);
}

if (process.versions.electron) startElectron();
