const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let apiProcess;

function startApiServer() {
  const pyExe = process.platform === 'win32' ? 'pythonw' : 'python3';
  apiProcess = spawn(pyExe, ['-m', 'uvicorn', 'api_server:app', '--host', '127.0.0.1', '--port', '8765'], {
    cwd: path.resolve(__dirname, '../../Codigo_Fuente'),
    windowsHide: true,
    stdio: 'ignore'
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: '#111827',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  win.removeMenu();
  win.loadFile(path.resolve(__dirname, '../ui/index.html'));
}

ipcMain.handle('pick-bak-file', async () => {
  const result = await dialog.showOpenDialog({ properties: ['openFile'], filters: [{name:'Backup', extensions:['bak']}] });
  return result.canceled ? null : result.filePaths[0];
});

app.whenReady().then(() => { startApiServer(); createWindow(); });
app.on('window-all-closed', () => { if (apiProcess) apiProcess.kill(); if (process.platform !== 'darwin') app.quit(); });
