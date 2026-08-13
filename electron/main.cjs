const path = require("node:path");
const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const { execute, findRoot, loadState, RepositoryError } = require("./git-service.cjs");

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1040,
    minHeight: 700,
    backgroundColor: "#08111f",
    title: "GitGod",
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) shell.openExternal(url);
    return { action: "deny" };
  });
}

function errorPayload(error) {
  return { ok: false, error: error instanceof Error ? error.message : String(error) };
}

ipcMain.handle("repository:choose", async (_event, currentPath) => {
  const selection = await dialog.showOpenDialog(mainWindow, {
    title: "Select a folder containing a Git repository",
    buttonLabel: "Select folder",
    defaultPath: typeof currentPath === "string" && currentPath ? currentPath : app.getPath("documents"),
    properties: ["openDirectory", "createDirectory"],
  });
  if (selection.canceled || selection.filePaths.length === 0) return { ok: false, canceled: true };
  try {
    const root = await findRoot(selection.filePaths[0]);
    return { ok: true, root, selectedPath: selection.filePaths[0] };
  } catch (error) {
    return errorPayload(error);
  }
});

ipcMain.handle("repository:choose-init", async () => {
  const selection = await dialog.showOpenDialog(mainWindow, {
    title: "Choose a folder to initialize",
    buttonLabel: "Use this folder",
    properties: ["openDirectory", "createDirectory", "promptToCreate"],
  });
  return selection.canceled || selection.filePaths.length === 0
    ? { ok: false, canceled: true }
    : { ok: true, path: selection.filePaths[0] };
});

ipcMain.handle("repository:open-path", async (_event, selectedPath) => {
  try {
    return { ok: true, root: await findRoot(selectedPath) };
  } catch (error) {
    return errorPayload(error);
  }
});

ipcMain.handle("repository:load", async (_event, repositoryRoot) => {
  try {
    return { ok: true, state: await loadState(repositoryRoot) };
  } catch (error) {
    return errorPayload(error);
  }
});

ipcMain.handle("git:execute", async (_event, args, cwd) => {
  try {
    return { ok: true, result: await execute(args, cwd) };
  } catch (error) {
    return errorPayload(error);
  }
});

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

process.on("uncaughtException", (error) => {
  if (!(error instanceof RepositoryError)) console.error(error);
});
