const SCRIPT_ORIGIN = (() => {
  const currentScript = document.currentScript;
  if (currentScript && currentScript.src) {
    try {
      return new URL(currentScript.src).origin;
    } catch (err) {
      console.warn('[chatbot] Unable to parse currentScript src:', err);
    }
  }
  const scripts = document.getElementsByTagName('script');
  for (let i = scripts.length - 1; i >= 0; i -= 1) {
    const src = scripts[i]?.src;
    if (src && src.includes('chatbot.js')) {
      try {
        return new URL(src).origin;
      } catch (err) {
        console.warn('[chatbot] Unable to parse script src:', err);
      }
    }
  }
  return window.location.origin;
})();

const DEFAULT_API_BASE = SCRIPT_ORIGIN || window.location.origin;
const CONFIG_ENDPOINT = `${DEFAULT_API_BASE}/chatbot/config`;
let API_BASE = normalizeBase(DEFAULT_API_BASE);
let configPromise = null;
let feedbackChartObj = null;
let lineChartObj = null;
const DEFAULT_ANALYTICS_PARAMS = Object.freeze({
  days: 30,
  recent_limit: 20,
  top_limit: 10,
});
let analyticsParams = { ...DEFAULT_ANALYTICS_PARAMS };
const PERCENT_FORMATTER =
  typeof Intl !== 'undefined'
    ? new Intl.NumberFormat('it-IT', {
        maximumFractionDigits: 1,
        minimumFractionDigits: 0,
      })
    : null;
const DATETIME_FORMATTER =
  typeof Intl !== 'undefined'
    ? new Intl.DateTimeFormat('it-IT', {
        dateStyle: 'short',
        timeStyle: 'short',
      })
    : null;
const COLOR_VARIABLE_MAP = Object.freeze({
  CHATBOT_PRIMARY_COLOR: '--chatbot-primary-color',
  CHATBOT_PRIMARY_TEXT_COLOR: '--chatbot-primary-text-color',
  CHATBOT_WINDOW_BACKGROUND_COLOR: '--chatbot-window-background-color',
  CHATBOT_MESSAGES_BACKGROUND_COLOR: '--chatbot-messages-background-color',
  CHATBOT_BORDER_COLOR: '--chatbot-border-color',
  CHATBOT_USER_MESSAGE_BACKGROUND_COLOR: '--chatbot-user-message-background-color',
  CHATBOT_USER_MESSAGE_TEXT_COLOR: '--chatbot-user-message-text-color',
  CHATBOT_BOT_MESSAGE_BACKGROUND_COLOR: '--chatbot-bot-message-background-color',
  CHATBOT_BOT_MESSAGE_TEXT_COLOR: '--chatbot-bot-message-text-color',
  CHATBOT_TYPING_INDICATOR_COLOR: '--chatbot-typing-dot-color',
  CHATBOT_FEEDBACK_POSITIVE_COLOR: '--chatbot-feedback-positive-color',
  CHATBOT_FEEDBACK_NEGATIVE_COLOR: '--chatbot-feedback-negative-color',
});

let feedbackEnabled = true;
let conversationId = null;

function scrollQaBlockIntoView(container, block) {
  if (!container || !block) {
    return;
  }

  const top = Math.max(0, block.offsetTop - container.offsetTop);
  const desiredPosition = { top, behavior: 'smooth' };

  try {
    container.scrollTo(desiredPosition);
  } catch (err) {
    container.scrollTop = top;
  }
}

