import { app, BrowserWindow, shell } from "electron";
import path from "node:path";
import { spawn, ChildProcess } from "node:child_process";

let mainWindow: BrowserWindow | null = null;
let engineProcess: ChildProcess | null = null;

function startEngine(): void {
  const enginePath = process.env.DOCHECK_ENGINE_BIN ?? "python";
  engineProcess = spawn(enginePath, ["-m", "docheck.main"], {
    env: { ...process.env, DOCHECK_BIND_TCP: "127.0.0.1:8765" },
    stdio: "inherit",
  });
  engineProcess.on("exit", (code) => console.log(`engine exited ${code}`));
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: "#09090B",
    titleBarStyle: "hiddenInset",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL("http://localhost:3000");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../out/index.html"));
  }
}

app.whenReady().then(() => {
  startEngine();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  engineProcess?.kill();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  engineProcess?.kill();
});
