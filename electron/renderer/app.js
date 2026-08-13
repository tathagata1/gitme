const { RISK, make, paths, raw, syncRemote } = window.GitCommands;

const appState = {
  root: null,
  repository: null,
  pending: null,
  pendingCwd: null,
  openAfterExecution: false,
  history: [],
  selectedChanges: new Set(),
  selectedStaged: new Set(),
  busy: false,
  countdownTimer: null,
  countdownDeadline: null,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]);
}

function basename(filePath) {
  return String(filePath).split(/[\\/]/).filter(Boolean).pop() || filePath;
}

function dirname(filePath) {
  const segments = String(filePath).split(/[\\/]/);
  segments.pop();
  return segments.join("/") || "repository root";
}

function toast(title, message = "", type = "success") {
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.innerHTML = `<strong>${escapeHtml(title)}</strong>${message ? `<span>${escapeHtml(message)}</span>` : ""}`;
  $("#toast-stack").append(element);
  setTimeout(() => element.remove(), 4300);
}

let modalResolver = null;
function modal({ title, message, confirmText = "Continue", fieldLabel = "", fieldValue = "", command = "", icon = "⑂", cancelable = true }) {
  $("#modal-title").textContent = title;
  $("#modal-message").textContent = message;
  $("#modal-confirm").textContent = confirmText;
  $("#modal-icon").textContent = icon;
  $("#modal-cancel").classList.toggle("hidden", !cancelable);
  const fieldWrap = $("#modal-field-wrap");
  fieldWrap.classList.toggle("hidden", !fieldLabel);
  $("#modal-field-label").textContent = fieldLabel;
  $("#modal-field").value = fieldValue;
  const commandElement = $("#modal-command");
  commandElement.classList.toggle("hidden", !command);
  commandElement.textContent = command;
  $("#modal-backdrop").classList.add("open");
  setTimeout(() => (fieldLabel ? $("#modal-field") : $("#modal-confirm")).focus(), 50);
  return new Promise((resolve) => { modalResolver = resolve; });
}

function closeModal(confirmed) {
  if (!modalResolver) return;
  const value = $("#modal-field-wrap").classList.contains("hidden") ? confirmed : (confirmed ? $("#modal-field").value : null);
  $("#modal-backdrop").classList.remove("open");
  const resolve = modalResolver;
  modalResolver = null;
  resolve(value);
}

function switchView(name) {
  $$(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `${name}-view`));
  const labels = { workspace: ["REPOSITORY OVERVIEW", "Workspace"], history: ["SESSION LOG", "Command history"], raw: ["ADVANCED MODE", "Raw command"] };
  $("#page-eyebrow").textContent = labels[name][0];
  $("#page-title").textContent = labels[name][1];
}

async function chooseRepository() {
  if (appState.busy) return;
  const response = await window.gitgod.chooseRepository(appState.root);
  if (response.canceled) return;
  if (!response.ok) {
    await modal({ title: "That folder is not a repository", message: response.error, confirmText: "Choose another", icon: "!", cancelable: false });
    return chooseRepository();
  }
  await openRepository(response.root);
}

async function initializeRepository() {
  const response = await window.gitgod.chooseInitFolder();
  if (!response.ok) return;
  setPreview(make("repo.init"), response.path, true);
}

async function openRepository(root, { quiet = false } = {}) {
  setBusy(true);
  const response = await window.gitgod.loadRepository(root);
  setBusy(false);
  if (!response.ok) {
    if (!quiet) await modal({ title: "Could not open repository", message: response.error, confirmText: "Close", icon: "!", cancelable: false });
    return false;
  }
  appState.root = response.state.root;
  appState.repository = response.state;
  appState.selectedChanges.clear();
  appState.selectedStaged.clear();
  localStorage.setItem("gitgod:lastRepository", response.state.root);
  renderRepository();
  switchView("workspace");
  if (!quiet) toast("Repository opened", response.state.root);
  return true;
}

