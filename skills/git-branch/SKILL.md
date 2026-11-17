---
name: git-branch
description: Prepare and deliver changes through feature or bugfix branches, with consistent brief commit messages and pull request comments. Use when asked to branch, commit, push, or complete a Git delivery workflow.
---

# Git branch workflow

Carry out the Git steps the user requested. A request for the full workflow includes branch creation, commit, push, pull request, merge, merged-branch cleanup, fetch, and local synchronization. A request only to commit does not authorize pushing or merging. Existing explicit authorization does not need to be requested again.

## Branches

- Use `feature/<feature-name>` for added capabilities and `bugfix/<bug-being-fixed>` for corrections.
- Use short, descriptive, lowercase names with hyphens, such as `feature/network-access` or `bugfix/expired-login`.
- Inspect repository instructions, status (including untracked files), current branch, remote, and remote default branch (`main` or `master`); do not guess the base.
- Begin each new task from an updated local default branch, even when edits already exist. If the tree is dirty, stash tracked and untracked changes with a descriptive message and record the stash object ID before switching branches. Do not stash ignored secrets or caches.
- Switch to the default branch, fetch with pruning, inspect divergence, then pull using fast-forward only. A local branch ahead of or diverged from the remote requires inspection; preserve its commits instead of resetting it automatically. If fetching or pulling fails, stop the delivery workflow rather than silently using a stale base.
- Apply the recorded stash to the updated default branch with `git stash apply --index <stash-id>`, retaining the stash until recovery is verified. Resolve conflicts while preserving both upstream and local work; stop if their intended resolution is unclear. Create the new `feature/...` or `bugfix/...` branch carrying the restored edits before making any commit. Drop only the recorded stash after confirming restoration and the new branch; leave unrelated stashes alone.
- If there are no local edits, update the default branch and create the new branch directly. A request to continue an existing PR or branch is an exception: update and inspect that branch without discarding its history.
- Do not overwrite an unrelated branch; choose a descriptive suffix if a name is already taken.

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
- After confirmed merge, fetch with pruning, switch to the default branch when the working tree permits it, and update using fast-forward only. Preserve unrelated local changes. For the full workflow, delete the remote feature or bugfix branch after verifying the PR is merged and its head has no subsequent commits. Then prune remote refs and remove the local branch after switching to the updated default branch. Squash merges create a new commit SHA, so an undeleted source branch can appear ahead and behind even when its changes are merged. Verify the merged PR and unchanged source head before removing a squash-merged local branch; do not rely on ancestry alone. Preserve branches with new work. If deletion is unavailable, report the remaining branch explicitly and link the merged PR for manual cleanup. When the user requests fixing an existing divergent merged branch, first verify the PR is merged, the source head is unchanged, and its tree matches the merged result. A lease-protected ref update to the current default branch can then align it without dropping unmerged content; never force-update a branch with additional work.
- Prefer connected GitHub tools for supported remote operations. Use local Git for checkout, staging, and synchronization. If metadata or filesystem access is unavailable, complete the supported steps and report exactly which local steps remain; do not claim a local fetch or checkout occurred.
- Finish with concise bullets giving the branch, commit or PR link, merge status, validation, and any remaining synchronization step.
