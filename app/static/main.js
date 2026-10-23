/**
 * Digital Doppelgänger — Frontend JS
 * Talks to FastAPI /api/* endpoints (or falls back to mock in SAMPLE_MODE).
 */

// ─── Config ──────────────────────────────────────────────────────────────────
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `http://${window.location.host}`
  : '';

// ─── State ───────────────────────────────────────────────────────────────────
let state = {
  runResult: null,
  activeTab: 'run',
};

// ─── DOM refs ─────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const tabs = {
  run:         { nav: $('nav-run'),         panel: $('tab-run') },
  findings:    { nav: $('nav-findings'),    panel: $('tab-findings') },
  trace:       { nav: $('nav-trace'),       panel: $('tab-trace') },
  remediation: { nav: $('nav-remediation'), panel: $('tab-remediation') },
  eval:        { nav: $('nav-eval'),        panel: $('tab-eval') },
};

// ─── Tab switching ────────────────────────────────────────────────────────────
function switchTab(tab) {
  state.activeTab = tab;
  for (const [key, { nav, panel }] of Object.entries(tabs)) {
    nav.classList.toggle('active', key === tab);
    panel.classList.toggle('active', key === tab);
  }
  // Load eval on demand
  if (tab === 'eval') loadEval();
  // Close mobile sidebar
  closeMobileSidebar();
}

for (const [key, { nav }] of Object.entries(tabs)) {
  nav.addEventListener('click', () => switchTab(key));
}

// ─── Mobile nav ───────────────────────────────────────────────────────────────
const sidebar   = document.querySelector('.sidebar');
const overlay   = $('sidebar-overlay');
const menuBtn   = $('mobile-menu-btn');

menuBtn.addEventListener('click', () => {
  sidebar.classList.add('open');
  overlay.classList.add('open');
});
overlay.addEventListener('click', closeMobileSidebar);

function closeMobileSidebar() {
  sidebar.classList.remove('open');
  overlay.classList.remove('open');
}

// ─── Consent gate for run button ──────────────────────────────────────────────
const consentCheck = $('consent-check');
const runBtn       = $('run-btn');

consentCheck.addEventListener('change', () => {
  runBtn.disabled = !consentCheck.checked;
});

// ─── Mode badge ───────────────────────────────────────────────────────────────
const modeBadge = $('mode-badge');
const modeText  = modeBadge.querySelector('.mode-text');

function setMode(mode) {
  modeBadge.dataset.mode = mode;
  modeText.textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
}

// ─── Run audit ────────────────────────────────────────────────────────────────
runBtn.addEventListener('click', runAudit);

