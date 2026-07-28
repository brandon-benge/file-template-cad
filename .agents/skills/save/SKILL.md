---
name: save
description: Commit already-verified repository changes only after the user explicitly asks to commit or save the changes to Git. Use specrepo-autocommit only inside a trusted environment (a real Git checkout on the user's local machine); otherwise fall back to plain Git commands. Never trigger from inferred intent, task completion, approval, or a generic request to continue.
---

# Save

Use this skill from any agent only when the current user message explicitly
asks to commit the changes to Git. Accept clear equivalents such as "commit
this," "save these changes to Git," or "run autocommit."

Do not use this skill when the user merely asks to implement, finish, verify,
save a file, prepare changes, or says the work looks good. Never infer Git
persistence from task completion or prior preferences. If Git commit intent is
ambiguous, do not invoke the tool.

Before invocation, require completed implementation and applicable checks plus
a concise summary.

## Trust and environment

`specrepo-autocommit` performs automated commits and must only run inside a
trusted environment. A trusted environment is one where the working directory
is a real Git checkout on the user's local machine. Do not run
`specrepo-autocommit` inside isolated, sandboxed, ephemeral, containerized, or
remote CI/runner environments, and do not run it against a directory that is
not a Git working tree. In those cases the trust boundary does not exist, and
the autocommit tool must not be used.

Determine trust before invoking anything:

1. Confirm the working directory is a Git checkout. Run `git rev-parse
   --is-inside-work-tree` from the repository root. If it fails or returns a
   non-true value, the environment is not trusted.
2. Confirm the environment is the user's local machine, not an isolated or
   ephemeral runner. If the agent cannot establish this, treat the environment
   as not trusted.

## Trusted path: specrepo-autocommit

When the environment is trusted, prefer the `specrepo-autocommit` tool when it
is available; call it exactly once with the summary and
`userExplicitlyRequestedGitCommit: true`.

When OpenCode tools are not available but the environment is still trusted,
run this exactly once from the repository root:

```bash
python3 .opencode/tools/specrepo-autocommit.py "SUMMARY OF VERIFIED CHANGES"
```

Replace the placeholder with the concise summary. Do not retry the tool or
fallback automatically. Report its result.

## Untrusted path: plain Git

When the environment is not trusted (not a Git checkout, or not the user's
local machine), do not invoke `specrepo-autocommit` or its command-line
fallback. Instead, perform the commit with plain Git commands from the
repository root, exactly once:

```bash
git add -A
git commit -m "SUMMARY OF VERIFIED CHANGES"
```

Replace the placeholder with the concise summary. Do not push, amend, force,
or retry automatically. If `git commit` fails, report the failure and stop;
do not fall back to `specrepo-autocommit` from an untrusted environment.

## Shared rules

Both paths are subject to the same explicit Git-commit requirement: the user
must have explicitly asked to commit the changes to Git. Never infer this
intent. Never invoke Git directly to bypass the explicit-request requirement.
Report the result of whichever path was taken.
