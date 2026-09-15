import assert from 'node:assert/strict';
import test from 'node:test';
import { formatJob, isTerminal } from './renderer_logic.js';

test('terminal statuses stop upload polling', () => {
  assert.equal(isTerminal('waiting_user'), false);
  assert.equal(isTerminal('running'), false);
  assert.equal(isTerminal('canceled'), true);
  assert.equal(isTerminal('failed'), true);
});

test('job formatting exposes status but not an absent error', () => {
  assert.equal(formatJob({ job_id: 'job-1', status: 'waiting_user' }), 'job-1: waiting_user');
  assert.equal(
    formatJob({ job_id: 'job-2', status: 'failed', error: { message: 'browser unavailable' } }),
    'job-2: failed — browser unavailable',
  );
});
