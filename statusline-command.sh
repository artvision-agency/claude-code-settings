#!/bin/bash
# Claude Code statusLine command
# Reads JSON from stdin and outputs a status line

input=$(cat)

# Extract fields
cwd=$(echo "$input" | jq -r '.cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
remaining_pct=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
git_branch=$(echo "$input" | jq -r '.workspace.git_worktree // empty')
repo_owner=$(echo "$input" | jq -r '.workspace.repo.owner // empty')
repo_name=$(echo "$input" | jq -r '.workspace.repo.name // empty')
vim_mode=$(echo "$input" | jq -r '.vim.mode // empty')

# Shorten cwd: replace $HOME with ~
home="$HOME"
if [ -n "$cwd" ]; then
  short_cwd="${cwd/#$home/~}"
else
  short_cwd="~"
fi

# Build repo/branch segment
repo_seg=""
if [ -n "$repo_owner" ] && [ -n "$repo_name" ]; then
  repo_seg=" ${repo_owner}/${repo_name}"
fi
if [ -n "$git_branch" ]; then
  repo_seg="${repo_seg} (${git_branch})"
fi

# Build model segment
model_seg=""
if [ -n "$model" ]; then
  model_seg=" | ${model}"
fi

# Build context segment
ctx_seg=""
if [ -n "$used_pct" ]; then
  printf -v used_int "%.0f" "$used_pct" 2>/dev/null || used_int=""
  if [ -n "$used_int" ]; then
    if [ "$used_int" -ge 80 ]; then
      ctx_seg=" | ctx: ${used_int}%!"
    elif [ "$used_int" -ge 40 ]; then
      ctx_seg=" | ctx: ${used_int}%"
    else
      ctx_seg=" | ctx: ${used_int}%"
    fi
  fi
fi

# Build vim segment
vim_seg=""
if [ -n "$vim_mode" ]; then
  vim_seg=" [${vim_mode}]"
fi

printf "%s%s%s%s%s" "$short_cwd" "$repo_seg" "$model_seg" "$ctx_seg" "$vim_seg"
