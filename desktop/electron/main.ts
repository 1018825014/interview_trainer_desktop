import electron from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { app, BrowserWindow, ipcMain } = electron;
const moduleDir = path.dirname(fileURLToPath(import.meta.url));

const isDev = !app.isPackaged;

function createMainWindow() {
  const win = new BrowserWindow({
    width: 1420,
    height: 920,
    minWidth: 1100,
    minHeight: 760,
    backgroundColor: "#121313",
    title: "面试训练助手",
    autoHideMenuBar: true,
    alwaysOnTop: true,
    webPreferences: {
      preload: path.join(moduleDir, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    win.loadURL("http://127.0.0.1:5173");
  } else {
    win.loadFile(path.join(app.getAppPath(), "dist", "index.html"));
  }

  ipcMain.handle("window:set-always-on-top", (_event, value: boolean) => {
    win.setAlwaysOnTop(value);
    return win.isAlwaysOnTop();
  });

  return win;
}

app.whenReady().then(() => {
  createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
