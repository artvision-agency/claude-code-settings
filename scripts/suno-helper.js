#!/usr/bin/env node
/**
 * Suno Helper — надёжная автоматизация Suno через Playwright
 *
 * Использование:
 *   node ~/.claude/scripts/suno-helper.js status        — проверить статус браузера
 *   node ~/.claude/scripts/suno-helper.js fix-chrome     — убить зомби Chrome + очистить locks
 *
 * Для использования из Claude Code:
 *   Bash: node ~/.claude/scripts/suno-helper.js <command>
 */

const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const CHROME_DIR = path.join(process.env.HOME, 'Library', 'Application Support', 'Google', 'Chrome for Testing');

function safeExec(cmd, args) {
  try {
    return execFileSync(cmd, args, { encoding: 'utf8', timeout: 10000 }).trim();
  } catch {
    return '';
  }
}

function fixChrome() {
  console.log('Fixing Chrome for Testing...');

  // Kill all Chrome for Testing processes
  safeExec('pkill', ['-9', '-f', 'Chrome for Testing']);

  // Remove lock files
  const locks = ['SingletonLock', 'SingletonSocket', 'SingletonCookie'];
  for (const lock of locks) {
    const lockPath = path.join(CHROME_DIR, lock);
    try {
      fs.unlinkSync(lockPath);
      console.log(`  Removed ${lock}`);
    } catch {
      // File doesn't exist
    }
  }

  console.log('Done. Wait 3 seconds before using Playwright.');
  console.log('Hint: use browser_navigate to reopen suno.com/create');
}

function checkStatus() {
  const chromeProcs = safeExec('pgrep', ['-f', 'Chrome for Testing']);
  const procCount = chromeProcs ? chromeProcs.split('\n').length : 0;
  const hasLock = fs.existsSync(path.join(CHROME_DIR, 'SingletonLock'));

  console.log('=== Chrome for Testing Status ===');
  console.log(`Processes: ${procCount}`);
  console.log(`SingletonLock: ${hasLock ? 'EXISTS' : 'none'}`);

  if (procCount > 0 && !hasLock) {
    console.log('Status: HEALTHY');
  } else if (procCount === 0 && hasLock) {
    console.log('Status: STALE LOCK (run: fix-chrome)');
  } else if (procCount === 0) {
    console.log('Status: NOT RUNNING');
  } else {
    console.log('Status: OK');
  }
}

// Main
const cmd = process.argv[2] || 'status';

switch (cmd) {
  case 'status':
    checkStatus();
    break;
  case 'fix-chrome':
  case 'fix':
    fixChrome();
    break;
  default:
    console.log(`Unknown command: ${cmd}`);
    console.log('Usage: suno-helper.js [status|fix-chrome]');
}
