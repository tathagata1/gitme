const { execFile } = require("node:child_process");
const path = require("node:path");
const { performance } = require("node:perf_hooks");

class RepositoryError extends Error {}

function runGit(args, cwd, timeout = 30000) {
  return new Promise((resolve) => {
    const startedAt = new Date();
    const start = performance.now();
    execFile(
      "git",
      args,
      {
        cwd,
        encoding: "utf8",
        windowsHide: true,
        timeout,
        maxBuffer: 10 * 1024 * 1024,
        shell: false,
      },
      (error, stdout = "", stderr = "") => {
        const exitCode = error ? (Number.isInteger(error.code) ? error.code : 1) : 0;
        resolve({
          args: [...args],
          exitCode,
          stdout,
          stderr,
          success: !error,
          startedAt: startedAt.toISOString(),
          durationSeconds: (performance.now() - start) / 1000,
        });
      },
    );
  });
}

function assertStringArray(args) {
  if (!Array.isArray(args) || args.length === 0 || args.some((item) => typeof item !== "string" || item.includes("\0"))) {
    throw new TypeError("Git arguments must be a non-empty array of valid strings.");
  }
}

async function findRoot(selectedPath) {
  if (typeof selectedPath !== "string" || !selectedPath.trim()) {
    throw new RepositoryError("Choose a folder first.");
  }
  const result = await runGit(["rev-parse", "--show-toplevel"], selectedPath);
  if (!result.success || !result.stdout.trim()) {
    const detail = result.stderr.trim() || result.stdout.trim();
    throw new RepositoryError(`“${selectedPath}” is not inside a Git working tree.${detail ? `\n\n${detail}` : ""}`);
  }
  return path.resolve(result.stdout.trim());
}

function parseStatus(output) {
  let currentBranch = "HEAD";
  let detachedHead = false;
  const files = [];
  const records = output.split("\0");

  for (let index = 0; index < records.length; index += 1) {
    const record = records[index];
    if (!record) continue;
    if (record.startsWith("# branch.head ")) {
      const head = record.slice(14).trim();
      detachedHead = head === "(detached)";
      currentBranch = detachedHead ? "Detached HEAD" : head;
      continue;
    }
    if (record.startsWith("1 ")) {
      const parts = record.split(" ");
      files.push({ path: parts.slice(8).join(" "), indexStatus: parts[1][0], worktreeStatus: parts[1][1] });
      continue;
    }
    if (record.startsWith("2 ")) {
      const parts = record.split(" ");
      files.push({
        path: parts.slice(9).join(" "),
        originalPath: records[index + 1] || null,
        indexStatus: parts[1][0],
        worktreeStatus: parts[1][1],
      });
      index += 1;
      continue;
    }
    if (record.startsWith("u ")) {
      const parts = record.split(" ");
      files.push({ path: parts.slice(10).join(" "), indexStatus: parts[1][0], worktreeStatus: parts[1][1] });
      continue;
    }
    if (record.startsWith("? ")) {
      files.push({ path: record.slice(2), indexStatus: "?", worktreeStatus: "?" });
    }
  }

  return { currentBranch, detachedHead, files };
}

function parseLog(output) {
  return output
    .split("\x1e")
    .map((record) => record.trim())
    .filter(Boolean)
    .map((record) => {
      const [hash = "", subject = "", decorations = "", relativeDate = "", author = ""] = record.split("\x1f");
      return { hash, subject, decorations, relativeDate, author };
    });
}

async function loadState(repositoryRoot) {
  const root = await findRoot(repositoryRoot);
  const status = await runGit(["status", "--porcelain=v2", "--branch", "-z"], root);
  if (!status.success) throw new RepositoryError(status.stderr.trim() || "Git could not read repository status.");

  const [branchesResult, logResult, remotesResult] = await Promise.all([
    runGit(["for-each-ref", "--format=%(refname:short)", "refs/heads"], root),
    runGit(["log", "-30", "--format=%h%x1f%s%x1f%D%x1f%cr%x1f%an%x1e"], root),
    runGit(["remote"], root),
  ]);
  const parsed = parseStatus(status.stdout);
  const remoteNames = remotesResult.success ? remotesResult.stdout.split(/\r?\n/).map((item) => item.trim()).filter(Boolean) : [];
  const remotes = await Promise.all(remoteNames.map(async (name) => {
    const [fetch, push] = await Promise.all([
      runGit(["remote", "get-url", "--all", name], root),
      runGit(["remote", "get-url", "--push", "--all", name], root),
    ]);
    return {
      name,
      fetchUrls: fetch.success ? fetch.stdout.split(/\r?\n/).filter(Boolean) : [],
      pushUrls: push.success ? push.stdout.split(/\r?\n/).filter(Boolean) : [],
    };
  }));

  const decorateFile = (file) => ({
    ...file,
    staged: ![".", " ", "?"].includes(file.indexStatus),
    changed: file.indexStatus === "?" || ![".", " "].includes(file.worktreeStatus),
  });
  return {
    root,
    ...parsed,
    branches: branchesResult.success ? branchesResult.stdout.split(/\r?\n/).map((item) => item.trim()).filter(Boolean) : [],
    commits: logResult.success ? parseLog(logResult.stdout) : [],
    remotes,
    files: parsed.files.map(decorateFile),
  };
}

async function execute(args, cwd) {
  assertStringArray(args);
  return runGit(args, cwd);
}

module.exports = { RepositoryError, execute, findRoot, loadState, parseLog, parseStatus, runGit };
