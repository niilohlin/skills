---
name: t3-install
description: Ship the current T3 Code worktree to the installed desktop app. Commits the working tree, merges the branch into main, pushes to origin (niilohlin/t3code), merges the latest upstream (pingdotgg/t3code) into main, resolves conflicts, builds the macOS DMG and installs it over /Applications. Use when asked to "install", "ship", "t3-install", or "get my changes into the app".
---

# t3-install

Repo layout: the main checkout is `~/personal/t3code` on `main`. Work usually happens in a
worktree under `~/.t3/worktrees/t3code/<id>` on a `t3/<id>` branch. Remotes: `origin` is the
fork `niilohlin/t3code`, `upstream` is `pingdotgg/t3code`.

You are probably running inside the app you are about to replace. Never kill it. Install the
new bundle and tell the user to quit and relaunch.

## 1. Commit the worktree

In the current worktree:

```sh
git status --short
```

If there are changes, commit them all with a conventional-commit title that describes the
work (`fix(web): ...`, `feat(web): ...`). Revert `pnpm-lock.yaml` first if the only change
there is `@pnpm/exe` from a local `vp i`. Record the branch:

```sh
BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

If you are already on `main` in `~/personal/t3code`, skip to step 3 after committing.

## 2. Merge into main and push

Run from the main checkout so no worktree is left on a detached state:

```sh
cd ~/personal/t3code
git status --short            # must be clean; stop and ask if not
git merge --no-edit "$BRANCH"
git push origin main
```

A merge conflict here means another branch landed on main after this one forked. Resolve it
in favour of keeping both behaviours, then `git commit` and push.

## 3. Merge upstream

```sh
git fetch upstream
git merge --no-edit upstream/main
```

On conflicts, resolve each file:

- Lockfile (`pnpm-lock.yaml`): take upstream's version, then run `vp i` to regenerate.
- Generated or snapshot files: take upstream's version and regenerate if a script exists.
- Source: keep the fork's intent and upstream's new code. Read both sides; do not pick a side
  blindly. Run `vp run check:changed` afterwards. Fix what it reports.

Then:

```sh
git commit --no-edit   # if the merge was conflicted
git push origin main
```

## 4. Build and install

```sh
vp i
vp run dist:desktop:dmg
```

The artifact lands in `release/`. Install the zip (same bundle as the DMG, no mounting):

```sh
ZIP=$(ls -t release/T3-Code-*-arm64.zip | head -1)
rm -rf "/Applications/T3 Code (Beta).app"
ditto -x -k "$ZIP" /Applications
codesign --verify --deep "/Applications/T3 Code (Beta).app" || echo "unsigned local build, expected"
```

The app name comes from `productName` in `apps/desktop/package.json`; check it if the path
above does not exist.

## 5. Report

Say which commits were merged (fork branch and upstream range), whether conflicts were
resolved and in which files, the version from `apps/desktop/package.json`, and that the
user must quit and relaunch T3 Code to run the new build. Do not relaunch it yourself.
