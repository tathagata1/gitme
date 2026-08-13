const test = require("node:test");
const assert = require("node:assert/strict");
const { parseLog, parseStatus } = require("./git-service.cjs");

test("parseStatus reads branches, ordinary files, renames, and untracked paths", () => {
  const input = [
    "# branch.oid abcdef",
    "# branch.head feature/desktop",
    "1 M. N... 100644 100644 100644 aaaaaaa bbbbbbb staged file.txt",
    "1 .M N... 100644 100644 100644 aaaaaaa bbbbbbb working.txt",
    "2 R. N... 100644 100644 100644 aaaaaaa bbbbbbb R100 renamed file.txt",
    "old file.txt",
    "? new file.txt",
    "",
  ].join("\0");
  const state = parseStatus(input);
  assert.equal(state.currentBranch, "feature/desktop");
  assert.equal(state.detachedHead, false);
  assert.deepEqual(state.files, [
    { path: "staged file.txt", indexStatus: "M", worktreeStatus: "." },
    { path: "working.txt", indexStatus: ".", worktreeStatus: "M" },
    { path: "renamed file.txt", originalPath: "old file.txt", indexStatus: "R", worktreeStatus: "." },
    { path: "new file.txt", indexStatus: "?", worktreeStatus: "?" },
  ]);
});

test("parseStatus labels a detached head", () => {
  const state = parseStatus("# branch.head (detached)\0");
  assert.equal(state.detachedHead, true);
  assert.equal(state.currentBranch, "Detached HEAD");
});

test("parseLog reads structured commit records", () => {
  const commits = parseLog("abc123\x1fAdd app\x1fHEAD -> main\x1f2 hours ago\x1fAda\x1e");
  assert.deepEqual(commits, [{ hash: "abc123", subject: "Add app", decorations: "HEAD -> main", relativeDate: "2 hours ago", author: "Ada" }]);
});
