const test = require("node:test");
const assert = require("node:assert/strict");
const { RISK, make, paths, raw, syncRemote, tokenize } = require("./renderer/commands.js");

test("structured commands preserve arguments with spaces", () => {
  const command = make("changes.commit", { message: "ship the desktop UI" });
  assert.deepEqual(command.args, ["commit", "-m", "ship the desktop UI"]);
  assert.equal(command.display, 'git commit -m "ship the desktop UI"');
});

test("file commands use the option separator", () => {
  assert.deepEqual(paths("changes.stage", ["docs/my file.md"]).args, ["add", "--", "docs/my file.md"]);
  assert.deepEqual(paths("changes.unstage", ["-danger.txt"], false).args, ["rm", "--cached", "--", "-danger.txt"]);
});

test("custom commands tokenize quotes without invoking a shell", () => {
  assert.deepEqual(tokenize('git commit -m "hello world"'), ["git", "commit", "-m", "hello world"]);
  assert.equal(raw("git status --short").risk, RISK.READ_ONLY);
  assert.equal(raw("git reset --hard HEAD~1").risk, RISK.DESTRUCTIVE);
  assert.throws(() => raw("echo nope"), /begin/);
});

test("remote management commands keep names and URLs as separate arguments", () => {
  assert.deepEqual(make("remote.add", { remote: "upstream", url: "https://example.com/team/repo.git" }).args, [
    "remote", "add", "upstream", "https://example.com/team/repo.git",
  ]);
  assert.deepEqual(make("remote.remove", { remote: "upstream" }).args, ["remote", "remove", "upstream"]);
});

test("sync publishes new branches and sequences existing remote branches", () => {
  const publish = syncRemote({ remote: "origin", branch: "feature/new", remoteBranchExists: false });
  assert.deepEqual(publish.args, ["push", "-u", "origin", "feature/new"]);
  assert.equal(publish.steps, undefined);

  const sync = syncRemote({ remote: "origin", branch: "main", remoteBranchExists: true });
  assert.deepEqual(sync.steps.map((step) => step.args), [
    ["fetch", "--prune", "origin"],
    ["pull", "--rebase", "origin", "main"],
    ["push", "-u", "origin", "main"],
  ]);
  assert.equal(sync.risk, RISK.CAUTION);
});
