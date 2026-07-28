---
description: Commit verified repository changes after an explicit user request
---

Load the `save` skill and follow it exactly. Proceed only when the user
explicitly asked to commit the changes to Git.

Save the already-verified repository changes by calling the native OpenCode
tool `specrepo-autocommit` exactly once with
`userExplicitlyRequestedGitCommit: true`. Use `$ARGUMENTS` as its `summary` when
the value is non-empty; otherwise use `Save verified repository changes`.

Do not inspect or edit files, run tests, call shell commands, invoke Git
directly, or use any fallback. Report the single tool call's completed,
blocked, rejected, or failed result.
