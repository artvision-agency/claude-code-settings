#!/usr/bin/env bash
# cc-aliases.sh — Shell aliases for the cc-session named-sessions system
#
# Source this file from ~/.bashrc or ~/.zshrc:
#   source ~/.claude/scripts/cc-aliases.sh
#
# Or add to shell profile (one-time):
#   echo 'source ~/.claude/scripts/cc-aliases.sh' >> ~/.zshrc

# Resume a named Claude Code session.
#   Usage: cc-resume <name>          exact or fuzzy match
#          cc-resume <uuid>          direct session ID
cc-resume() {
  ~/.claude/scripts/cc-session.sh resume "$@"
}

# Name the current (latest) Claude Code session.
#   Usage: cc-name <name>
cc-name() {
  ~/.claude/scripts/cc-session.sh name "$@"
}

# List named Claude Code sessions.
#   Usage: cc-sessions              all saved sessions
#          cc-sessions --active     sessions from last 7 days
cc-sessions() {
  ~/.claude/scripts/cc-session.sh list "$@"
}

# Launch Claude Code with Telegram channel bridge.
#   Usage: cc-hub            start new session with TG
#          cc-hub --resume   resume last session with TG
alias cc-hub='claude --channels plugin:telegram@claude-plugins-official'