async function refreshRepository({ quiet = false } = {}) {
  if (!appState.root || appState.busy) return;
  setBusy(true);
  const response = await window.gitgod.loadRepository(appState.root);
  setBusy(false);
  if (!response.ok) {
    toast("Refresh failed", response.error, "error");
    return;
  }
  appState.repository = response.state;
  renderRepository();
  if (!quiet) toast("Repository refreshed", response.state.currentBranch);
}

function setBusy(busy) {
  appState.busy = busy;
  $("#refresh").classList.toggle("spinning", busy);
}

function renderRepository() {
  const repository = appState.repository;
  if (!repository) return;
  const changed = repository.files.filter((file) => file.changed);
  const staged = repository.files.filter((file) => file.staged);
  const changedPaths = new Set(changed.map((file) => file.path));
  const stagedPaths = new Set(staged.map((file) => file.path));
  appState.selectedChanges.forEach((filePath) => { if (!changedPaths.has(filePath)) appState.selectedChanges.delete(filePath); });
  appState.selectedStaged.forEach((filePath) => { if (!stagedPaths.has(filePath)) appState.selectedStaged.delete(filePath); });
  const name = basename(repository.root);
  $("#empty-state").classList.add("hidden");
  $("#dashboard").classList.remove("hidden");
  $("#repo-name").textContent = name;
  $("#repo-path").textContent = repository.root;
  $("#branch-chip strong").textContent = repository.currentBranch;
  $("#changes-count").textContent = changed.length;
  $("#staged-count").textContent = staged.length;
  $("#branches-count").textContent = repository.branches.length;
  $("#remotes-count").textContent = repository.remotes.length;
  $("#remote-badge").textContent = repository.remotes.length ? `${repository.remotes.length} remote${repository.remotes.length === 1 ? "" : "s"}` : "Local only";
  renderFiles("changes", changed, appState.selectedChanges);
  renderFiles("staged", staged, appState.selectedStaged);
  renderBranches();
  renderCommits();
  renderRemotes();
  updateSelectionLabels();
}

function renderFiles(kind, files, selected) {
  const container = $(`#${kind}-list`);
  const isStaged = kind === "staged";
  if (!files.length) {
    container.innerHTML = `<div class="list-empty"><div><strong>${isStaged ? "Nothing staged yet" : "Working tree is clean"}</strong>${isStaged ? "Select changed files and stage them." : "You’re completely in sync."}</div></div>`;
    return;
  }
  container.innerHTML = files.map((file) => {
    const status = isStaged ? file.indexStatus : file.worktreeStatus;
    const label = status === "?" ? "NEW" : status === "M" ? "MOD" : status === "D" ? "DEL" : status === "R" ? "REN" : status;
    return `<label class="file-row"><input type="checkbox" data-file-kind="${kind}" data-path="${escapeHtml(file.path)}" ${selected.has(file.path) ? "checked" : ""}/><span class="file-status">${escapeHtml(label)}</span><span class="file-name"><strong>${escapeHtml(basename(file.path))}</strong><small>${escapeHtml(dirname(file.path))}</small></span><span class="file-kind">${isStaged ? "INDEX" : "WORKTREE"}</span></label>`;
  }).join("");
}

function renderBranches() {
  const repository = appState.repository;
  const container = $("#branch-list");
  if (!repository.branches.length) {
    container.innerHTML = '<div class="list-empty"><div><strong>No branches yet</strong>Your first commit will create one.</div></div>';
    return;
  }
  container.innerHTML = repository.branches.map((branch) => {
    const current = branch === repository.currentBranch;
    return `<div class="branch-row ${current ? "current" : ""}" draggable="${!current}" data-branch="${escapeHtml(branch)}"><span class="branch-line"></span><strong>${escapeHtml(branch)}</strong>${current ? '<span class="current-label">CURRENT</span>' : `<span class="branch-menu"><button data-branch-action="switch" data-branch="${escapeHtml(branch)}">Switch</button><button data-branch-action="merge" data-branch="${escapeHtml(branch)}">Merge</button><button data-branch-action="delete" data-branch="${escapeHtml(branch)}">Delete</button></span>`}</div>`;
  }).join("");
}

