---
name: ship-change
description: Turn finished work in nightreign-boss-timer into a small pull request and get it merged. Use when asked to open a pull request, push a change, split work into pull requests, or merge a stack of pull requests in this repository.
---

# Ship a change

Changes reach `main` only through pull requests with green CI. The project owner reviews every
one, so each must be small and about one thing.

## 1. Size and scope

- One topic per pull request. Aim for a few hundred changed lines including tests.
- Split larger work along its seams, in this order: logic with no window (testable with plain
  arrays), then the widget, then the wiring into the app with its docs.
- When one part needs another, stack them: branch the second off the first and open its pull
  request against the first branch.

## 2. Before every push

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

All three must pass. CI runs the same on Linux (lint) and Windows (tests, Python 3.11 and 3.13).

Also check:

- A change a user can see has a line in `CHANGELOG.md` under "Unreleased", and
  `docs/USER_GUIDE.md` and `docs/INSTALL.md` say what the program now does. Mark what is still
  planned as planned.
- A new or changed public function or module is in `docs/API.md`. A test fails if a module is
  missing from it.
- New user-facing text is in all three translation files (see the `add-ui-text` skill).
- Nothing personal is in the diff: no real names, no user names in paths such as
  `C:\Users\<name>\...`, no email addresses. Use `git diff main` and read it.
- No game footage, and no full screenshots.

## 3. Commit and pull request

- Commit subject in the imperative: "Add bar detector", not "Added" or "Adds".
- Fill in `.github/PULL_REQUEST_TEMPLATE.md`: what and why, how it was tested, the checklist.
- Under "How it was tested", say what was run on a real screen and, plainly, what was **not**
  tested (for example "not tested against the real game").

```bash
git push -u origin <branch>
gh pr create --base main --head <branch> --title "<subject>" --body-file <file>
gh pr checks <number> --watch
```

## 4. Merging

Squash-merge once CI is green and the owner has approved, or has said to merge.

```bash
gh pr merge <number> --squash
```

### Merging a stack

Deleting a branch closes every pull request based on it, and a pull request whose base is gone
cannot be reopened. So, for pull requests A <- B <- C:

1. Retarget B and C to `main` first: `gh pr edit <number> --base main`.
2. Squash-merge A.
3. Move B's own commits onto the new `main` and push:

   ```bash
   git fetch origin
   git rebase --onto origin/main <branch-of-A> <branch-of-B>
   git push --force-with-lease origin <branch-of-B>
   ```

4. Wait for CI on B, squash-merge it, and repeat for C.
5. Delete the branches only after the whole stack is merged.

`CHANGELOG.md` conflicts during the rebase are resolved by keeping both sides.

## 5. After merging

```bash
git checkout main && git pull --ff-only
```
