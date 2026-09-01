/* ═══════════════════════════════════════════
   STATE
═══════════════════════════════════════════ */
const API = 'http://localhost:5000/api';
let ALL = [], FILTERED = [], sortCol = 'price', sortDir = 'asc', page = 1;
const PAGE = 25;
let pollTimer = null;

/* ═══════════════════════════════════════════
   BOOT
═══════════════════════════════════════════ */
async function boot() {
  document.getElementById('hdr-date').textContent =
    new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  await loadData();
  bindEvents();
  animateIn();
}

/* ═══════════════════════════════════════════
   LOAD DATA
═══════════════════════════════════════════ */
async function loadData() {
  try {
    const res = await fetch(`${API}/data`);
    if (!res.ok) throw new Error('Server error');
    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) { showNoData(); return; }
    ALL = data;
    populateGenreFilter();
    applyFilters();
    buildStats();
    buildCharts();
  } catch {
    showNoData();
  }
}

function showNoData() {
  document.getElementById('tbody').innerHTML = `
    <tr class="no-data-row"><td colspan="9">
      <div class="no-data-msg">No data yet.</div>
      <div class="no-data-hint">Use the <strong>Scrape Controls</strong> panel above to collect Steam games data.</div>
    </td></tr>`;
  document.getElementById('f-count').textContent = '0';
  ['s-total', 's-price', 's-free'].forEach(id => document.getElementById(id).textContent = '0');
  document.getElementById('s-genre').textContent = '—';
}

/* ═══════════════════════════════════════════
   STATS
═══════════════════════════════════════════ */
function buildStats() {
  document.getElementById('s-total').textContent = ALL.length.toLocaleString();
  const paid = ALL.filter(g => g.price > 0);
  const avg = paid.length ? paid.reduce((s, g) => s + g.price, 0) / paid.length : 0;
  document.getElementById('s-price').textContent = '$' + avg.toFixed(2);
  const gc = {};
  ALL.forEach(g => gc[g.genre] = (gc[g.genre] || 0) + 1);
  const top = Object.entries(gc).sort((a, b) => b[1] - a[1])[0];
  document.getElementById('s-genre').textContent = top ? top[0] : '—';
  document.getElementById('s-free').textContent = ALL.filter(g => g.price === 0).length.toLocaleString();
}

/* ═══════════════════════════════════════════
   FILTERS
═══════════════════════════════════════════ */
function populateGenreFilter() {
  const sel = document.getElementById('f-genre');
  sel.innerHTML = '<option value="">All Genres</option>';
  [...new Set(ALL.map(g => g.genre).filter(Boolean))].sort().forEach(g => {
    const o = document.createElement('option');
    o.value = g; o.textContent = g; sel.appendChild(o);
  });
}

function applyFilters() {
  const q  = document.getElementById('f-q').value.toLowerCase();
  const g  = document.getElementById('f-genre').value;
  const rt = document.getElementById('f-rating').value;
  const px = document.getElementById('f-price').value;

  FILTERED = ALL.filter(d => {
    if (q  && !`${d.title||''} ${d.developer||''} ${d.tags||''}`.toLowerCase().includes(q)) return false;
    if (g  && d.genre !== g) return false;
    if (rt === 'pos'   && !/positive/i.test(d.rating)) return false;
    if (rt === 'mixed' && !/mixed/i.test(d.rating))    return false;
    if (rt === 'neg'   && !/negative/i.test(d.rating)) return false;
    if (px === 'free'  && d.price !== 0) return false;
    if (px === 'u10'   && (d.price === 0 || d.price >= 10)) return false;
    if (px === 'u20'   && (d.price === 0 || d.price >= 20)) return false;
    if (px === 'o20'   && d.price < 20) return false;
    return true;
  });

  doSort(); page = 1;
  renderTable(); renderPages();
  document.getElementById('f-count').textContent = FILTERED.length.toLocaleString();
}

/* ═══════════════════════════════════════════
   SORT
═══════════════════════════════════════════ */
function doSort() {
  FILTERED.sort((a, b) => {
    let va = a[sortCol] ?? '', vb = b[sortCol] ?? '';
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    return va < vb ? (sortDir === 'asc' ? -1 : 1) : va > vb ? (sortDir === 'asc' ? 1 : -1) : 0;
  });
}