function applyColorOverrides(overrides) {
  if (!overrides || !Object.keys(overrides).length) {
    return;
  }

  const root = document.documentElement;
  Object.entries(overrides).forEach(([cssVar, rawValue]) => {
    if (!rawValue) {
      return;
    }
    const sanitized = rawValue.trim().replace(/^['"]|['"]$/g, '');
    if (!sanitized) {
      return;
    }
    root.style.setProperty(cssVar, sanitized);
  });
}

function parseBoolean(value, defaultValue) {
  if (value === undefined || value === null) {
    return defaultValue;
  }
  const normalized = String(value)
    .trim()
    .replace(/^['"]|['"]$/g, '')
    .toLowerCase();
  if (!normalized) {
    return defaultValue;
  }
  if (['true', '1', 'yes', 'on'].includes(normalized)) {
    return true;
  }
  if (['false', '0', 'no', 'off'].includes(normalized)) {
    return false;
  }
  return defaultValue;
}

function formatPercentage(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0%';
  }
  const normalized = Math.max(0, Math.min(1, value));
  const percent = normalized * 100;
  if (PERCENT_FORMATTER) {
    return `${PERCENT_FORMATTER.format(percent)}%`;
  }
  const precision = percent >= 10 ? 0 : 1;
  return `${percent.toFixed(precision)}%`;
}

function formatDateTime(value) {
  if (!value) {
    return '—';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  if (DATETIME_FORMATTER) {
    return DATETIME_FORMATTER.format(parsed);
  }
  return parsed.toISOString();
}

function summarizeSources(sources) {
  if (!Array.isArray(sources) || !sources.length) {
    return { text: '—', tooltip: 'Nessuna fonte associata' };
  }
  const labels = sources
    .map((src) => {
      if (src && typeof src === 'object') {
        return src.title || src.path || src.url || src.document_id;
      }
      return null;
    })
    .filter((label) => typeof label === 'string' && label.trim().length);

  if (!labels.length) {
    return { text: '—', tooltip: 'Nessuna fonte disponibile' };
  }
  if (labels.length === 1) {
    return { text: labels[0], tooltip: labels[0] };
  }
  const [first, ...rest] = labels;
  return {
    text: `${first} (+${rest.length})`,
    tooltip: labels.join('\n'),
  };
}

function formatFeedbackLabel(value) {
  if (value === 'positive') {
    return 'Positivo';
  }
  if (value === 'negative') {
    return 'Negativo';
  }
  return value || '—';
}

function updateWindowLabels(windowInfo) {
  let label = 'Storico completo';
  if (windowInfo && typeof windowInfo.days === 'number' && windowInfo.days > 0) {
    if (windowInfo.days === 1) {
      label = 'Ultimo giorno';
    } else {
      label = `Ultimi ${windowInfo.days} giorni`;
    }
  }
  document.querySelectorAll('[data-window-label]').forEach((el) => {
    el.textContent = label;
  });
}

function normalizeBase(url) {
  if (!url) {
    return DEFAULT_API_BASE;
  }
  return url.trim().replace(/\/+$/, '');
}

function generateConversationId() {
  if (window.crypto && typeof window.crypto.randomUUID === 'function') {
    return window.crypto.randomUUID();
  }
  const randomPart = Math.random().toString(16).slice(2);
  return `conv-${Date.now()}-${randomPart}`;
}

function ensureConversationId() {
  if (!conversationId) {
    conversationId = generateConversationId();
  }
  return conversationId;
}

function resetConversationId() {
  conversationId = null;
}

async function writeTextToClipboard(text) {
  if (typeof text !== 'string' || !text.length) {
    return false;
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      console.warn('[chatbot] navigator.clipboard.writeText failed:', err);
    }
  }

  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.setAttribute('readonly', '');
  textArea.style.position = 'fixed';
  textArea.style.top = '-9999px';
  textArea.style.opacity = '0';
  document.body.appendChild(textArea);

  textArea.select();
  textArea.setSelectionRange(0, textArea.value.length);

  let succeeded = false;
  try {
    succeeded = document.execCommand('copy');
  } catch (err) {
    console.warn('[chatbot] document.execCommand copy failed:', err);
  }

  document.body.removeChild(textArea);
  return succeeded;
}

function enhanceCodeBlocks(container) {
  if (!container) {
    return;
  }

  const codeBlocks = container.querySelectorAll('pre code');
  if (!codeBlocks.length) {
    return;
  }

  codeBlocks.forEach((codeEl) => {
    const pre = codeEl.parentElement;
    if (!pre || pre.dataset.copyEnhanced === 'true') {
      return;
    }

    const parent = pre.parentNode;
    if (!parent) {
      return;
    }

    pre.dataset.copyEnhanced = 'true';

    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';
    parent.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const actions = document.createElement('div');
    actions.className = 'code-block-actions';
    wrapper.appendChild(actions);

    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'copy-code-btn';
    copyBtn.setAttribute('aria-label', 'Copia il codice');
    copyBtn.title = 'Copia il codice';

    const icon = document.createElement('span');
    icon.className = 'material-symbols-outlined';
    icon.textContent = 'content_copy';

    copyBtn.appendChild(icon);
    actions.appendChild(copyBtn);

    const srStatus = document.createElement('span');
    srStatus.className = 'sr-only copy-feedback';
    srStatus.setAttribute('aria-live', 'polite');
    actions.appendChild(srStatus);

    const resetState = () => {
      copyBtn.dataset.state = 'idle';
      icon.textContent = 'content_copy';
      copyBtn.classList.remove('copied', 'copy-error');
      copyBtn.title = 'Copia il codice';
      copyBtn.setAttribute('aria-label', 'Copia il codice');
      srStatus.textContent = '';
      copyBtn.disabled = false;
    };

    resetState();

    copyBtn.addEventListener('click', async () => {
      const text = codeEl.textContent || '';
      if (!text.trim()) {
        return;
      }

      copyBtn.dataset.state = 'copying';
      copyBtn.disabled = true;

      let success = false;
      try {
        success = await writeTextToClipboard(text);
      } catch (err) {
        success = false;
      }

      if (success) {
        copyBtn.dataset.state = 'copied';
        icon.textContent = 'check';
        copyBtn.classList.add('copied');
        copyBtn.title = 'Copiato!';
        copyBtn.setAttribute('aria-label', 'Codice copiato');
        srStatus.textContent = 'Codice copiato negli appunti';
      } else {
        copyBtn.dataset.state = 'error';
        icon.textContent = 'error';
        copyBtn.classList.add('copy-error');
        copyBtn.title = 'Copia non riuscita';
        copyBtn.setAttribute('aria-label', 'Copia non riuscita');
        srStatus.textContent = 'Copia non riuscita';
      }

      window.setTimeout(() => {
        resetState();
      }, 1800);
    });
  });
}

async function loadChatbotConfig() {
  try {
    const res = await fetch(CONFIG_ENDPOINT, { cache: 'no-store' });
    if (res.ok) {
      const data = await res.json();

      const overrides = {};
      if (data && typeof data === 'object') {
        if (Object.prototype.hasOwnProperty.call(data, 'api_url')) {
          const apiUrl = data.api_url;
          if (apiUrl) {
            API_BASE = normalizeBase(String(apiUrl));
          } else {
            API_BASE = normalizeBase(DEFAULT_API_BASE);
          }
        }

        if (Object.prototype.hasOwnProperty.call(data, 'feedback_enabled')) {
          feedbackEnabled = parseBoolean(data.feedback_enabled, true);
        }

        const rawOverrides = data.color_overrides;
        if (rawOverrides && typeof rawOverrides === 'object') {
          Object.entries(rawOverrides).forEach(([key, value]) => {
            if (!value) {
              return;
            }
            const cssVar = COLOR_VARIABLE_MAP[key];
            if (!cssVar) {
              return;
            }
            overrides[cssVar] = String(value);
          });
        }
      }

      applyColorOverrides(overrides);
      return API_BASE;
    }
  } catch (err) {
    console.error('[chatbot] Failed to load chatbot config:', err);
  }

  API_BASE = normalizeBase(DEFAULT_API_BASE);
  return API_BASE;
}

async function ensureConfigLoaded() {
  if (!configPromise) {
    configPromise = loadChatbotConfig();
  }
  return configPromise;
}

async function initChatbot() {
  await ensureConfigLoaded();

  if (document.getElementById('chatbot-btn')) {
    return;
  }

  const btn = document.createElement('div');
  btn.id = 'chatbot-btn';
  btn.innerHTML = `<span class="material-symbols-outlined">robot_2</span>`;
  document.body.appendChild(btn);

  const overlay = document.createElement('div');
  overlay.id = 'chatbot-overlay';
  document.body.appendChild(overlay);

  const chatWindow = document.createElement('div');
  chatWindow.id = 'chatbot-window';
  chatWindow.innerHTML = `
    <div id="chatbot-header">
      <span>agent-jira</span>
      <div class="chat-actions">
        <button id="clear-chat" title="Svuota chat">
          <span class="material-symbols-outlined">delete</span>
        </button>
        <button id="close-chat" title="Chiudi">
          <span class="material-symbols-outlined">close</span>
        </button>
      </div>
    </div>
    <div id="chatbot-messages"></div>
    <input id="chatbot-input" placeholder="Scrivi e premi Invio..." />
  `;
  document.body.appendChild(chatWindow);

  btn.onclick = () => {
    chatWindow.classList.add('open');
    overlay.classList.add('show');

    if (input) {
      input.focus();
    }

    const msgBox = document.getElementById('chatbot-messages');
    if (msgBox.children.length === 0) {
      const welcome = document.createElement('div');
      welcome.classList.add('msg-row', 'bot-row', 'welcome-msg');
      welcome.innerHTML = `
        <div class="avatar bot-avatar">🤖</div>
        <div class="bot-msg bot-welcome">
          👋 Benvenuto! Sono l’assistente della documentazione locale.<br>
          Scrivi la tua domanda o esplora i documenti disponibili 📚
        </div>
      `;
      msgBox.appendChild(welcome);
      welcome.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const closeChat = () => {
    chatWindow.classList.remove('open');
    overlay.classList.remove('show');
  };
  document.getElementById('close-chat').onclick = closeChat;
  overlay.onclick = closeChat;

  document.getElementById('clear-chat').onclick = () => {
    resetConversationId();
    document.getElementById('chatbot-messages').innerHTML = '';
  };

  const input = document.getElementById('chatbot-input');
  let sending = false;

  input.addEventListener('keypress', async (e) => {
    if (e.key === 'Enter' && input.value.trim() !== '' && !sending) {
      sending = true;
      const msgBox = document.getElementById('chatbot-messages');

      const qaWrapper = document.createElement('div');
      qaWrapper.classList.add('qa-block');

      qaWrapper.innerHTML = `
        <div class="msg-row user-row">
          <div class="user-msg">${input.value}</div>
          <div class="avatar user-avatar">👤</div>
        </div>
      `;
      const q = input.value;
      input.value = '';

      const typingId = 'typing-' + Date.now();
      qaWrapper.innerHTML += `
        <div class="msg-row bot-row">
          <div class="avatar bot-avatar">🤖</div>
          <div class="bot-msg" id="${typingId}">
            <span class="typing-loader">
              <span></span><span></span><span></span>
            </span>
          </div>
        </div>`;
      msgBox.appendChild(qaWrapper);
      scrollQaBlockIntoView(msgBox, qaWrapper);

      const chatEndpoint = `${API_BASE}/chat`;
      const activeConversationId = ensureConversationId();

      try {
        const res = await fetch(chatEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, conversation_id: activeConversationId }),
        });

        if (!res.ok) throw new Error('HTTP ' + res.status);

        const data = await res.json();
        const rawAnswer = (data.answer || '').trim();
        const sources = Array.isArray(data.sources) ? data.sources : [];
        const newMsg = document.getElementById(typingId);

        if (rawAnswer.startsWith('<') && rawAnswer.endsWith('>')) {
          newMsg.innerHTML = rawAnswer;
        } else if (window.marked) {
          newMsg.innerHTML = window.marked.parse(rawAnswer);
        } else {
          newMsg.textContent = rawAnswer;
        }

        enhanceCodeBlocks(newMsg);

        if (feedbackEnabled) {
          const feedbackRow = document.createElement('div');
          feedbackRow.classList.add('feedback-row');

          const positiveBtn = document.createElement('button');
          positiveBtn.innerHTML = `
            <span class="material-symbols-outlined" style="font-size:18px;">thumb_up</span>`;
          positiveBtn.dataset.feedback = 'positive';

          const negativeBtn = document.createElement('button');
          negativeBtn.innerHTML = `
            <span class="material-symbols-outlined" style="font-size:18px; vertical-align:middle;">
              thumb_down
            </span>
          `;
          negativeBtn.dataset.feedback = 'negative';

          feedbackRow.appendChild(positiveBtn);
          feedbackRow.appendChild(negativeBtn);
          qaWrapper.appendChild(feedbackRow);

          const feedbackEndpoint = `${API_BASE}/feedback`;

          [positiveBtn, negativeBtn].forEach((fb) => {
            fb.addEventListener('click', async () => {
              try {
                const payload = {
                  query: q,
                  answer: rawAnswer,
                  feedback: fb.dataset.feedback,
                  conversation_id: activeConversationId,
                  sources,
                };
                if (fb.dataset.feedback === 'negative') {
                  const commentInput = window.prompt(
                    'Puoi indicare il motivo del feedback negativo? (facoltativo, max 500 caratteri)'
                  );
                  if (typeof commentInput === 'string') {
                    const trimmed = commentInput.trim();
                    if (trimmed.length) {
                      payload.comment = trimmed;
                    }
                  }
                }

                const feedbackRes = await fetch(feedbackEndpoint, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload),
                });

                if (feedbackRes.ok) {
                  [positiveBtn, negativeBtn].forEach((b) => {
                    b.disabled = true;
                    b.style.opacity = '0.5';
                  });

                  fb.classList.add('given');

                  const confirm = document.createElement('span');
                  confirm.className = 'feedback-confirm';
                  confirm.textContent = ' Feedback inviato ✅';
                  feedbackRow.appendChild(confirm);
                }
              } catch (err) {
                console.error('Errore invio feedback:', err);
              }
            });
          });
        }

        scrollQaBlockIntoView(msgBox, qaWrapper);
      } catch (err) {
        document.getElementById(typingId).innerText = '❌ Errore: ' + err.message;
        scrollQaBlockIntoView(msgBox, qaWrapper);
      } finally {
        sending = false;
      }
    }
  });
}

