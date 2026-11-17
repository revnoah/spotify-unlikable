---
name: git-branch
description: Prepare and deliver changes through feature or bugfix branches, with consistent brief commit messages and pull request comments. Use when asked to branch, commit, push, or complete a Git delivery workflow.
---

# Git branch workflow

Carry out the Git steps the user requested. A request for the full workflow includes branch creation, commit, push, pull request, merge, fetch, and local synchronization. A request only to commit does not authorize pushing or merging. Existing explicit authorization does not need to be requested again.

## Branches

- Use `feature/<feature-name>` for added capabilities and `bugfix/<bug-being-fixed>` for corrections.
- Use short, descriptive, lowercase names with hyphens, such as `feature/network-access` or `bugfix/expired-login`.
- Inspect repository instructions, status, current branch, remote, and default branch before changes. Fetch the remote before choosing the base when available.
- Start new work from the updated default branch. For changes already in progress, preserve their actual base and all uncommitted work; inspect divergence before publishing.
- Continue an existing suitable branch. Do not overwrite an unrelated branch; choose a descriptive suffix if a name is already taken.

## Messages

Use a short imperative subject: `feat: Enable network access` or `fix: Refresh expired sessions`.

Commit bodies, pull request descriptions, and workflow comments should be brief, flat bullet points. Describe the resulting behavior and relevant validation; omit conversational history and redundant comments. Use the same subject style for pull request titles and squash commits.

Example:

```text
feat: Enable network access

- Accept connections from other devices.
- Add configurable HTTPS certificates.
- Validate backend and frontend checks.
```

Report only checks actually run. If a separate PR comment is requested, use a short bullet list for information beyond the description.

## Delivery

- Review the diff and stage only intended files. Exclude credentials, sessions, caches, and unrelated edits. Run checks appropriate to the change.
- Commit and push the feature or bugfix branch with an upstream. Create or update its pull request against the confirmed default branch when requested.
- Before an authorized merge, inspect the final diff, current head, checks, and mergeability. Honor required checks and branch protections. Prefer squash when supported unless repository conventions or the user specify otherwise. Tie the merge to the reviewed head SHA when the tool supports it.
- Stop on failed required checks, unresolved conflicts, permission failures, or an unexpected head change. Inspect the new state before retrying; do not repeatedly retry unchanged failures or bypass protections.
- After confirmed merge, fetch with pruning, switch to the default branch when the working tree permits it, and update using fast-forward only. Preserve unrelated local changes. Clean up merged feature branches only when requested or established repository conventions call for it.
- Prefer connected GitHub tools for supported remote operations. Use local Git for checkout, staging, and synchronization. If metadata or filesystem access is unavailable, complete the supported steps and report exactly which local steps remain; do not claim a local fetch or checkout occurred.
- Finish with concise bullets giving the branch, commit or PR link, merge status, validation, and any remaining synchronization step.
