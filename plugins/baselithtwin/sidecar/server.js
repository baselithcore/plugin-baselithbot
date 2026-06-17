/**
 * BaselithTwin WhatsApp sidecar (whatsapp-web.js).
 *
 * A small, maintained replacement for the abandoned @open-wa/wa-automate. It:
 *   - authenticates a WhatsApp Web session (QR on first run, persisted after);
 *   - pushes every inbound message to the plugin webhook
 *     (POST {PLUGIN_WEBHOOK_URL} with header X-Webhook-Secret);
 *   - exposes the *same* minimal REST the plugin's OpenWAGateway already calls
 *     (/getConnectionState, /sendText, /sendImage), Bearer-authenticated with
 *     API_KEY — so the Python side needs ZERO changes: keep GATEWAY=openwa and
 *     point BASELITH_TWIN_OPENWA_BASE_URL at this process.
 *
 * Env:
 *   PORT                 REST port (default 8002; match the plugin base URL).
 *   API_KEY              Bearer key required on REST calls (match the plugin).
 *   SESSION              Session name for LocalAuth persistence.
 *   PLUGIN_WEBHOOK_URL   Where to push inbound messages.
 *   WEBHOOK_SECRET       Shared secret sent as X-Webhook-Secret.
 *   HEADLESS             "false" to show the browser window (default true).
 */

const crypto = require('crypto');
const dns = require('dns').promises;
const fs = require('fs');
const net = require('net');
const path = require('path');
const express = require('express');
const qrcode = require('qrcode-terminal');
const { Client, LocalAuth } = require('whatsapp-web.js');

/**
 * Read the repo-root .env so the sidecar shares the SAME credentials as the
 * plugin (no drift / secret mismatch). Explicit process.env always wins; the
 * .env only fills gaps. Maps the plugin's BASELITH_TWIN_* keys onto the
 * sidecar's short names.
 */
function loadRepoEnv() {
  const envPath = path.resolve(__dirname, '../../../.env');
  let raw = '';
  try {
    raw = fs.readFileSync(envPath, 'utf8');
  } catch {
    return {};
  }
  const map = {};
  for (const line of raw.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const eq = t.indexOf('=');
    if (eq < 0) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
      v = v.slice(1, -1);
    }
    map[k] = v;
  }
  return {
    API_KEY: map.BASELITH_TWIN_OPENWA_API_KEY,
    WEBHOOK_SECRET: map.BASELITH_TWIN_WEBHOOK_SECRET,
    SESSION: map.BASELITH_TWIN_OPENWA_SESSION,
  };
}

const REPO = loadRepoEnv();

const PORT = parseInt(process.env.PORT || '8002', 10);
// Fail-closed: a missing API key would leave the send API world-readable.
const API_KEY = process.env.API_KEY || REPO.API_KEY || '';
if (!API_KEY) {
  console.error(
    '[sidecar] API_KEY is required (set it to the same value as ' +
      'BASELITH_TWIN_OPENWA_API_KEY). Refusing to start without auth.'
  );
  process.exit(1);
}
const SESSION = process.env.SESSION || REPO.SESSION || 'baselith-twin';
const PLUGIN_WEBHOOK_URL =
  process.env.PLUGIN_WEBHOOK_URL || 'http://localhost:8000/api/baselithtwin/webhook';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || REPO.WEBHOOK_SECRET || '';
const HEADLESS = (process.env.HEADLESS || 'true') !== 'false';

let ready = false;
// Ids we sent via the REST API — skipped on inbound so the twin never
// re-ingests its own auto-sent replies as "owner style" (avoids a feedback loop).
const ownSentIds = new Set();
// Ids already forwarded — `message` and `message_create` can both fire for the
// same message, so we dedupe to forward each exactly once.
const forwardedIds = new Set();