async function runAudit() {
  const profileId   = $('profile-select').value;
  const sampleMode  = $('mode-sample').checked;

  if (!consentCheck.checked) return;

  // Disable button, set running state
  runBtn.disabled = true;
  setMode('running');
  showRunningStatus();

  try {
    const res = await fetch(`${API_BASE}/api/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: profileId, sample_mode: sampleMode, consent: true }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    state.runResult = data;

    setMode(data.mode || 'sample');
    showSuccessStatus(data);
    renderKPIs(data);
    renderFindings(data.findings);
    renderTrace(data.traces);
    renderRemediation(data.findings);

  } catch (err) {
    setMode('degraded');
    showErrorStatus(err.message);
  } finally {
    runBtn.disabled = !consentCheck.checked;
  }
}

// ─── Status helpers ───────────────────────────────────────────────────────────
const statusContent = $('status-content');

const AGENTS = [
  { key: 'planner',   label: 'Planner · source mapping' },
  { key: 'extractor', label: 'Extractor · fact harvest' },
  { key: 'linker',    label: 'Linker · entity linking' },
  { key: 'red_team',  label: 'Red-team · hypothesis generation' },
  { key: 'verifier',  label: 'Verifier · evidence audit' },
  { key: 'reporter',  label: 'Reporter · synthesis' },
];

let _agentTimer = null;

function showRunningStatus() {
  statusContent.className = 'status-running';
  let current = 0;

  function render() {
    statusContent.innerHTML = AGENTS.map((a, i) => {
      const cls = i < current ? 'done' : i === current ? 'active' : 'waiting';
      return `<div class="agent-step ${cls}">${a.label}</div>`;
    }).join('');
  }

  render();
  _agentTimer = setInterval(() => {
    if (current < AGENTS.length - 1) { current++; render(); }
    else clearInterval(_agentTimer);
  }, 950);
}

function showSuccessStatus(data) {
  clearInterval(_agentTimer);
  const score = data.exposure_summary?.exposure_score ?? '—';
  const tier  = data.exposure_summary?.exposure_tier ?? '—';
  statusContent.className = '';
  statusContent.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:8px;font-size:14px;">
      <p style="color:var(--positive);font-weight:500;">✓ Audit complete — Profile ${escHtml(data.profile_id)}</p>
      <p style="color:var(--ink-2);">Exposure: <strong>${score} / 100</strong> · ${tier}</p>
      <p style="color:var(--ink-3);font-size:12px;">Rounds: ${data.rounds_executed} · Loop iterations: ${data.loop_iterations}</p>
      <p style="color:var(--ink-3);font-size:12px;font-family:var(--mono);">${escHtml(data.trace_file)}</p>
    </div>`;
}

function showErrorStatus(msg) {
  clearInterval(_agentTimer);
  statusContent.className = '';
  statusContent.innerHTML = `
    <div style="color:var(--accent);font-size:14px;padding:8px 0;">
      <p style="font-weight:500;margin-bottom:6px;">✕ Run failed</p>
      <p style="font-size:13px;color:var(--ink-3);">${escHtml(msg)}</p>
    </div>`;
}

// ─── KPI strip ────────────────────────────────────────────────────────────────
function renderKPIs(data) {
  const ex   = data.exposure_summary || {};
  const lc   = ex.level_counts || {};
  const crit = (lc.CRITICAL || 0) + (lc.HIGH || 0);

  $('kpi-score').textContent    = `${ex.exposure_score ?? '—'} / 100`;
  $('kpi-tier').textContent     = ex.exposure_tier ?? '—';
  $('kpi-findings').textContent = data.findings?.length ?? '—';
  $('kpi-critical').textContent = crit;

  const tierCls = { CRITICAL: 'danger', HIGH: 'warn', MODERATE: '', LOW: '', MINIMAL: '' };
  $('kpi-tier').className = `kpi-value ${tierCls[ex.exposure_tier] || ''}`;

  $('kpi-strip').style.display = '';
}

// ─── Findings ─────────────────────────────────────────────────────────────────
const findingsList   = $('findings-list');
const findingsSub    = $('findings-sub');
const findingsActions = $('findings-header-actions');
const findingsFilter = $('findings-filter');

findingsFilter.addEventListener('change', () => {
  if (!state.runResult) return;
  renderFindings(state.runResult.findings);
});

function renderFindings(findings) {
  if (!findings || !findings.length) {
    findingsList.innerHTML = `<div class="empty-state"><p>No findings returned.</p></div>`;
    return;
  }

  findingsSub.textContent = `${findings.length} finding${findings.length !== 1 ? 's' : ''} sorted by severity.`;
  findingsActions.style.display = '';

  const filterVal = findingsFilter.value;
  const RISK_ORDER = ['CRITICAL', 'HIGH', 'MODERATE', 'LOW', 'INFORMATIONAL'];
  const sorted = [...findings].sort((a, b) =>
    RISK_ORDER.indexOf(a.risk_level.name) - RISK_ORDER.indexOf(b.risk_level.name)
  );
  const filtered = filterVal === 'all' ? sorted : sorted.filter(f => f.risk_level.name === filterVal);

  if (!filtered.length) {
    findingsList.innerHTML = `<div class="empty-state"><p>No findings at this level.</p></div>`;
    return;
  }

  findingsList.innerHTML = filtered.map((f, i) => renderFindingCard(f, i)).join('');

  // Wire up toggle & graph
  filtered.forEach((f, i) => {
    const card = document.querySelector(`[data-finding-id="${f.finding_id}"]`);
    if (!card) return;
    card.querySelector('.finding-header').addEventListener('click', () => {
      card.classList.toggle('open');
    });
    const graphBtn = card.querySelector('.graph-btn');
    if (graphBtn) graphBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      showEvidenceGraph(f);
    });
  });
}