async function loadData(overrides = {}) {
  await ensureConfigLoaded();

  analyticsParams = { ...analyticsParams, ...overrides };

  const searchParams = new URLSearchParams();
  if (analyticsParams.days !== null && analyticsParams.days !== undefined) {
    searchParams.set('days', analyticsParams.days);
  }
  if (analyticsParams.recent_limit !== null && analyticsParams.recent_limit !== undefined) {
    searchParams.set('recent_limit', analyticsParams.recent_limit);
  }
  if (analyticsParams.top_limit !== null && analyticsParams.top_limit !== undefined) {
    searchParams.set('top_limit', analyticsParams.top_limit);
  }

  const queryString = searchParams.toString();
  const url =
    queryString.length > 0 ? `${API_BASE}/admin/data?${queryString}` : `${API_BASE}/admin/data`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();

    updateWindowLabels(data.window || null);

    const totalEl = document.getElementById('total');
    if (totalEl) totalEl.textContent = data.total_feedbacks ?? 0;

    const positiveEl = document.getElementById('positives');
    if (positiveEl) positiveEl.textContent = data.positives ?? 0;

    const negativeEl = document.getElementById('negatives');
    if (negativeEl) negativeEl.textContent = data.negatives ?? 0;

    const positiveRateEl = document.getElementById('positiveRate');
    if (positiveRateEl) positiveRateEl.textContent = formatPercentage(data.positive_rate);

    const timeRangeSelect = document.getElementById('timeRangeSelect');
    if (timeRangeSelect) {
      const value =
        analyticsParams.days === null || analyticsParams.days === undefined
          ? 'all'
          : String(analyticsParams.days);
      if (timeRangeSelect.value !== value) {
        timeRangeSelect.value = value;
      }
    }

    const donutCtx = document.getElementById('feedbackChart');
    if (donutCtx && window.Chart) {
      if (feedbackChartObj) feedbackChartObj.destroy();
      feedbackChartObj = new window.Chart(donutCtx, {
        type: 'doughnut',
        data: {
          labels: ['Positivi', 'Negativi'],
          datasets: [
            {
              data: [data.positives || 0, data.negatives || 0],
              backgroundColor: ['#10b981', '#ef4444'],
            },
          ],
        },
        options: {
          responsive: true,
          plugins: { legend: { position: 'bottom' } },
        },
      });
    }

    const recentItems = Array.isArray(data.recent) ? data.recent : [];
    const tbody = document.getElementById('feedbackTable');
    if (tbody) {
      tbody.innerHTML = '';
      if (!recentItems.length) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 6;
        emptyCell.textContent = 'Nessun feedback registrato nel periodo selezionato.';
        emptyRow.appendChild(emptyCell);
        tbody.appendChild(emptyRow);
      } else {
        recentItems.forEach((item) => {
          const tr = document.createElement('tr');

          const idCell = document.createElement('td');
          idCell.textContent = item.id ?? '—';
          tr.appendChild(idCell);

          const queryCell = document.createElement('td');
          queryCell.textContent = item.query || '—';
          tr.appendChild(queryCell);

          const answerCell = document.createElement('td');
          const rawAnswer = typeof item.answer === 'string' ? item.answer : '';
          const trimmedAnswer = rawAnswer.length > 120 ? `${rawAnswer.slice(0, 120)}…` : rawAnswer;
          const answerSpan = document.createElement('span');
          answerSpan.textContent = trimmedAnswer || '—';
          answerCell.appendChild(answerSpan);
          if (rawAnswer) {
            const answerBtn = document.createElement('button');
            answerBtn.type = 'button';
            answerBtn.className = 'btn small-btn';
            answerBtn.title = 'Mostra risposta completa';
            answerBtn.textContent = '📄';
            answerBtn.addEventListener('click', () => openModal(rawAnswer));
            answerCell.appendChild(answerBtn);
          }
          tr.appendChild(answerCell);

          const feedbackCell = document.createElement('td');
          feedbackCell.textContent = formatFeedbackLabel(item.feedback);
          feedbackCell.classList.add('badge');
          if (item.feedback === 'positive') {
            feedbackCell.classList.add('badge-positive');
          } else if (item.feedback === 'negative') {
            feedbackCell.classList.add('badge-negative');
          }
          tr.appendChild(feedbackCell);

          const sourcesCell = document.createElement('td');
          const summary = summarizeSources(item.sources);
          sourcesCell.textContent = summary.text;
          if (summary.tooltip) {
            sourcesCell.title = summary.tooltip;
          }
          tr.appendChild(sourcesCell);

          const timestampCell = document.createElement('td');
          timestampCell.textContent = formatDateTime(item.timestamp);
          if (item.timestamp) {
            timestampCell.title = item.timestamp;
          }
          tr.appendChild(timestampCell);

          tbody.appendChild(tr);
        });
      }
    }

    const timeseries = Array.isArray(data.timeseries) ? data.timeseries : [];
    const labels = timeseries.map((row) => row.date);
    const positivesSeries = timeseries.map((row) => row.positives || 0);
    const negativesSeries = timeseries.map((row) => row.negatives || 0);

    const lineCtx = document.getElementById('lineChart');
    if (lineCtx && window.Chart) {
      if (lineChartObj) lineChartObj.destroy();
      lineChartObj = new window.Chart(lineCtx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'Positivi',
              data: positivesSeries,
              borderColor: '#10b981',
              backgroundColor: 'rgba(16, 185, 129, 0.2)',
              tension: 0.3,
              fill: false,
              pointRadius: 3,
            },
            {
              label: 'Negativi',
              data: negativesSeries,
              borderColor: '#ef4444',
              backgroundColor: 'rgba(239, 68, 68, 0.2)',
              tension: 0.3,
              fill: false,
              pointRadius: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { title: { display: true, text: 'Data' } },
            y: {
              title: { display: true, text: 'Numero di feedback' },
              beginAtZero: true,
              ticks: { precision: 0 },
            },
          },
        },
      });
    }

    const topQueries = Array.isArray(data.top_queries) ? data.top_queries : [];
    const queriesBody = document.getElementById('topQueriesBody');
    if (queriesBody) {
      queriesBody.innerHTML = '';
      if (!topQueries.length) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 6;
        emptyCell.textContent = 'Nessuna query disponibile per il periodo selezionato.';
        emptyRow.appendChild(emptyCell);
        queriesBody.appendChild(emptyRow);
      } else {
        topQueries.forEach((item) => {
          const tr = document.createElement('tr');

          const queryCell = document.createElement('td');
          queryCell.textContent = item.query || '—';
          tr.appendChild(queryCell);

          const totalCell = document.createElement('td');
          totalCell.textContent = (item.total ?? 0).toString();
          tr.appendChild(totalCell);

          const positiveCell = document.createElement('td');
          positiveCell.textContent = (item.positives ?? 0).toString();
          tr.appendChild(positiveCell);

          const negativeCell = document.createElement('td');
          negativeCell.textContent = (item.negatives ?? 0).toString();
          tr.appendChild(negativeCell);

          const rateCell = document.createElement('td');
          rateCell.textContent = formatPercentage(item.positive_rate);
          tr.appendChild(rateCell);

          const lastCell = document.createElement('td');
          lastCell.textContent = formatDateTime(item.last_timestamp);
          if (item.last_timestamp) {
            lastCell.title = item.last_timestamp;
          }
          tr.appendChild(lastCell);

          queriesBody.appendChild(tr);
        });
      }
    }

    const topDocuments = Array.isArray(data.top_documents) ? data.top_documents : [];
    const docsBody = document.getElementById('topDocsBody');
    if (docsBody) {
      docsBody.innerHTML = '';
      if (!topDocuments.length) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 6;
        emptyCell.textContent = 'Nessuna fonte disponibile per il periodo selezionato.';
        emptyRow.appendChild(emptyCell);
        docsBody.appendChild(emptyRow);
      } else {
        topDocuments.forEach((doc) => {
          const tr = document.createElement('tr');

          const labelCell = document.createElement('td');
          if (doc.url) {
            const link = document.createElement('a');
            link.href = doc.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = doc.title || doc.url;
            labelCell.appendChild(link);
          } else if (doc.path) {
            const code = document.createElement('code');
            code.textContent = doc.path;
            labelCell.appendChild(code);
          } else {
            labelCell.textContent = doc.title || doc.document_id || '—';
          }
          tr.appendChild(labelCell);

          const originCell = document.createElement('td');
          originCell.textContent = doc.origin || doc.source_type || '—';
          tr.appendChild(originCell);

          const totalCell = document.createElement('td');
          totalCell.textContent = (doc.total ?? 0).toString();
          tr.appendChild(totalCell);

          const positivesCell = document.createElement('td');
          positivesCell.textContent = (doc.positives ?? 0).toString();
          tr.appendChild(positivesCell);

          const negativesCell = document.createElement('td');
          negativesCell.textContent = (doc.negatives ?? 0).toString();
          tr.appendChild(negativesCell);

          const rateCell = document.createElement('td');
          rateCell.textContent = formatPercentage(doc.positive_rate);
          tr.appendChild(rateCell);

          docsBody.appendChild(tr);
        });
      }
    }

    const learningItems = Array.isArray(data.learning_candidates) ? data.learning_candidates : [];
    const learningBody = document.getElementById('learningBody');
    if (learningBody) {
      learningBody.innerHTML = '';
      if (!learningItems.length) {
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.colSpan = 6;
        emptyCell.textContent = 'Nessuna query richiede attenzione nel periodo selezionato.';
        emptyRow.appendChild(emptyCell);
        learningBody.appendChild(emptyRow);
      } else {
        learningItems.forEach((item) => {
          const tr = document.createElement('tr');

          const queryCell = document.createElement('td');
          queryCell.textContent = item.query || '—';
          tr.appendChild(queryCell);

          const totalCell = document.createElement('td');
          totalCell.textContent = (item.total ?? 0).toString();
          tr.appendChild(totalCell);

          const positiveCell = document.createElement('td');
          positiveCell.textContent = (item.positives ?? 0).toString();
          tr.appendChild(positiveCell);

          const negativeCell = document.createElement('td');
          negativeCell.textContent = (item.negatives ?? 0).toString();
          tr.appendChild(negativeCell);

          const rateCell = document.createElement('td');
          rateCell.textContent = formatPercentage(item.positive_rate);
          tr.appendChild(rateCell);

          const lastCell = document.createElement('td');
          lastCell.textContent = formatDateTime(item.last_timestamp);
          if (item.last_timestamp) {
            lastCell.title = item.last_timestamp;
          }
          tr.appendChild(lastCell);

          learningBody.appendChild(tr);
        });
      }
    }
  } catch (err) {
    console.error('[chatbot] Failed to load admin data:', err);
  }
}

