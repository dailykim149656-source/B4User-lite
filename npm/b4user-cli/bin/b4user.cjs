#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function defaultRuntimeRoot() {
  if (process.env.B4USER_RUNTIME_DIR) {
    return process.env.B4USER_RUNTIME_DIR;
  }
  if (process.platform === 'win32') {
    return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'b4user', 'runtime');
  }
  return path.join(os.homedir(), '.b4user', 'runtime');
}

function defaultCliPath() {
  if (process.env.B4USER_PYTHON_CLI) {
    return process.env.B4USER_PYTHON_CLI;
  }
  const runtime = defaultRuntimeRoot();
  if (process.platform === 'win32') {
    return path.join(runtime, 'Scripts', 'b4user.exe');
  }
  return path.join(runtime, 'bin', 'b4user');
}

function failMissingCli(cliPath) {
  console.error(`B4User Python runtime was not found at: ${cliPath}`);
  console.error('Try reinstalling the npm package: npm install -g @b4user/cli');
  console.error('Or set B4USER_PYTHON_CLI to an existing b4user executable for development/testing.');
  process.exit(1);
}

const cliPath = defaultCliPath();
if (!fs.existsSync(cliPath)) {
  failMissingCli(cliPath);
}

function needsWindowsCommandShell(executablePath) {
  return process.platform === 'win32' && /\.(cmd|bat)$/i.test(executablePath);
}

const result = spawnSync(cliPath, process.argv.slice(2), {
  stdio: 'inherit',
  shell: needsWindowsCommandShell(cliPath),
  env: process.env,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
