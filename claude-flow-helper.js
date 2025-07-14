// Simple test to see if we can use claude-flow as a library
const { spawn } = require('child_process');
const path = require('path');

console.log("🤖 Running Claude-Flow to help with trading bot...\n");

// Find the claude-flow binary
const claudeFlowPath = path.join(__dirname, 'node_modules', '.bin', 'claude-flow');

// Run the command
const proc = spawn('node', [claudeFlowPath, 'hive-mind', 'spawn', 'Help improve my trading bot'], {
  stdio: 'inherit',
  env: { ...process.env, NODE_ENV: 'production' }
});

proc.on('error', (err) => {
  console.error('Error running claude-flow:', err);
  console.log('\nTrying alternative method...');
  
  // Alternative: run with tsx
  const tsxProc = spawn('npx', ['tsx', path.join(__dirname, 'node_modules/claude-flow/src/cli/cli-core.ts'), 'hive-mind', 'spawn', 'Help improve my trading bot'], {
    stdio: 'inherit'
  });
});
