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
# Runs with cwd = the project's configured Root Directory, so `-- .`
# scopes the diff to that project's own files, same as the command it
# replaces.
set -uo pipefail

BASE="${VERCEL_GIT_PREVIOUS_SHA:-}"

if [ -z "$BASE" ] || ! git cat-file -e "${BASE}^{commit}" 2>/dev/null; then
  BASE="HEAD^"
fi

git diff "$BASE" HEAD --quiet -- .
