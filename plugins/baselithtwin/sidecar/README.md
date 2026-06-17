# BaselithTwin WhatsApp sidecar

A small **whatsapp-web.js** gateway process that replaces the abandoned
`@open-wa/wa-automate`. It speaks the same minimal REST the plugin's
`OpenWAGateway` already calls, so the Python side needs **no changes** — keep
`BASELITH_TWIN_GATEWAY=openwa` and point the base URL at this sidecar.

## Why

`@open-wa/wa-automate@4.76` no longer loads current WhatsApp Web (blank page,
`JSON.parse ... is not valid JSON` at `browser.js`). `whatsapp-web.js` is
actively maintained and uses the same QR-link flow.

## Run

```bash
cd plugins/baselithtwin/sidecar
npm install

PORT=8002 \
API_KEY="<same as BASELITH_TWIN_OPENWA_API_KEY>" \
SESSION=baselith-twin \
PLUGIN_WEBHOOK_URL="http://localhost:8000/api/baselithtwin/webhook" \
WEBHOOK_SECRET="<same as BASELITH_TWIN_WEBHOOK_SECRET>" \
HEADLESS=false \
npm start
```

First run prints a QR — scan it from WhatsApp → **Linked devices**. The session
persists under `.wwebjs_auth/`, so later runs reconnect without a QR (set
`HEADLESS=true`).

## Contract

| Plugin call (`OpenWAGateway`) | Sidecar behaviour |
|---|---|
| `POST /getConnectionState` | `{response: "CONNECTED"\|"UNLAUNCHED"}` |
| `POST /sendText {args:{to,content}}` | `client.sendMessage(to, content)` |
| `POST /sendImage {args:{to,url,caption}}` | media send from URL |
| inbound `message_create` | `POST {PLUGIN_WEBHOOK_URL}` with `X-Webhook-Secret` |

The sidecar tags messages it sends via the API and skips re-pushing them, so the
twin never re-ingests its own auto-sent replies as owner style.

> Node helper only — not part of the Python wheel.
