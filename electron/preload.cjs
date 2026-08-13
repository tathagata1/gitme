const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("gitgod", {
  chooseRepository: (currentPath) => ipcRenderer.invoke("repository:choose", currentPath),
  chooseInitFolder: () => ipcRenderer.invoke("repository:choose-init"),
  openPath: (selectedPath) => ipcRenderer.invoke("repository:open-path", selectedPath),
  loadRepository: (root) => ipcRenderer.invoke("repository:load", root),
  execute: (args, cwd) => ipcRenderer.invoke("git:execute", args, cwd),
});