const client = new Client({
  authStrategy: new LocalAuth({ clientId: SESSION }),
  puppeteer: {
    headless: HEADLESS,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
});

client.on('qr', (qr) => {
  console.log('[sidecar] Scan this QR with WhatsApp → Linked devices:');
  qrcode.generate(qr, { small: true });
});
client.on('authenticated', () => console.log('[sidecar] authenticated'));
client.on('auth_failure', (m) => console.error('[sidecar] auth failure:', m));
client.on('ready', () => {
  ready = true;
  console.log(`[sidecar] WhatsApp ready (session=${SESSION})`);
});
client.on('disconnected', (r) => {
  ready = false;
  console.warn('[sidecar] disconnected:', r);
});

/** Whether an IP literal is in a non-public (loopback/private/LL/ULA) range. */
function isBlockedIp(ip) {
  const v = net.isIP(ip);
  if (v === 4) {
    const p = ip.split('.').map(Number);
    if (p[0] === 10) return true; // 10/8
    if (p[0] === 127) return true; // loopback
    if (p[0] === 169 && p[1] === 254) return true; // link-local
    if (p[0] === 172 && p[1] >= 16 && p[1] <= 31) return true; // 172.16/12
    if (p[0] === 192 && p[1] === 168) return true; // 192.168/16
    if (p[0] === 100 && p[1] >= 64 && p[1] <= 127) return true; // CGNAT 100.64/10
    if (p[0] === 0 || p[0] >= 224) return true; // this-host / multicast / reserved
    return false;
  }
  if (v === 6) {
    const ip6 = ip.toLowerCase();
    if (ip6 === '::1' || ip6 === '::') return true; // loopback / unspecified
    if (ip6.startsWith('fe80')) return true; // link-local
    if (ip6.startsWith('fc') || ip6.startsWith('fd')) return true; // ULA fc00::/7
    if (ip6.startsWith('::ffff:')) return isBlockedIp(ip6.slice(7)); // v4-mapped
    return false;
  }
  return true; // not an IP literal → treat as unsafe
}

/** Resolve a URL's host and reject https-less or private-range targets. */
async function assertSafeUrl(raw) {
  let u;
  try {
    u = new URL(raw);
  } catch {
    throw new Error('invalid url');
  }
  if (u.protocol !== 'https:') throw new Error('only https urls are allowed');
  const targets = net.isIP(u.hostname)
    ? [{ address: u.hostname }]
    : await dns.lookup(u.hostname, { all: true });
  for (const { address } of targets) {
    if (isBlockedIp(address)) throw new Error(`blocked host: ${address}`);
  }
  return u.toString();
}

/** SSRF-safe image fetch: validate every redirect hop, then return media. */
async function fetchImageSafely(raw, maxRedirects = 3) {
  const { MessageMedia } = require('whatsapp-web.js');
  let url = raw;
  for (let hop = 0; hop <= maxRedirects; hop++) {
    url = await assertSafeUrl(url);
    const res = await fetch(url, { redirect: 'manual' });
    if (res.status >= 300 && res.status < 400 && res.headers.get('location')) {
      url = new URL(res.headers.get('location'), url).toString();
      continue; // re-validated on the next loop iteration
    }
    if (!res.ok) throw new Error(`fetch failed: ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    const mime = (res.headers.get('content-type') || 'application/octet-stream')
      .split(';')[0]
      .trim();
    if (!mime.startsWith('image/')) throw new Error('not an image');
    return new MessageMedia(mime, buf.toString('base64'));
  }
  throw new Error('too many redirects');
}

/** Forward one message to the plugin webhook. */
async function pushInbound(msg) {
  const mid = msg.id._serialized;
  if (ownSentIds.delete(mid)) return; // our own API send
  if (forwardedIds.has(mid)) return; // already forwarded by the other event
  forwardedIds.add(mid);
  if (forwardedIds.size > 2000) forwardedIds.clear(); // bound memory
  console.log(`[sidecar] → forwarding ${mid} from=${msg.from} fromMe=${msg.fromMe}`);
  const payload = {
    id: msg.id._serialized,
    contact_id: msg.from,
    contact_name: msg._data && msg._data.notifyName ? msg._data.notifyName : null,
    text: msg.body || '',
    from_me: msg.fromMe === true,
    media: msg.hasMedia ? { kind: 'image', caption: msg.body || null } : null,
  };
  try {
    const res = await fetch(PLUGIN_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Secret': WEBHOOK_SECRET,
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) console.error('[sidecar] webhook', res.status, await res.text());
  } catch (e) {
    console.error('[sidecar] webhook push failed:', e.message);
  }
}

// Listen to BOTH events: `message` is the reliable inbound trigger, while
// `message_create` also carries the owner's own outbound (style data). Dedup in
// pushInbound forwards each message exactly once.
client.on('message', (msg) => void pushInbound(msg));
client.on('message_create', (msg) => void pushInbound(msg));

client.initialize();

// -- REST surface (OpenWA-compatible subset) --------------------------------

const app = express();
app.use(express.json({ limit: '2mb' }));

// Bearer auth on every REST call, constant-time to avoid timing oracles.
app.use((req, res, next) => {
  const auth = req.headers.authorization || '';
  const expected = `Bearer ${API_KEY}`;
  const a = Buffer.from(auth);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    return res.status(401).json({ error: 'unauthorized' });
  }
  next();
});

app.post('/getConnectionState', (_req, res) => {
  res.json({ response: ready ? 'CONNECTED' : 'UNLAUNCHED' });
});

app.post('/sendText', async (req, res) => {
  const { to, content } = (req.body && req.body.args) || {};
  if (!ready) return res.status(503).json({ error: 'not ready' });
  try {
    const sent = await client.sendMessage(to, content);
    ownSentIds.add(sent.id._serialized);
    res.json({ response: sent.id._serialized });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/sendImage', async (req, res) => {
  const { to, url, caption } = (req.body && req.body.args) || {};
  if (!ready) return res.status(503).json({ error: 'not ready' });
  try {
    const media = await fetchImageSafely(url); // SSRF-guarded fetch
    const sent = await client.sendMessage(to, media, { caption });
    ownSentIds.add(sent.id._serialized);
    res.json({ response: sent.id._serialized });
  } catch (e) {
    // 400 for rejected/unsafe URLs, 500 for genuine send failures.
    const code = /blocked|invalid|https|image|redirect/.test(e.message) ? 400 : 500;
    res.status(code).json({ error: e.message });
  }
});

app.listen(PORT, () => {
  console.log(`[sidecar] REST on http://localhost:${PORT} → webhook ${PLUGIN_WEBHOOK_URL}`);
});
