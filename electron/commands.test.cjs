const test = require("node:test");
const assert = require("node:assert/strict");
const { RISK, make, paths, raw, tokenize } = require("./renderer/commands.js");

test("structured commands preserve arguments with spaces", () => {
  const command = make("changes.commit", { message: "ship the desktop UI" });
  assert.deepEqual(command.args, ["commit", "-m", "ship the desktop UI"]);
  assert.equal(command.display, 'git commit -m "ship the desktop UI"');
});

test("file commands use the option separator", () => {
  assert.deepEqual(paths("changes.stage", ["docs/my file.md"]).args, ["add", "--", "docs/my file.md"]);
  assert.deepEqual(paths("changes.unstage", ["-danger.txt"], false).args, ["rm", "--cached", "--", "-danger.txt"]);
});

test("raw commands tokenize quotes without invoking a shell", () => {
  assert.deepEqual(tokenize('git commit -m "hello world"'), ["git", "commit", "-m", "hello world"]);
  assert.equal(raw("git status --short").risk, RISK.READ_ONLY);
  assert.equal(raw("git reset --hard HEAD~1").risk, RISK.DESTRUCTIVE);
  assert.throws(() => raw("echo nope"), /begin/);
});
