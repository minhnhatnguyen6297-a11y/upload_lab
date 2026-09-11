import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('desktopCommand', {
  submit: (command, payload) => ipcRenderer.invoke('desktop-command:submit', command, payload),
  getStatus: (jobId) => ipcRenderer.invoke('desktop-command:get-status', jobId),
});
