const $ = id => document.getElementById(id);

let activeSessionId = null;
let sessions = {};
let sending = false;
let debugMode = false;
let selectedMode = null;
let selectedModel = null;
let selectedTurnLimit = null;

let PROVIDER_LOGOS = {};
let MODEL_LOGOS = {};
let MODEL_DISPLAY_NAMES = { 'auto': 'Auto' };
let ENV_LOGOS = {};
let MODE_ICONS = { 'meta-agent': 'bx-brain', agent: 'bx-bot', plan: 'bx-edit', ask: 'bx-chat' };
let MODE_LABELS = { 'meta-agent': 'Meta-Agent', agent: 'Agent', plan: 'Plan', ask: 'Ask' };
const AI_IDE_PROVIDERS = new Set(['cursor', 'copilot', 'windsurf', 'github-copilot']);
const _iconCache = {};