async function reindexDocs() {
  await ensureConfigLoaded();

  try {
    const res = await fetch(`${API_BASE}/reindex`, { method: 'POST' });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();
    alert('Reindicizzazione completata ✅ Nuovi documenti: ' + data.new_files_indexed);
  } catch (err) {
    console.error('[chatbot] Failed to reindex docs:', err);
    alert('❌ Reindicizzazione fallita: ' + err.message);
    return;
  }

  loadData();
}

function openModal(text) {
  document.getElementById('modalText').textContent = text;
  document.getElementById('modal').style.display = 'block';
}

function closeModal() {
  document.getElementById('modal').style.display = 'none';
}

window.onclick = function (event) {
  const modal = document.getElementById('modal');
  if (event.target === modal) closeModal();
};

function switchTab(evt) {
  const tabButtons = document.querySelectorAll('.tab-button');
  tabButtons.forEach((btn) => btn.classList.remove('active'));
  evt.currentTarget.classList.add('active');

  const contents = document.querySelectorAll('.tab-content');
  contents.forEach((c) => (c.style.display = 'none'));

  const tabId = evt.currentTarget.getAttribute('data-tab');
  document.getElementById(tabId).style.display = 'block';

  if (tabId === 'analyticsTab' && !lineChartObj) {
    loadData();
  }
}

function toggleDarkMode() {
  document.body.classList.toggle('dark-mode');
  const btn = document.querySelector('.btn-toggle-mode');
  if (btn) {
    btn.textContent = document.body.classList.contains('dark-mode') ? '☀️' : '🌙';
  }
}

function setupAnalyticsFilters() {
  const select = document.getElementById('timeRangeSelect');
  if (!select) {
    return;
  }
  select.addEventListener('change', (event) => {
    const value = event.target.value;
    if (value === 'all') {
      loadData({ days: null });
      return;
    }
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed) && parsed > 0) {
      loadData({ days: parsed });
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setupAnalyticsFilters();
    initChatbot().catch((err) => console.error('[chatbot] Initialization failed', err));
  });
} else {
  setupAnalyticsFilters();
  initChatbot().catch((err) => console.error('[chatbot] Initialization failed', err));
}

window.loadData = loadData;
window.reindexDocs = reindexDocs;
window.openModal = openModal;
window.closeModal = closeModal;
window.switchTab = switchTab;
window.toggleDarkMode = toggleDarkMode;