function renderCommits() {
  const commits = appState.repository.commits;
  const container = $("#commit-list");
  if (!commits.length) {
    container.innerHTML = '<div class="list-empty"><div><strong>No commits yet</strong>Stage files and create the first commit.</div></div>';
    return;
  }
  container.innerHTML = commits.map((commit) => `<div class="commit-row"><span class="commit-node"></span><span class="commit-copy"><strong>${escapeHtml(commit.subject)}</strong><small>${escapeHtml(commit.author)} · ${escapeHtml(commit.relativeDate)}${commit.decorations ? ` · ${escapeHtml(commit.decorations)}` : ""}</small></span><code class="commit-hash">${escapeHtml(commit.hash)}</code></div>`).join("");
}

function renderRemotes() {
  const repository = appState.repository;
  const container = $("#remote-list");
  if (!repository.remotes.length) {
    container.innerHTML = '<div class="list-empty"><div><strong>No remotes configured</strong>Add a hosted repository URL to publish or sync this branch.</div></div>';
    return;
  }
  container.innerHTML = repository.remotes.map((remote) => {
    const tracksCurrentBranch = repository.upstream === `${remote.name}/${repository.currentBranch}`;
    const relation = tracksCurrentBranch
      ? `${repository.upstream} · ↑ ${repository.ahead} ahead · ↓ ${repository.behind} behind`
      : `${remote.branches.length} remote branch${remote.branches.length === 1 ? "" : "es"}`;
    const fetchUrl = remote.fetchUrls[0] || "No fetch URL";
    const pushUrl = remote.pushUrls[0] || fetchUrl;
    return `<div class="remote-row">
      <div class="remote-identity"><strong>${escapeHtml(remote.name)}</strong><span class="remote-tracking">${escapeHtml(relation)}</span></div>
      <div class="remote-url"><strong title="${escapeHtml(fetchUrl)}">${escapeHtml(fetchUrl)}</strong><small>${pushUrl === fetchUrl ? "Fetch and push URL" : `Push: ${escapeHtml(pushUrl)}`}</small></div>
      <div class="remote-actions">
        <button data-remote-action="fetch" data-remote="${escapeHtml(remote.name)}">Fetch</button>
        <button class="sync-button" data-remote-action="sync" data-remote="${escapeHtml(remote.name)}">Sync</button>
        <button class="remove-button" data-remote-action="remove" data-remote="${escapeHtml(remote.name)}">Remove</button>
      </div>
    </div>`;
  }).join("");
}

function updateSelectionLabels() {
  $("#changes-selected").textContent = `${appState.selectedChanges.size} selected`;
}

async function prepareAction(operation, parameters = {}) {
  if (!appState.repository && operation !== "repo.init") {
    toast("Choose a repository first", "Open any folder inside a Git worktree.", "error");
    return;
  }
  try {
    let command;
    if (operation === "changes.stage") command = paths(operation, [...appState.selectedChanges]);
    else if (operation === "changes.unstage") command = paths(operation, [...appState.selectedStaged], appState.repository.commits.length > 0);
    else if (operation === "changes.commit") {
      const message = await modal({ title: "Commit staged changes", message: "Write a concise message describing this snapshot.", fieldLabel: "Commit message", confirmText: "Create preview", icon: "✓" });
      if (message === null) return;
      command = make(operation, { message });
    } else if (operation === "branch.create") {
      const branch = await modal({ title: "Create a new branch", message: `The new branch starts from ${appState.repository.currentBranch}.`, fieldLabel: "Branch name", confirmText: "Create preview", icon: "⑂" });
      if (branch === null) return;
      command = make(operation, { branch });
    } else command = make(operation, parameters);
    setPreview(command);
  } catch (error) {
    toast("Cannot create command", error.message, "error");
  }
}

