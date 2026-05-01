const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('bridge', {
  pickBakFile: () => ipcRenderer.invoke('pick-bak-file')
});