function renderFindingCard(f, i) {
  const riskColors = {
    CRITICAL:     '#c1121f',
    HIGH:         '#d45c00',
    MODERATE:     '#7a4f00',
    LOW:          '#1a6e3d',
    INFORMATIONAL:'#3a6ea5',
  };
  const riskBar = riskColors[f.risk_level.name] || '#999';
  const verdictLabel = f.verdict.replace('_', ' ');
  const attackers = f.attacker_models.length
    ? f.attacker_models.map(a => `<span class="attacker-chip">${escHtml(a)}</span>`).join('')
    : '<span class="attacker-chip">none</span>';

  const chain = (f.evidence_chain || []).map((node, ni) => {
    const t = node._type || 'Entity';
    const abbr = t.slice(0, 2).toUpperCase();
    const val = node.value || node.claim || node.pattern || node.name || '';
    const src = node._source || '';
    return `
      <div class="evidence-node">
        <div class="evidence-dot">${abbr}</div>
        <div class="evidence-content">
          <div class="evidence-type">${escHtml(t)}</div>
          <div class="evidence-value">${escHtml(String(val).slice(0, 120))}</div>
          ${src ? `<div class="evidence-source">${escHtml(src)}</div>` : ''}
        </div>
      </div>`;
  }).join('');

  const hasGraph = f.evidence_chain && f.evidence_chain.length >= 2;

  return `
  <div class="finding-card" data-finding-id="${f.finding_id}">
    <div class="finding-header">
      <div class="finding-risk-bar" style="background:${riskBar}"></div>
      <div class="finding-main">
        <div class="finding-badges">
          <span class="badge badge-verdict-${f.verdict}">${escHtml(verdictLabel)}</span>
          <span class="badge badge-risk-${f.risk_level.name}">${f.risk_level.name} · L${f.risk_level.value}</span>
        </div>
        <div class="finding-claim">${escHtml(f.claim)}</div>
        <div class="finding-meta">
          <span class="finding-conf">Confidence: ${Math.round(f.confidence * 100)}%</span>
          <span>Category: ${escHtml(f.category)}</span>
        </div>
      </div>
      <div class="finding-chevron">
        <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
    </div>
    <div class="finding-body">
      <div class="finding-section-title">Evidence Chain</div>
      <div class="evidence-chain">${chain || '<p style="color:var(--ink-3);font-size:13px;">No evidence chain captured.</p>'}</div>
      ${hasGraph ? `
      <button class="graph-btn">
        <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="4" cy="4" r="2" stroke="currentColor" stroke-width="1.25"/>
          <circle cx="12" cy="8" r="2" stroke="currentColor" stroke-width="1.25"/>
          <circle cx="4" cy="12" r="2" stroke="currentColor" stroke-width="1.25"/>
          <line x1="6" y1="5" x2="10" y2="7" stroke="currentColor" stroke-width="1.25"/>
          <line x1="6" y1="11" x2="10" y2="9" stroke="currentColor" stroke-width="1.25"/>
        </svg>
        View Evidence Graph
      </button>` : ''}
      <div class="finding-section-title" style="margin-top:20px">Threat Models</div>
      <div class="attackers-list">${attackers}</div>
      <div class="finding-section-title" style="margin-top:16px">Remediation</div>
      <p style="font-size:13px;color:var(--ink-2);line-height:1.6;">${escHtml(f.remediation || 'No remediation generated.')}</p>
    </div>
  </div>`;
}

// ─── Loop trace ───────────────────────────────────────────────────────────────
const traceContainer = $('trace-container');

function renderTrace(traces) {
  if (!traces || !traces.length) {
    traceContainer.innerHTML = `<div class="empty-state"><p>No trace data returned.</p></div>`;
    return;
  }

  traceContainer.innerHTML = traces.map(t => renderTraceItem(t)).join('');
}