/* ═══════════════════════════════════════════
   TABLE
═══════════════════════════════════════════ */
function renderTable() {
  const tbody = document.getElementById('tbody');
  const slice = FILTERED.slice((page - 1) * PAGE, page * PAGE);

  if (!slice.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="9">No games match your filters.</td></tr>';
    return;
  }

  tbody.innerHTML = slice.map(d => {
    const priceH = d.price === 0
      ? '<span class="price-v free">FREE</span>'
      : `<span class="price-v paid">$${Number(d.price).toFixed(2)}</span>`;

    const discH = d.discount > 0
      ? `<span class="disc">-${d.discount}%</span>`
      : '<span style="color:var(--text-3)">—</span>';

    const ratingCls = /positive/i.test(d.rating) ? 'bg'
      : /mixed/i.test(d.rating) ? 'by'
      : /negative/i.test(d.rating) ? 'br' : 'bx';

    const revH = d.review_count > 0
      ? `<span class="rev">${Number(d.review_count).toLocaleString()}</span>`
      : '<span style="color:var(--text-3)">—</span>';

    const url = d.app_id ? `https://store.steampowered.com/app/${d.app_id}/` : '#';

    return `<tr>
      <td class="td-title"><a href="${url}" target="_blank" rel="noopener" title="${esc(d.title)}">${esc(d.title)}</a></td>
      <td><span class="badge bp">${esc(d.genre || '—')}</span></td>
      <td>${priceH}</td>
      <td>${discH}</td>
      <td><span class="badge ${ratingCls}">${esc(d.rating || 'N/A')}</span></td>
      <td>${revH}</td>
      <td style="color:var(--text-2);max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(d.developer || '—')}</td>
      <td style="color:var(--text-3);font-family:var(--mono);font-size:.73rem">${esc(d.release_date || '—')}</td>
      <td>${osIcons(d.os_support || '')}</td>
    </tr>`;
  }).join('');
}

function osIcons(os) {
  if (!os) return '—';
  return `<div class="os-row">${os.split(',').map(p => {
    p = p.trim();
    if (/win/i.test(p)) return '<div class="os-dot ow" title="Windows"></div>';
    if (/mac/i.test(p)) return '<div class="os-dot om" title="macOS"></div>';
    if (/lin/i.test(p)) return '<div class="os-dot ol" title="Linux"></div>';
    return '';
  }).join('')}</div>`;
}

const esc = s => String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/* ═══════════════════════════════════════════
   PAGINATION
═══════════════════════════════════════════ */
function renderPages() {
  const tot  = Math.ceil(FILTERED.length / PAGE);
  const wrap = document.getElementById('pages');
  if (tot <= 1) { wrap.innerHTML = ''; return; }

  const range = tot <= 7 ? arr(tot)
    : page <= 4 ? [1, 2, 3, 4, 5, '…', tot]
    : page >= tot - 3 ? [1, '…', tot - 4, tot - 3, tot - 2, tot - 1, tot]
    : [1, '…', page - 1, page, page + 1, '…', tot];

  wrap.innerHTML =
    btn('‹', page <= 1, `goPage(${page - 1})`, 'Previous') +
    range.map(p => p === '…'
      ? `<span class="pg-dots">…</span>`
      : `<button class="pg ${p === page ? 'active' : ''}" onclick="goPage(${p})" aria-label="Page ${p}" ${p === page ? 'aria-current=page' : ''}>${p}</button>`
    ).join('') +
    btn('›', page >= tot, `goPage(${page + 1})`, 'Next');
}

const arr = n => Array.from({ length: n }, (_, i) => i + 1);
const btn = (lbl, dis, fn, ar) => `<button class="pg" ${dis ? 'disabled' : ''} onclick="${fn}" aria-label="${ar}">${lbl}</button>`;

