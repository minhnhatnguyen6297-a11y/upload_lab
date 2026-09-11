import assert from 'node:assert/strict';
import test from 'node:test';
import { createClient, startSidecar, validatePayload, waitForSidecar } from './main.js';

test('sensitive renderer payload is rejected before main fetch', () => {
  assert.throws(() => validatePayload({ cookie: 'secret' }), /sensitive/i);
});

test('client retry after timeout reuses one command id', async () => {
  const bodies = [];
  let attempts = 0;
  const fetchImpl = async (_url, init) => {
    bodies.push(JSON.parse(init.body));
    attempts += 1;
    if (attempts === 1) throw new Error('timeout');
    return { ok: true, json: async () => ({ job_id: 'job-1', status: 'accepted' }) };
  };

  const result = await createClient({ baseUrl: 'http://127.0.0.1:1', token: 'test', fetchImpl })
    .submit('scan_document', {});

  assert.equal(result.job_id, 'job-1');
  assert.equal(bodies.length, 2);
  assert.equal(bodies[0].command_id, bodies[1].command_id);
});

test('client does not retry an HTTP rejection', async () => {
  let attempts = 0;
  const fetchImpl = async () => {
    attempts += 1;
    return { ok: false, json: async () => ({ detail: { message: 'forbidden' } }) };
  };

  await assert.rejects(
    () => createClient({ baseUrl: 'http://127.0.0.1:1', token: 'test', fetchImpl }).submit('scan_document', {}),
    /forbidden/
  );
  assert.equal(attempts, 1);
});

test('sidecar readiness retries then reports health', async () => {
  let attempts = 0;
  const health = await waitForSidecar({
    healthz: async () => {
      attempts += 1;
      if (attempts < 3) throw new Error('connection refused');
      return { status: 'ok' };
    },
  }, { timeoutMs: 100, intervalMs: 1 });

  assert.equal(health.status, 'ok');
  assert.equal(attempts, 3);
});

test('sidecar starts from the repository root so Python module imports resolve', () => {
  let invocation;
  const child = { kill() {} };
  startSidecar({
    port: 8945,
    spawnImpl: (python, args, options) => {
      invocation = { python, args, options };
      return child;
    },
  });

  assert.match(invocation.options.cwd, /desktop-command-poc[\\/]?$/);
  assert.doesNotMatch(invocation.options.cwd, /poc[\\/]desktop_command[\\/]electron[\\/]?$/);
  assert.deepEqual(invocation.args.slice(0, 3), ['-m', 'poc.desktop_command.server', '--port']);
  assert.match(invocation.options.env.DESKTOP_COMMAND_TOKEN, /.+/);
});