function renderTraceItem(t) {
  const agentClass = `agent-${(t.agent || '').replace('-', '_').toLowerCase()}`;
  const outcomeClass = `outcome-${(t.outcome || 'success').replace('_', '_')}`;

  const detailParts = [];
  if (t.details) {
    const d = t.details;
    if (d.sources?.length)           detailParts.push(`sources: ${d.sources.join(', ')}`);
    if (d.fact_count != null)        detailParts.push(`facts: ${d.fact_count}`);
    if (d.linked_entities_count != null) detailParts.push(`linked: ${d.linked_entities_count}`);
    if (d.inferences_proposed != null)   detailParts.push(`proposed: ${d.inferences_proposed}`);
    if (d.verdicts_count != null)        detailParts.push(`verdicts: ${d.verdicts_count}`);
    if (d.evidence_requests_count != null && d.evidence_requests_count > 0)
      detailParts.push(`evidence requests: ${d.evidence_requests_count}`);
    if (d.rejected_count != null && d.rejected_count > 0)
      detailParts.push(`rejected: ${d.rejected_count}`);
    if (d.rows_returned != null)     detailParts.push(`rows: ${d.rows_returned}`);
    if (d.findings_count != null)    detailParts.push(`findings: ${d.findings_count}`);
    if (d.round != null)             detailParts.push(`round ${d.round}`);
  }

  const msgMap = {
    plan:               'Planned data sources for extraction',
    extracted_facts:    'Extracted facts from all data sources',
    linked_entities:    'Linked entities across sources',
    candidate_inference:'Proposed adversarial inferences',
    verdict:            'Verifier evaluated inferences',
    evidence_query:     'Fetched evidence from data layer (Zetaris query)',
    final_report:       'Synthesised final findings and report',
  };
  const msg = msgMap[t.message_type] || t.message_type;

  return `
  <div class="trace-item">
    <span class="trace-step">${t.step}</span>
    <span class="trace-agent-badge ${agentClass}">${t.agent}</span>
    <div class="trace-content">
      <div class="trace-msg">${escHtml(msg)}</div>
      ${detailParts.length ? `<div class="trace-detail">${escHtml(detailParts.join(' · '))}</div>` : ''}
    </div>
    <span class="trace-outcome ${outcomeClass}">${(t.outcome || 'success').replace('_', ' ')}</span>
    <span class="trace-model">${escHtml(t.model || '')}</span>
  </div>`;
}

// ─── Remediation ──────────────────────────────────────────────────────────────
const remediationList   = $('remediation-list');
const exposureDeltaCard = $('exposure-delta-card');
const exposureBars      = $('exposure-bars');

