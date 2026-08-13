(function exposeCommands(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.GitCommands = api;
})(typeof globalThis !== "undefined" ? globalThis : window, () => {
  const RISK = Object.freeze({ READ_ONLY: 0, NORMAL: 1, CAUTION: 2, DESTRUCTIVE: 3 });

  const definitions = {
    "repo.init": ["Initialize repository", ["init"], RISK.NORMAL, "Creates Git metadata in the selected folder."],
    "changes.commit": ["Commit staged changes", ["commit", "-m", "{message}"], RISK.NORMAL, "Creates a commit from the staged snapshot."],
    "branch.create": ["Create branch", ["switch", "-c", "{branch}"], RISK.NORMAL, "Creates a new branch and immediately switches to it."],
    "branch.switch": ["Switch branch", ["switch", "{branch}"], RISK.NORMAL, "Checks out the selected local branch."],
    "branch.delete": ["Delete branch", ["branch", "-d", "{branch}"], RISK.CAUTION, "Safely deletes the branch only if Git considers it merged."],
    "branch.merge": ["Merge branch", ["merge", "{branch}"], RISK.CAUTION, "Merges the selected branch into the current branch."],
    "remote.fetch": ["Fetch remote", ["fetch"], RISK.NORMAL, "Downloads remote objects and references without merging."],
    "remote.fetch-one": ["Fetch remote", ["fetch", "--prune", "{remote}"], RISK.NORMAL, "Downloads the selected remote's objects and refreshes its tracking references."],
    "remote.pull": ["Pull changes", ["pull"], RISK.CAUTION, "Fetches and integrates the configured upstream branch."],
    "remote.push": ["Push commits", ["push"], RISK.NORMAL, "Uploads commits using the branch’s configured upstream."],
    "remote.add": ["Add remote", ["remote", "add", "{remote}", "{url}"], RISK.NORMAL, "Adds a named remote URL to this repository."],
    "remote.remove": ["Remove remote", ["remote", "remove", "{remote}"], RISK.CAUTION, "Removes the selected remote and its local remote-tracking references. The hosted repository is not deleted."],
  };

  function quote(argument) {
    return /^[A-Za-z0-9_./:@%+=,-]+$/.test(argument) && argument ? argument : `"${argument.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
  }

  function make(operation, parameters = {}) {
    const definition = definitions[operation];
    if (!definition) throw new Error(`Unknown Git operation: ${operation}`);
    const [summary, template, risk, explanation] = definition;
    const args = template.map((part) => part.replace(/\{(\w+)\}/g, (_match, name) => {
      const value = String(parameters[name] || "").trim();
      if (!value) throw new Error(`${name.replace("_", " ")} is required.`);
      if (/[\0\r\n]/.test(value)) throw new Error(`${name.replace("_", " ")} contains an invalid character.`);
      return value;
    }));
    return command(operation, args, summary, explanation, risk);
  }

  function command(operation, args, summary, explanation, risk = RISK.NORMAL) {
    return { operation, args, summary, explanation, risk, display: ["git", ...args].map(quote).join(" ") };
  }

  function sequence(operation, steps, summary, explanation, risk = RISK.NORMAL) {
    const commands = steps.map((args) => command(operation, args, summary, explanation, risk));
    return {
      operation,
      args: commands[0].args,
      steps: commands.map(({ args, display }) => ({ args, display })),
      summary,
      explanation,
      risk,
      display: commands.map(({ display }, index) => `${index + 1}. ${display}`).join("\n"),
    };
  }

  function syncRemote({ remote, branch, remoteBranchExists = false }) {
    const values = { remote: String(remote || "").trim(), branch: String(branch || "").trim() };
    if (!values.remote) throw new Error("remote is required.");
    if (!values.branch || values.branch === "Detached HEAD") throw new Error("Switch to a local branch before syncing.");
    if ([values.remote, values.branch].some((value) => /[\0\r\n]/.test(value))) throw new Error("Remote and branch names must be on one line.");
    const push = ["push", "-u", values.remote, values.branch];
    if (!remoteBranchExists) {
      return command("remote.sync", push, "Publish branch to remote", `Pushes ${values.branch} to ${values.remote} and configures it as the upstream branch.`);
    }
    return sequence(
      "remote.sync",
      [["fetch", "--prune", values.remote], ["pull", "--rebase", values.remote, values.branch], push],
      "Sync branch with remote",
      `Fetches ${values.remote}, rebases local ${values.branch} onto its remote branch, then pushes the synchronized result. Each command runs separately without a shell.`,
      RISK.CAUTION,
    );
  }

  function paths(operation, selectedPaths, hasHead = true) {
    const values = [...new Set(selectedPaths.filter(Boolean))];
    if (!values.length) throw new Error(`Select at least one file to ${operation === "changes.stage" ? "stage" : "unstage"}.`);
    if (operation === "changes.stage") {
      return command(operation, ["add", "--", ...values], "Stage selected files", `Adds ${values.length} selected file${values.length === 1 ? "" : "s"} to the next commit.`);
    }
    const args = hasHead ? ["restore", "--staged", "--", ...values] : ["rm", "--cached", "--", ...values];
    return command(operation, args, "Unstage selected files", `Removes ${values.length} selected file${values.length === 1 ? "" : "s"} from the next commit without discarding work.`);
  }

  function tokenize(input) {
    const tokens = [];
    let token = "";
    let quoteMode = null;
    let escaping = false;
    for (const character of input.trim()) {
      if (escaping) {
        token += character;
        escaping = false;
      } else if (character === "\\" && quoteMode !== "'") {
        escaping = true;
      } else if (quoteMode) {
        if (character === quoteMode) quoteMode = null;
        else token += character;
      } else if (character === "'" || character === '"') {
        quoteMode = character;
      } else if (/\s/.test(character)) {
        if (token) {
          tokens.push(token);
          token = "";
        }
      } else token += character;
    }
    if (escaping || quoteMode) throw new Error("The raw command contains an unfinished quote or escape.");
    if (token) tokens.push(token);
    return tokens;
  }

  function raw(input) {
    const tokens = tokenize(input);
    if (!tokens.length || !["git", "git.exe"].includes(tokens[0].toLowerCase())) throw new Error("Raw commands must begin with ‘git’. ");
    if (tokens.length === 1) throw new Error("Enter a Git subcommand after ‘git’. ");
    const args = tokens.slice(1);
    const lower = args.map((part) => part.toLowerCase());
    let risk = RISK.NORMAL;
    const destructive =
      (lower[0] === "reset" && lower.includes("--hard")) ||
      (lower[0] === "clean" && lower.slice(1).some((part) => /^-[a-z]*f/i.test(part))) ||
      (lower[0] === "push" && lower.slice(1).some((part) => ["-f", "--force", "--force-with-lease"].includes(part))) ||
      (lower[0] === "branch" && args.includes("-D"));
    if (destructive) risk = RISK.DESTRUCTIVE;
    else if (["merge", "rebase"].includes(lower[0]) || (lower[0] === "branch" && lower.includes("-d"))) risk = RISK.CAUTION;
    else if (["status", "log", "diff", "show", "fsck"].includes(lower[0])) risk = RISK.READ_ONLY;
    return command("raw", args, "Raw Git command", "Runs these arguments directly through Git without invoking a shell.", risk);
  }

  return { RISK, command, make, paths, quote, raw, sequence, syncRemote, tokenize };
});
