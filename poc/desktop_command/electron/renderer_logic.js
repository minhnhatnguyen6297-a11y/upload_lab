export const TERMINAL_STATUSES = new Set(['failed', 'completed', 'canceled']);

export function isTerminal(status) {
  return TERMINAL_STATUSES.has(status);
}

export function formatJob(job) {
  const suffix = job.error?.message || job.result?.message || '';
  return `${job.job_id}: ${job.status}${suffix ? ` — ${suffix}` : ''}`;
}
