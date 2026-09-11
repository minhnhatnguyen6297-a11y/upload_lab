const output = document.querySelector('#status');

async function submit(command) {
  output.textContent = 'Sending command…';
  try {
    const job = await window.desktopCommand.submit(command, {});
    output.textContent = `${job.job_id}: ${job.status}`;
  } catch (error) {
    output.textContent = `Error: ${error.message}`;
  }
}

document.querySelector('#start').addEventListener('click', () => submit('start_upload'));
document.querySelector('#scan').addEventListener('click', () => submit('scan_document'));