async function prepareRemoteAction(action, remoteName) {
  const remote = appState.repository?.remotes.find((item) => item.name === remoteName);
  if (!remote) {
    toast("Remote not found", "Refresh the repository and try again.", "error");
    return;
  }
  try {
    if (action === "fetch") {
      setPreview(make("remote.fetch-one", { remote: remote.name }));
      return;
    }
    if (action === "sync") {
      const remoteBranchExists = remote.branches.includes(`${remote.name}/${appState.repository.currentBranch}`);
      setPreview(syncRemote({ remote: remote.name, branch: appState.repository.currentBranch, remoteBranchExists }));
      return;
    }
    if (action === "remove") {
      const confirmed = await modal({
        title: `Remove remote ${remote.name}?`,
        message: "This removes the local remote configuration and its tracking references. It does not delete the hosted repository.",
        confirmText: "Create preview",
        icon: "−",
      });
      if (!confirmed) return;
      setPreview(make("remote.remove", { remote: remote.name }));
    }
  } catch (error) {
    toast("Cannot create command", error.message, "error");
  }
}

function setPreview(command, cwd = appState.root, openAfterExecution = false) {
  stopExecutionCountdown();
  appState.pending = command;
  appState.pendingCwd = cwd;
  appState.openAfterExecution = openAfterExecution;
  const riskNames = ["READ ONLY", "NORMAL", "CAUTION", "DESTRUCTIVE"];
  const badge = $("#risk-badge");
  badge.textContent = riskNames[command.risk];
  badge.className = `risk-badge ${command.risk === RISK.CAUTION ? "caution" : command.risk === RISK.DESTRUCTIVE ? "destructive" : command.risk === RISK.READ_ONLY ? "read-only" : ""}`;
  $("#preview-summary").textContent = command.summary;
  $("#preview-command").textContent = command.display;
  $("#preview-explanation").textContent = command.explanation;
  $("#command-dock").classList.add("open");
  startExecutionCountdown();
}

function stopExecutionCountdown() {
  if (appState.countdownTimer !== null) clearInterval(appState.countdownTimer);
  appState.countdownTimer = null;
  appState.countdownDeadline = null;
}

function startExecutionCountdown() {
  const duration = 5000;
  appState.countdownDeadline = Date.now() + duration;
  const updateCountdown = () => {
    if (!appState.pending || appState.countdownDeadline === null) return;
    const remaining = Math.max(0, appState.countdownDeadline - Date.now());
    const seconds = Math.max(1, Math.ceil(remaining / 1000));
    $("#countdown-seconds").textContent = seconds;
    $("#countdown-unit").textContent = seconds === 1 ? "second" : "seconds";
    if (remaining === 0 && !appState.busy) executePending();
  };
  updateCountdown();
  appState.countdownTimer = setInterval(updateCountdown, 100);
}

function clearPreview() {
  stopExecutionCountdown();
  appState.pending = null;
  appState.pendingCwd = null;
  appState.openAfterExecution = false;
  $("#command-dock").classList.remove("open");
}