function renderRemediation(findings) {
  if (!findings || !findings.length) {
    remediationList.innerHTML = `<div class="empty-state"><p>No findings to remediate.</p></div>`;
    return;
  }

  const data = state.runResult;
  const before = data.before_score ?? data.exposure_summary?.exposure_score ?? 0;
  const after  = data.after_score  ?? Math.max(0, before * 0.35);

  // Exposure bars
  exposureDeltaCard.style.display = '';
  exposureBars.innerHTML = `
    <div class="exposure-bar-row">
      <span class="exposure-bar-label" style="color:var(--accent)">Before</span>
      <div class="exposure-bar-track">
        <div class="exposure-bar-fill before" style="width:${before}%"></div>
      </div>
      <span class="exposure-bar-value" style="color:var(--accent)">${before} / 100</span>
    </div>
    <div class="exposure-bar-row">
      <span class="exposure-bar-label" style="color:var(--positive)">After</span>
      <div class="exposure-bar-track">
        <div class="exposure-bar-fill after" style="width:${after}%"></div>
      </div>
      <span class="exposure-bar-value" style="color:var(--positive)">${after} / 100</span>
    </div>
    <p style="font-size:12px;color:var(--ink-3);margin-top:6px;">
      Projected ${Math.round(100 - (after / before) * 100)}% exposure reduction if all remediations are applied.
    </p>`;

  // Remediation cards
  const actionable = findings.filter(f =>
    f.remediation_plan && f.remediation_plan.title !== 'No Action Required'
  );
  const advisory = findings.filter(f =>
    f.remediation_plan && f.remediation_plan.title === 'No Action Required'
  );
  const all = [...actionable, ...advisory];

  remediationList.innerHTML = all.map(f => {
    const rem = f.remediation_plan;
    if (!rem) return '';

    const p = rem.priority || '';
    const pClass = p.includes('Immediate') ? 'immediate' :
                   p.includes('Short')     ? 'short' :
                   p.includes('Best')      ? 'best' : 'advisory';

    const steps = (rem.steps || []).map(s => `<li>${escHtml(s)}</li>`).join('');

    return `
    <div class="remediation-card">
      <div class="remediation-header">
        <div>
          <div class="remediation-title">${escHtml(rem.title)}</div>
          <div style="font-size:12px;color:var(--ink-3);margin-top:3px;">Finding: ${escHtml(f.claim.slice(0, 80))}${f.claim.length > 80 ? '…' : ''}</div>
        </div>
        <span class="priority-badge priority-${pClass}">${escHtml(p)}</span>
      </div>
      <p class="remediation-impact">${escHtml(rem.impact || '')}</p>
      ${steps ? `<ul class="remediation-steps">${steps}</ul>` : ''}
    </div>`;
  }).join('');
}

// ─── Eval ─────────────────────────────────────────────────────────────────────
const evalContent = $('eval-content');
$('refresh-eval-btn').addEventListener('click', loadEval);

let _evalLoaded = false;

async function loadEval() {
  if (_evalLoaded && !state.activeTab === 'eval') return;
  evalContent.innerHTML = '<p class="loading-msg">Loading…</p>';
  try {
    const res = await fetch(`${API_BASE}/api/eval`);
    const data = await res.json();
    evalContent.innerHTML = markdownToHtml(data.markdown || 'No results yet.');
    _evalLoaded = true;
  } catch (e) {
    evalContent.innerHTML = `<p style="color:var(--ink-3)">Could not load eval results: ${escHtml(e.message)}</p>`;
  }
}

