const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");

const port = 8002;

async function waitForServer(server) {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (server.exitCode !== null) {
      throw new Error(`E2E server exited with code ${server.exitCode}`);
    }
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`);
      if (response.ok) return;
    } catch (_error) {
      // The server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("Timed out waiting for the E2E server");
}

async function stopServer(server) {
  if (server.exitCode !== null) return;
  server.kill();
  await Promise.race([
    new Promise((resolve) => server.once("exit", resolve)),
    new Promise((resolve) => setTimeout(resolve, 3_000)),
  ]);
  if (server.exitCode === null) {
    server.kill("SIGKILL");
    await Promise.race([
      new Promise((resolve) => server.once("exit", resolve)),
      new Promise((resolve) => setTimeout(resolve, 3_000)),
    ]);
  }
}

async function removeDatabaseFiles(database) {
  const expectedPrefix = path.join(os.tmpdir(), "python-trainer-e2e-");
  if (!database.startsWith(expectedPrefix) || !database.endsWith(".db")) {
    throw new Error(`Refusing to remove unexpected E2E database path: ${database}`);
  }
  await Promise.all(
    [database, `${database}-wal`, `${database}-shm`].map((file) => fs.rm(file, { force: true })),
  );
}

module.exports = async () => {
  const database = path.join(os.tmpdir(), `python-trainer-e2e-${process.pid}.db`);
  const server = spawn(
    "python",
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
    {
      cwd: process.cwd(),
      env: { ...process.env, DB_PATH: database },
      stdio: "inherit",
    },
  );

  try {
    await waitForServer(server);
  } catch (error) {
    await stopServer(server);
    await removeDatabaseFiles(database);
    throw error;
  }

  return async () => {
    try {
      await stopServer(server);
    } finally {
      await removeDatabaseFiles(database);
    }
  };
};
