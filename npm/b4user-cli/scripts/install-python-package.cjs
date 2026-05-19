#!/usr/bin/env node
'use strict';

const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PACKAGE_VERSION = '0.1.2';

function log(message) {
  console.log(`[b4user] ${message}`);
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    text: true,
    shell: false,
    env: process.env,
  });
  return result;
}

function isPython311OrNewer(command, prefixArgs = []) {
  const result = run(command, [...prefixArgs, '-c', 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")'], { capture: true });
  if (result.status !== 0) {
    return false;
  }
  const [major, minor] = result.stdout.trim().split('.').map(Number);
  return major > 3 || (major === 3 && minor >= 11);
}

function candidatePythons() {
  if (process.env.B4USER_PYTHON) {
    return [process.env.B4USER_PYTHON];
  }
  if (process.platform === 'win32') {
    return ['py -3.11', 'python', 'python3'];
  }
  return ['python3.11', 'python3', 'python'];
}

function splitCommand(raw) {
  // Good enough for launcher discovery: supports the Windows `py -3.11` form.
  return raw.split(' ').filter(Boolean);
}

function findPython() {
  for (const raw of candidatePythons()) {
    const parts = splitCommand(raw);
    const command = parts[0];
    const prefixArgs = parts.slice(1);
    const result = run(command, [...prefixArgs, '-c', 'import sys; print(sys.executable)'], { capture: true });
    if (result.status === 0 && isPython311OrNewer(command, prefixArgs)) {
      return { command, prefixArgs, executable: result.stdout.trim() };
    }
  }
  return null;
}

function pythonRun(python, args, options = {}) {
  return run(python.command, [...python.prefixArgs, ...args], options);
}

function defaultRuntimeRoot() {
  if (process.env.B4USER_RUNTIME_DIR) {
    return process.env.B4USER_RUNTIME_DIR;
  }
  if (process.platform === 'win32') {
    return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local'), 'b4user', 'runtime');
  }
  return path.join(os.homedir(), '.b4user', 'runtime');
}

function cliPath(runtimeRoot) {
  if (process.platform === 'win32') {
    return path.join(runtimeRoot, 'Scripts', 'b4user.exe');
  }
  return path.join(runtimeRoot, 'bin', 'b4user');
}

function checkMode() {
  const packageJson = path.resolve(__dirname, '..', 'package.json');
  const bin = path.resolve(__dirname, '..', 'bin', 'b4user.cjs');
  if (!fs.existsSync(packageJson)) {
    throw new Error(`missing package.json: ${packageJson}`);
  }
  if (!fs.existsSync(bin)) {
    throw new Error(`missing launcher: ${bin}`);
  }
  log('B4User npm installer check passed');
}

function localSourceSpec() {
  const candidate = path.resolve(__dirname, '..', '..', '..');
  if (fs.existsSync(path.join(candidate, 'pyproject.toml')) && fs.existsSync(path.join(candidate, 'src', 'b4user'))) {
    return candidate;
  }
  return null;
}

function defaultPackageSpec() {
  return process.env.B4USER_PYTHON_PACKAGE_SPEC || localSourceSpec() || `b4user==${PACKAGE_VERSION}`;
}

function install() {
  if (process.env.B4USER_SKIP_PYTHON_INSTALL === '1') {
    log('Skipping Python runtime install because B4USER_SKIP_PYTHON_INSTALL=1');
    return;
  }
  const python = findPython();
  if (!python) {
    console.error('B4User requires Python 3.11+ to install the Python runtime.');
    console.error('Install Python from https://www.python.org/downloads/ or with: winget install Python.Python.3.11');
    console.error('Then rerun: npm install -g @b4user/cli');
    process.exit(1);
  }

  const runtimeRoot = defaultRuntimeRoot();
  const spec = defaultPackageSpec();
  log(`Using Python: ${python.executable}`);
  log(`Creating/updating runtime: ${runtimeRoot}`);
  const venv = pythonRun(python, ['-m', 'venv', runtimeRoot]);
  if (venv.status !== 0) {
    process.exit(venv.status ?? 1);
  }

  const runtimePython = process.platform === 'win32'
    ? path.join(runtimeRoot, 'Scripts', 'python.exe')
    : path.join(runtimeRoot, 'bin', 'python');

  log('Upgrading pip');
  let result = run(runtimePython, ['-m', 'pip', 'install', '--upgrade', 'pip']);
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }

  log(`Installing ${spec}`);
  result = run(runtimePython, ['-m', 'pip', 'install', '--upgrade', spec]);
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }

  const installedCli = cliPath(runtimeRoot);
  if (!fs.existsSync(installedCli)) {
    console.error(`Install finished but b4user executable was not found at: ${installedCli}`);
    process.exit(1);
  }
  log(`Installed. Run: b4user --help`);
}

try {
  if (process.argv.includes('--check')) {
    checkMode();
  } else {
    install();
  }
} catch (error) {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
}