async function executePending() {
  const command = appState.pending;
  if (!command || appState.busy) return;
  stopExecutionCountdown();
  $("#command-dock").classList.remove("open");
  const cwd = appState.pendingCwd;
  const shouldOpen = appState.openAfterExecution;
  setBusy(true);
  const steps = command.steps || [{ args: command.args, display: command.display }];
  const results = [];
  let startError = null;
  for (const step of steps) {
    const response = await window.gitgod.execute(step.args, cwd);
    if (!response.ok) {
      startError = response.error;
      break;
    }
    results.push({ ...response.result, step });
    if (!response.result.success) break;
  }
  setBusy(false);
  if (startError) {
    if (appState.pending === command) clearPreview();
    toast("Could not start Git", startError, "error");
    return;
  }
  const lastResult = results[results.length - 1];
  const multiStep = steps.length > 1;
  const outputFor = (result, stream) => {
    const output = result[stream].trim();
    if (!multiStep || !output) return output;
    return `== ${result.step.display} ==\n${output}`;
  };
  const result = {
    args: command.args,
    exitCode: lastResult.exitCode,
    stdout: results.map((item) => outputFor(item, "stdout")).filter(Boolean).join("\n\n"),
    stderr: results.map((item) => outputFor(item, "stderr")).filter(Boolean).join("\n\n"),
    success: results.length === steps.length && results.every((item) => item.success),
    startedAt: results[0].startedAt,
    durationSeconds: results.reduce((total, item) => total + item.durationSeconds, 0),
    command,
    cwd,
  };
  appState.history.unshift(result);
  renderHistory();
  if (appState.pending === command) clearPreview();
  if (result.success) {
    toast("Command completed", command.display);
    if (shouldOpen) {
      const opened = await window.gitgod.openPath(cwd);
      if (opened.ok) await openRepository(opened.root);
    } else await refreshRepository({ quiet: true });
  } else toast(`Git exited with code ${result.exitCode}`, result.stderr.trim() || "Open Command history for the full output.", "error");
  await showResult(result);
}

async function showResult(result) {
  const output = [result.stdout.trim(), result.stderr.trim()].filter(Boolean).join("\n\n") || "(No output)";
  await modal({
    title: result.success ? "Command completed" : `Git exited with code ${result.exitCode}`,
    message: `${result.command.display}\n\n${output.slice(0, 1400)}${output.length > 1400 ? "\n\n…Full output is available in Command history." : ""}`,
    confirmText: "Done",
    icon: result.success ? "✓" : "!",
    cancelable: false,
  });
}

function renderHistory() {
  $("#history-count").textContent = appState.history.length;
  const list = $("#history-list");
  if (!appState.history.length) {
    list.innerHTML = '<div class="blank-slate">Commands you execute will appear here.</div>';
    return;
  }
  list.innerHTML = appState.history.map((result, index) => `<button class="history-item" data-history-index="${index}"><strong><span class="${result.success ? "success" : "failure"}">${result.success ? "✓" : "×"}</span> ${escapeHtml(result.command.display)}</strong><small>${escapeHtml(new Date(result.startedAt).toLocaleTimeString())} · ${result.durationSeconds.toFixed(2)}s · exit ${result.exitCode}</small></button>`).join("");
}

function showHistoryItem(index) {
  const result = appState.history[index];
  if (!result) return;
  $$(".history-item").forEach((item) => item.classList.toggle("active", Number(item.dataset.historyIndex) === index));
  $("#history-detail").innerHTML = `<h3 class="${result.success ? "success" : "failure"}">${result.success ? "Command succeeded" : "Command failed"}</h3><p>${escapeHtml(result.command.explanation)}</p><pre>${escapeHtml(result.command.display)}</pre><p class="eyebrow">OUTPUT</p><pre class="output-block">${escapeHtml([result.stdout, result.stderr].filter(Boolean).join("\n") || "(No output)")}</pre><p>Exit code ${result.exitCode} · ${result.durationSeconds.toFixed(2)} seconds · ${escapeHtml(result.cwd)}</p>`;
}

function handleCheckbox(event) {
  const input = event.target.closest("input[data-file-kind]");
  if (!input) return;
  const selected = input.dataset.fileKind === "changes" ? appState.selectedChanges : appState.selectedStaged;
  if (input.checked) selected.add(input.dataset.path);
  else selected.delete(input.dataset.path);
  updateSelectionLabels();
}

function selectAll(kind) {
  const collection = kind === "changes" ? appState.selectedChanges : appState.selectedStaged;
  const files = appState.repository.files.filter((file) => kind === "changes" ? file.changed : file.staged);
  const shouldSelect = collection.size !== files.length;
  collection.clear();
  if (shouldSelect) files.forEach((file) => collection.add(file.path));
  renderFiles(kind, files, collection);
  updateSelectionLabels();
}

