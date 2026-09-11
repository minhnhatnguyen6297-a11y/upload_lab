import { formatJob, isTerminal } from './renderer_logic.js';

const output = document.querySelector('#status');
const startButton = document.querySelector('#start');
const cancelButton = document.querySelector('#cancel');
const scanButton = document.querySelector('#scan');
let activeUploadJobId = null;
let pollTimer = null;

function render(job) {
  output.textContent = formatJob(job);
  const active = activeUploadJobId && !isTerminal(job.status);
  startButton.disabled = Boolean(active);
  cancelButton.disabled = !active;
}

async function pollUpload(jobId) {
  try {
    const job = await window.desktopCommand.getStatus(jobId);
    render(job);
    if (!isTerminal(job.status)) {
      pollTimer = window.setTimeout(() => pollUpload(jobId), 400);
    } else {
      activeUploadJobId = null;
    }
  } catch (error) {
    output.textContent = `Error: ${error.message}`;
    activeUploadJobId = null;
    cancelButton.disabled = true;
  }
}

async function submit(command) {
  output.textContent = 'Sending command...';
  try {
    const job = await window.desktopCommand.submit(command, {});
    if (command === 'start_upload') activeUploadJobId = job.job_id;
    render(job);
    if (command === 'start_upload') pollUpload(job.job_id);
    return job;
  } catch (error) {
    output.textContent = `Error: ${error.message}`;
    return null;
  }
}

startButton.addEventListener('click', () => submit('start_upload'));
cancelButton.addEventListener('click', async () => {
  if (!activeUploadJobId) return;
  if (pollTimer) window.clearTimeout(pollTimer);
  const originalJobId = activeUploadJobId;
  await submit('cancel_upload');
  pollUpload(originalJobId);
});
scanButton.addEventListener('click', () => submit('scan_document'));
