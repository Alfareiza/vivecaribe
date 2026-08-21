#!/usr/bin/env bash
# Vercel "Ignored Build Step" for both projects (vivecaribe, vivecaribe-frontend).
#
# Exit 0 => skip the build, exit 1 => proceed with the build (Vercel's
# convention, matched by `git diff --quiet`'s own exit codes).
#
# Compares against $VERCEL_GIT_PREVIOUS_SHA (the last commit Vercel actually
# deployed for THIS project) instead of HEAD^ (the new commit's immediate
# git parent). A single push can carry multiple commits (e.g. GitHub
# "Rebase and merge" landing a multi-commit PR); if the relevant change
# lives earlier than the tip commit, an unqualified `HEAD^` diff comes up
# empty and the build is silently skipped even though real changes exist
# relative to what's live in production. Hit this on #66 and #73.
#
# $VERCEL_GIT_PREVIOUS_SHA is only set once a project has a prior deploy to
# compare against — it's empty on the very first preview build of a new
# branch. Falling straight back to HEAD^ there has the exact same failure
# mode as above: if that branch's own tip commit is a docs-only trailing
# commit (e.g. a feature commit followed by a `docs(memory-bank)` commit,
# pushed together in one go), HEAD^ only sees that last commit's own empty
# diff and skips the build even though the branch as a whole has real
# changes. Hit this on #81's first preview push. Fall back to the
# merge-base with main instead — i.e. diff everything since this branch
# actually diverged — and only drop to HEAD^ if that can't be resolved
# either (e.g. main itself isn't fetched in this checkout).
#
# Runs with cwd = the project's configured Root Directory, so `-- .`
# scopes the diff to that project's own files, same as the command it
# replaces.
set -uo pipefail

BASE="${VERCEL_GIT_PREVIOUS_SHA:-}"

if [ -z "$BASE" ] || ! git cat-file -e "${BASE}^{commit}" 2>/dev/null; then
  BASE=""
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    BASE="$(git merge-base origin/main HEAD 2>/dev/null || true)"
  fi
  if [ -z "$BASE" ] || ! git cat-file -e "${BASE}^{commit}" 2>/dev/null; then
    BASE="HEAD^"
  fi
fi

git diff "$BASE" HEAD --quiet -- .