document.addEventListener("click", async (event) => {
  const viewButton = event.target.closest("[data-view]");
  if (viewButton) switchView(viewButton.dataset.view);
  const actionButton = event.target.closest("[data-action]");
  if (actionButton) await prepareAction(actionButton.dataset.action);
  const branchButton = event.target.closest("[data-branch-action]");
  if (branchButton) {
    const operation = `branch.${branchButton.dataset.branchAction}`;
    await prepareAction(operation, { branch: branchButton.dataset.branch });
  }
  const remoteButton = event.target.closest("[data-remote-action]");
  if (remoteButton) await prepareRemoteAction(remoteButton.dataset.remoteAction, remoteButton.dataset.remote);
  const historyButton = event.target.closest("[data-history-index]");
  if (historyButton) showHistoryItem(Number(historyButton.dataset.historyIndex));
});

document.addEventListener("change", handleCheckbox);
document.addEventListener("dragstart", (event) => {
  const branch = event.target.closest(".branch-row:not(.current)");
  if (branch) event.dataTransfer.setData("text/x-gitgod-branch", branch.dataset.branch);
});
document.addEventListener("dragover", (event) => {
  if (event.target.closest(".branch-row.current")) event.preventDefault();
});
document.addEventListener("drop", (event) => {
  if (!event.target.closest(".branch-row.current")) return;
  event.preventDefault();
  const branch = event.dataTransfer.getData("text/x-gitgod-branch");
  if (branch) prepareAction("branch.merge", { branch });
});
$("#choose-repository").addEventListener("click", chooseRepository);
$("#sidebar-select-folder").addEventListener("click", chooseRepository);
$("#empty-open").addEventListener("click", chooseRepository);
$("#initialize-repository").addEventListener("click", initializeRepository);
$("#refresh").addEventListener("click", () => refreshRepository());
$("#select-all-changes").addEventListener("click", () => selectAll("changes"));
$("#select-all-staged").addEventListener("click", () => selectAll("staged"));
$("#show-add-remote").addEventListener("click", () => {
  if (!appState.repository) {
    toast("Choose a repository first", "Open a repository before adding a remote.", "error");
    return;
  }
  $("#remote-add-form").classList.remove("hidden");
  $("#remote-name").focus();
});
$("#cancel-add-remote").addEventListener("click", () => $("#remote-add-form").classList.add("hidden"));
$("#remote-add-form").addEventListener("submit", (event) => {
  event.preventDefault();
  try {
    const command = make("remote.add", { remote: $("#remote-name").value, url: $("#remote-url").value });
    $("#remote-add-form").reset();
    $("#remote-add-form").classList.add("hidden");
    setPreview(command);
  } catch (error) {
    toast("Cannot add remote", error.message, "error");
  }
});
$("#clear-preview").addEventListener("click", clearPreview);
$("#cancel-command").addEventListener("click", clearPreview);
$("#copy-command").addEventListener("click", async () => {
  if (!appState.pending) return;
  await navigator.clipboard.writeText(appState.pending.display);
  toast("Command copied");
});
$("#preview-raw").addEventListener("click", () => {
  try { setPreview(raw($("#raw-input").value)); }
  catch (error) { toast("Invalid raw command", error.message, "error"); }
});
$("#raw-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") $("#preview-raw").click();
});
$("#modal-confirm").addEventListener("click", () => closeModal(true));
$("#modal-cancel").addEventListener("click", () => closeModal(false));
$("#modal-field").addEventListener("keydown", (event) => { if (event.key === "Enter") closeModal(true); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if ($("#modal-backdrop").classList.contains("open") && !$("#modal-cancel").classList.contains("hidden")) closeModal(false);
    else clearPreview();
  }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "o") { event.preventDefault(); chooseRepository(); }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "r") { event.preventDefault(); refreshRepository(); }
});

renderHistory();
const lastRepository = localStorage.getItem("gitgod:lastRepository");
if (lastRepository) openRepository(lastRepository, { quiet: true });