function goPage(p) {
  page = p; renderTable(); renderPages();
  document.getElementById('tc').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ═══════════════════════════════════════════
   EXPORT CSV
═══════════════════════════════════════════ */
function exportCSV() {
  const q      = document.getElementById('f-q').value;
  const genre  = document.getElementById('f-genre').value;
  const rating = document.getElementById('f-rating').value;
  const price  = document.getElementById('f-price').value;

  const params = new URLSearchParams();
  if (q)      params.set('q',      q);
  if (genre)  params.set('genre',  genre);
  if (rating) params.set('rating', rating);
  if (price)  params.set('price',  price);

  const url = `${API}/export?${params.toString()}`;
  const a   = document.createElement('a');
  a.href    = url;
  a.download = 'steam_games_export.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/* ═══════════════════════════════════════════
   CLEAR DATA
═══════════════════════════════════════════ */
async function clearData() {
  if (!confirm('Delete all scraped data? This cannot be undone.')) return;
  try {
    const r = await fetch(`${API}/clear`, { method: 'DELETE' });
    const text = await r.text();
    let j;
    try { j = JSON.parse(text); } catch { alert('Server returned: ' + text.slice(0, 200)); return; }
    if (!r.ok) { alert(j.error || 'Failed'); return; }
    ALL = []; FILTERED = [];
    buildStats(); buildCharts(); showNoData();
    document.getElementById('f-count').textContent = '0';
  } catch (e) { alert('Fetch error: ' + e.message); }
}

/* ═══════════════════════════════════════════
   SCRAPE
═══════════════════════════════════════════ */
async function startScrape() {
  const genre    = document.getElementById('sc-genre').value;
  const rows     = parseInt(document.getElementById('sc-rows').value);
  const maxPages = Math.min(80, Math.ceil(rows / 25));
  const scrapeBtn = document.getElementById('btn-scrape');

  scrapeBtn.disabled = true;
  setScrapeUI(true, 'Starting scraper…');

  try {
    const res = await fetch(`${API}/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ genre, max_pages: maxPages, test: false }),
    });
    const j = await res.json();
    if (res.status === 409) {
      document.getElementById('sc-status-txt').textContent = 'Already running — attaching…';
      pollStatus();
      return;
    }
    if (!res.ok) { setStatus('Error: ' + (j.error || res.status), false); scrapeBtn.disabled = false; return; }
    pollStatus();
  } catch (e) {
    setStatus('Error: ' + e.message, false);
    scrapeBtn.disabled = false;
  }
}

function setScrapeUI(running, statusTxt) {
  document.getElementById('sc-spinner').style.display     = running ? 'block' : 'none';
  document.getElementById('btn-stop').style.display       = running ? 'inline-flex' : 'none';
  document.getElementById('sc-progress').style.display    = running ? 'block' : 'none';
  document.getElementById('sc-live-count').style.display  = running ? 'block' : 'none';
  document.getElementById('sc-state-pill').textContent    = running ? '● Scraping' : '● Idle';
  document.getElementById('sc-state-pill').className      = running ? 'pill pill-purple' : 'pill pill-gray';
  if (statusTxt) document.getElementById('sc-status-txt').textContent = statusTxt;
  if (running) {
    const lb = document.getElementById('log-box');
    lb.style.height    = '120px';
    lb.style.overflowY = 'auto';
    lb.style.color     = 'var(--text-2)';
    lb.style.cursor    = 'default';
  }
}

function pollStatus() {
  clearInterval(pollTimer);
  let tick = 0;
  const targetRows = parseInt(document.getElementById('sc-rows').value) || 2000;

  pollTimer = setInterval(async () => {
    try {
      const r = await fetch(`${API}/scrape/status`);
      const s = await r.json();

      if (s.log && s.log.length) {
        const lb = document.getElementById('log-box');
        lb.textContent = s.log.join('\n');
        lb.scrollTop   = lb.scrollHeight;
      }

      if (!s.running && s.done) {
        clearInterval(pollTimer);
        document.getElementById('btn-scrape').disabled = false;
        setScrapeUI(false, s.error ? '✗ Stopped: ' + s.error : '✓ Done! Loading fresh data…');
        await loadData();
        const count = ALL.length;
        document.getElementById('sc-status-txt').textContent = `✓ Complete — ${count} games loaded`;
        document.getElementById('sc-live-count').style.display = 'none';
      } else {
        tick++;
        if (tick % 4 === 0) {
          await loadData();
          const count = ALL.length;
          document.getElementById('sc-live-count').textContent = count + ' rows';
          const pct = Math.min(95, Math.round((count / targetRows) * 100));
          document.getElementById('sc-bar').style.width = pct + '%';
        }
        const lastLog = s.log.length ? s.log[s.log.length - 1].replace(/\s+/g, ' ').trim().slice(0, 80) : 'Initialising…';
        document.getElementById('sc-status-txt').textContent = lastLog;
      }
    } catch { /* ignore poll errors */ }
  }, 1500);
}

async function stopScrape() {
  await fetch(`${API}/scrape/stop`, { method: 'POST' });
  document.getElementById('sc-status-txt').textContent = 'Stopping… (finishing current page)';
}

function toggleLog() {
  const lb = document.getElementById('log-box');
  lb.style.height = lb.style.height === '200px' ? '120px' : '200px';
}

/* ═══════════════════════════════════════════
   CHARTS
═══════════════════════════════════════════ */
const TTP = document.getElementById('tooltip');

function showTip(lbl, val, x, y) {
  document.getElementById('tt-lbl').textContent = lbl;
  document.getElementById('tt-val').textContent = val;
  TTP.style.left = (x + 14) + 'px';
  TTP.style.top  = (y - 44) + 'px';
  TTP.classList.add('show');
}
function hideTip() { TTP.classList.remove('show'); }

function buildCharts() { buildGenre(); buildPrice(); }

function drawChart(cvId, entries, opts) {
  const cv  = document.getElementById(cvId);
  const ctx = cv.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const W   = cv.parentElement.clientWidth;
  const H   = 190;
  cv.width = W * dpr; cv.height = H * dpr;
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  ctx.scale(dpr, dpr);

  const PAD = { t: 8, r: 8, b: opts.rotateLabels ? 55 : 36, l: 8 };
  const cH  = H - PAD.t - PAD.b;
  const bW  = (W - PAD.l - PAD.r) / entries.length;
  const max = Math.max(...entries.map(e => e.v), 1);

  ctx.strokeStyle = 'rgba(255,255,255,0.04)'; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75, 1].forEach(f => {
    const y = PAD.t + cH * (1 - f);
    ctx.beginPath(); ctx.moveTo(PAD.l, y); ctx.lineTo(W - PAD.r, y); ctx.stroke();
  });

  const hits = [];
  entries.forEach((e, i) => {
    const bh = cH * (e.v / max);
    const bx = PAD.l + i * bW + bW * 0.1;
    const bw = bW * 0.8;
    const by = PAD.t + cH - bh;

    if (bh > 0) {
      ctx.save();
      ctx.shadowColor = e.c; ctx.shadowBlur = 8;
      ctx.fillStyle = e.c; ctx.globalAlpha = 0.88;
      roundRect(ctx, bx, by, bw, bh, [4, 4, 0, 0]); ctx.fill();
      ctx.restore();
      ctx.fillStyle = '#E2E8F0'; ctx.font = `600 9px Fira Code,monospace`; ctx.textAlign = 'center';
      ctx.fillText(e.v.toLocaleString(), bx + bw / 2, by - 4);
    }

    ctx.fillStyle = '#64748B'; ctx.font = `10px Fira Sans,sans-serif`; ctx.textAlign = 'center';
    if (opts.rotateLabels) {
      ctx.save(); ctx.translate(bx + bw / 2, H - PAD.b + 16); ctx.rotate(-Math.PI / 6);
      ctx.fillText(e.l, 0, 0); ctx.restore();
    } else {
      ctx.fillText(e.l, bx + bw / 2, H - PAD.b + 14);
    }
    hits.push({ x: bx, y: PAD.t, w: bw, h: cH, l: e.l, v: e.v });
  });

  cv.addEventListener('mousemove', evt => {
    const r = cv.getBoundingClientRect(), mx = evt.clientX - r.left, my = evt.clientY - r.top;
    const hit = hits.find(h => mx >= h.x && mx <= h.x + h.w && my >= h.y && my <= h.y + h.h);
    if (hit) showTip(hit.l, hit.v.toLocaleString() + ' games', evt.clientX, evt.clientY);
    else hideTip();
  });
  cv.addEventListener('mouseleave', hideTip);
}

function buildGenre() {
  const COLS = ['#7C3AED', '#A78BFA', '#4ADE80', '#F43F5E', '#FBBF24', '#60A5FA', '#FB923C', '#E879F9', '#34D399', '#F472B6'];
  const gc = {};
  ALL.forEach(g => gc[g.genre] = (gc[g.genre] || 0) + 1);
  const entries = Object.entries(gc).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([l, v], i) => ({ l, v, c: COLS[i] }));
  drawChart('chart-genre', entries, { rotateLabels: true });
}

function buildPrice() {
  const bkts = [
    { l: 'Free', lo: 0, hi: 0 }, { l: '$1–5', lo: 1, hi: 5 }, { l: '$5–10', lo: 5, hi: 10 },
    { l: '$10–20', lo: 10, hi: 20 }, { l: '$20–30', lo: 20, hi: 30 }, { l: '$30–50', lo: 30, hi: 50 }, { l: '$50+', lo: 50, hi: Infinity }
  ];
  const COLS = ['#7C3AED', '#8B5CF6', '#A78BFA', '#818CF8', '#6366F1', '#4F46E5', '#4338CA'];
  const entries = bkts.map((b, i) => ({ l: b.l, v: ALL.filter(g => g.price >= b.lo && g.price <= b.hi).length, c: COLS[i] }));
  drawChart('chart-price', entries, { rotateLabels: false });
}

function roundRect(ctx, x, y, w, h, r) {
  if (h <= 0 || w <= 0) return;
  ctx.beginPath();
  if (ctx.roundRect) { ctx.roundRect(x, y, w, h, r); }
  else {
    const [tl, tr] = Array.isArray(r) ? r : [r, r];
    ctx.moveTo(x + tl, y); ctx.lineTo(x + w - tr, y); ctx.arcTo(x + w, y, x + w, y + tr, tr);
    ctx.lineTo(x + w, y + h); ctx.lineTo(x, y + h); ctx.lineTo(x, y + tl); ctx.arcTo(x, y, x + tl, y, tl);
    ctx.closePath();
  }
}

/* ═══════════════════════════════════════════
   EVENTS
═══════════════════════════════════════════ */
function bindEvents() {
  let deb;
  document.getElementById('f-q').addEventListener('input', () => { clearTimeout(deb); deb = setTimeout(applyFilters, 220); });
  ['f-genre', 'f-rating', 'f-price'].forEach(id => document.getElementById(id).addEventListener('change', applyFilters));

  document.querySelectorAll('thead th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      sortDir = sortCol === col ? (sortDir === 'asc' ? 'desc' : 'asc') : 'asc';
      sortCol = col;
      document.querySelectorAll('thead th').forEach(t => t.removeAttribute('aria-sort'));
      th.setAttribute('aria-sort', sortDir === 'asc' ? 'ascending' : 'descending');
      doSort(); page = 1; renderTable(); renderPages();
    });
    th.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); th.click(); } });
  });

  window.addEventListener('resize', buildCharts);
}

/* ═══════════════════════════════════════════
   GSAP ANIMATION
═══════════════════════════════════════════ */
function animateIn() {
  if (window.matchMedia('(prefers-reduced-motion:reduce)').matches) return;
  gsap.from('.sc', { opacity: 0, y: 14, scale: .97, duration: .38, stagger: { each: .07 }, ease: 'back.out(1.4)', delay: .1 });
  gsap.from('#gc,#pc', { opacity: 0, y: 18, duration: .42, stagger: .1, ease: 'back.out(1.4)', delay: .32 });
  gsap.from('#sc-panel,#tc', { opacity: 0, y: 20, duration: .4, stagger: .1, ease: 'power3.out', delay: .5 });
}

boot();
