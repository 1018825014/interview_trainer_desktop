import electron from "electron";

const { contextBridge, ipcRenderer } = electron;

contextBridge.exposeInMainWorld("interviewTrainer", {
  backendBaseUrl: "http://127.0.0.1:8000",
  platform: process.platform,
  setAlwaysOnTop: (value: boolean) => ipcRenderer.invoke("window:set-always-on-top", value),
});