// ─── Minimal Markdown renderer ────────────────────────────────────────────────
function markdownToHtml(md) {
  // Tables (must come first before line-level processing)
  md = md.replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)+)/g, (_, header, body) => {
    const ths = header.split('|').filter(s => s.trim()).map(s =>
      `<th>${renderInline(s.trim())}</th>`).join('');
    const rows = body.trim().split('\n').map(row => {
      const tds = row.split('|').filter(s => s.trim()).map(s =>
        `<td>${renderInline(s.trim())}</td>`).join('');
      return `<tr>${tds}</tr>`;
    }).join('');
    return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
  });
  // Headings
  md = md.replace(/^### (.+)$/gm, (_, t) => `<h3>${renderInline(t)}</h3>`);
  md = md.replace(/^## (.+)$/gm,  (_, t) => `<h2>${renderInline(t)}</h2>`);
  md = md.replace(/^# (.+)$/gm,   (_, t) => `<h1>${renderInline(t)}</h1>`);
  // List items
  md = md.replace(/^- (.+)$/gm, (_, t) => `<li>${renderInline(t)}</li>`);
  md = md.replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`);
  // Paragraphs
  md = md.replace(/\n{2,}/g, '\n').split('\n').map(line => {
    line = line.trim();
    if (!line || line.startsWith('<')) return line;
    return `<p>${renderInline(line)}</p>`;
  }).join('\n');
  return md;
}

function renderInline(text) {
  // inline code first (before escaping other chars)
  text = text.replace(/`([^`]+)`/g, (_, code) =>
    `<code>${escHtml(code)}</code>`);
  // bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // italic
  text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
  return text;
}

// ─── Evidence graph (Canvas) ──────────────────────────────────────────────────
const graphModal      = $('graph-modal');
const graphModalTitle = $('graph-modal-title');
const graphModalClose = $('graph-modal-close');
const graphCanvas     = $('graph-canvas');

graphModalClose.addEventListener('click', () => { graphModal.style.display = 'none'; });
graphModal.addEventListener('click', e => { if (e.target === graphModal) graphModal.style.display = 'none'; });

function showEvidenceGraph(finding) {
  const chain = finding.evidence_chain || [];
  graphModalTitle.textContent = `Evidence Graph · ${finding.claim.slice(0, 60)}${finding.claim.length > 60 ? '…' : ''}`;
  graphModal.style.display = 'flex';
  drawGraph(graphCanvas, chain);
}

function drawGraph(canvas, nodes) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;
  ctx.clearRect(0, 0, W, H);

  if (!nodes || nodes.length === 0) {
    ctx.fillStyle = '#7a7f8e';
    ctx.font = '14px IBM Plex Sans, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('No evidence nodes', W / 2, H / 2);
    return;
  }

  const n = nodes.length;
  const cx = W / 2, cy = H / 2;
  const radius = Math.min(W, H) * 0.36;
  const nodeR  = 28;

  // Position nodes in a circle or line
  const positions = nodes.map((node, i) => {
    if (n === 1) return { x: cx, y: cy };
    if (n === 2) return { x: cx + (i === 0 ? -radius * 0.6 : radius * 0.6), y: cy };
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });

  // Node colors by type
  const typeColors = {
    Fact:        { fill: '#dbeafe', stroke: '#3a6ea5', text: '#1e3a5f' },
    Inference:   { fill: '#fce4e4', stroke: '#c1121f', text: '#7a0f0f' },
    Place:       { fill: '#d4edda', stroke: '#1a6e3d', text: '#0d3d20' },
    TimePattern: { fill: '#fef3cd', stroke: '#7a4f00', text: '#4a3000' },
    Evidence:    { fill: '#f3e8ff', stroke: '#7e22ce', text: '#3b0a6a' },
    default:     { fill: '#f2f3f5', stroke: '#b0b4be', text: '#3a3d45' },
  };

  // Draw edges first
  ctx.lineWidth = 1.5;
  for (let i = 0; i < positions.length - 1; i++) {
    const a = positions[i], b = positions[i + 1];
    ctx.strokeStyle = '#ced1d8';
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();

    // Arrow
    const angle = Math.atan2(b.y - a.y, b.x - a.x);
    const ax = b.x - nodeR * Math.cos(angle);
    const ay = b.y - nodeR * Math.sin(angle);
    ctx.fillStyle = '#ced1d8';
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - 10 * Math.cos(angle - 0.4), ay - 10 * Math.sin(angle - 0.4));
    ctx.lineTo(ax - 10 * Math.cos(angle + 0.4), ay - 10 * Math.sin(angle + 0.4));
    ctx.closePath();
    ctx.fill();
  }

  // Draw nodes
  nodes.forEach((node, i) => {
    const { x, y } = positions[i];
    const t = node._type || 'default';
    const c = typeColors[t] || typeColors.default;

    // Circle
    ctx.beginPath();
    ctx.arc(x, y, nodeR, 0, 2 * Math.PI);
    ctx.fillStyle = c.fill;
    ctx.fill();
    ctx.strokeStyle = c.stroke;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Type abbrev
    ctx.fillStyle = c.text;
    ctx.font = 'bold 10px IBM Plex Mono, monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(t.slice(0, 3).toUpperCase(), x, y - 6);

    // Value label
    const val = String(node.value || node.claim || node.name || '').slice(0, 14);
    ctx.font = '9px IBM Plex Sans, sans-serif';
    ctx.fillStyle = c.text;
    ctx.fillText(val, x, y + 6);

    // Source label below circle
    const src = String(node._source || '').slice(0, 16);
    if (src) {
      ctx.font = '9px IBM Plex Mono, monospace';
      ctx.fillStyle = '#b0b4be';
      ctx.fillText(src, x, y + nodeR + 12);
    }
  });
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
