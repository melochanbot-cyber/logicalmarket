#!/usr/bin/env node

/**
 * Risk Barometer Alert System
 * 
 * Checks the risk barometer data and sends alerts when assets hit WARNING or DANGER levels.
 * 
 * Usage:
 *   node scripts/risk-alert.mjs [--dry-run] [--feishu-chat-id=xxx]
 * 
 * Environment:
 *   FEISHU_CHAT_ID - Feishu chat ID for alerts (default: from argv or none)
 * 
 * Alert Levels:
 *   - DANGER (71-100): Always alert
 *   - WARNING (51-70): Alert once per day per asset
 *   - CAUTION (31-50): No alert (monitor only)
 *   - LOW (0-30): No alert
 * 
 * State tracking in data/alert-state.json prevents spam.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE = path.resolve(__dirname, '..');
const BAROMETER_FILE = path.join(WORKSPACE, 'data', 'risk-barometer.json');
const STATE_FILE = path.join(WORKSPACE, 'data', 'alert-state.json');

// Parse CLI args
const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const feishuChatId = args.find(a => a.startsWith('--feishu-chat-id='))?.split('=')[1] 
                    || process.env.FEISHU_CHAT_ID;

// Alert thresholds
const LEVELS = {
  DANGER: { min: 71, emoji: '🔴', priority: 3 },
  WARNING: { min: 51, emoji: '🟠', priority: 2 },
  CAUTION: { min: 31, emoji: '🟡', priority: 1 },
  LOW: { min: 0, emoji: '🟢', priority: 0 },
};

function loadBarometer() {
  if (!fs.existsSync(BAROMETER_FILE)) {
    throw new Error(`Barometer file not found: ${BAROMETER_FILE}`);
  }
  return JSON.parse(fs.readFileSync(BAROMETER_FILE, 'utf-8'));
}

function loadState() {
  if (!fs.existsSync(STATE_FILE)) {
    return { lastAlerts: {} };
  }
  return JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
}

function saveState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

function shouldAlert(asset, level, score, state) {
  const now = Date.now();
  const lastAlert = state.lastAlerts[asset] || {};
  
  // DANGER: always alert
  if (level === 'DANGER') {
    return true;
  }
  
  // WARNING: alert once per day
  if (level === 'WARNING') {
    const lastWarning = lastAlert.WARNING || 0;
    const hoursSince = (now - lastWarning) / (1000 * 60 * 60);
    return hoursSince >= 24;
  }
  
  // CAUTION/LOW: no alert
  return false;
}

function updateState(state, asset, level) {
  if (!state.lastAlerts[asset]) {
    state.lastAlerts[asset] = {};
  }
  state.lastAlerts[asset][level] = Date.now();
}

function formatAlert(asset, barometer) {
  const { score, level, signals, recommendation } = barometer;
  const levelInfo = LEVELS[level];
  
  let message = `${levelInfo.emoji} **${asset.toUpperCase()} Risk Alert**\n\n`;
  message += `**Level:** ${level} (${score}/100)\n`;
  message += `**Recommendation:** ${recommendation}\n\n`;
  message += `**Triggered Signals:**\n`;
  
  const triggered = signals.filter(s => s.triggered);
  for (const signal of triggered) {
    message += `• ${signal.name} (+${signal.points} pts) - ${signal.detail}\n`;
  }
  
  return message;
}

async function sendFeishuAlert(message) {
  if (!feishuChatId) {
    console.log('⚠️  No Feishu chat ID configured - skipping message send');
    return false;
  }
  
  // This would use the actual Feishu message API
  // For now, just log that we would send it
  console.log(`📨 Would send to Feishu chat ${feishuChatId}:`);
  console.log(message);
  console.log();
  
  // TODO: Integrate with OpenClaw message tool or Feishu API
  // Example:
  // const { message: messageTool } = await import('../../tools/feishu-message.mjs');
  // await messageTool({ action: 'send', target: feishuChatId, message });
  
  return true;
}

async function main() {
  try {
    console.log('🔍 Checking risk barometer...\n');
    
    const barometer = loadBarometer();
    const state = loadState();
    const alerts = [];
    
    // Check each asset
    for (const [asset, data] of Object.entries(barometer.barometers)) {
      const { score, level } = data;
      console.log(`${asset.padEnd(10)} ${level.padEnd(8)} ${score}/100`);
      
      if (shouldAlert(asset, level, score, state)) {
        alerts.push({ asset, data });
        console.log(`  → Alert triggered`);
      }
    }
    
    console.log();
    
    if (alerts.length === 0) {
      console.log('✅ No alerts triggered');
      return;
    }
    
    console.log(`🚨 ${alerts.length} alert(s) to send:\n`);
    
    for (const { asset, data } of alerts) {
      const message = formatAlert(asset, data);
      
      if (dryRun) {
        console.log('--- DRY RUN ---');
        console.log(message);
        console.log('---------------\n');
      } else {
        await sendFeishuAlert(message);
        updateState(state, asset, data.level);
      }
    }
    
    if (!dryRun) {
      saveState(state);
      console.log('✅ State updated');
    }
    
  } catch (err) {
    console.error('❌ Error:', err.message);
    process.exit(1);
  }
}

main();
