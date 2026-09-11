import assert from 'node:assert/strict';
import test from 'node:test';
import { createClient, validatePayload } from './main.js';

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
