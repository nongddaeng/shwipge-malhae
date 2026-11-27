(function () {
  "use strict";

  /* ───────── 도구 ───────── */
  const $ = (id) => document.getElementById(id);
  const root = document.documentElement;
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} },
  };
  const getJSON = (url) =>
    fetch(url, { cache: "no-store" }).then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });

  function dayLabel(iso, opts) {
    const d = new Date(iso + "T00:00:00+09:00");
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("ko-KR", { timeZone: "Asia/Seoul", month: "long", day: "numeric", ...(opts || {}) });
  }
  const shortDay = (iso) => { const [, m, d] = iso.split("-"); return `${+m}.${+d}`; };
  function timeText(iso) {
    const dt = new Date(iso);
    return isNaN(dt) ? "" : dt.toLocaleTimeString("ko-KR", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Seoul" });
  }

  /* ───────── 상태 ───────── */
  const state = {
    dates: [], latest: null, date: null, data: null, cache: {},
    glossary: null, kw: null, quiz: {},
    mode: store.get("sm-mode") || "both",
  };
  const catName = {};
  /* 분야별 노선색 (CSS 변수) */
  const lineColor = (cat) => `var(--l-${/^[a-z]+$/.test(cat || "") ? cat : "x"}, var(--ink))`;
  const lineMark = (name) => (/^[A-Za-z]/.test(name) ? name.slice(0, 2) : name.slice(0, 1));
  const isToday = () => state.date === state.latest;

  /* ───────── 데이터 ───────── */
  function loadDate(date) {
    if (state.cache[date]) return Promise.resolve(state.cache[date]);
    const url = date === state.latest ? "data/news.json" : `data/archive/${encodeURIComponent(date)}.json`;
    return getJSON(url).then((d) => (state.cache[date] = d));
  }

  function setDate(date) {
    return loadDate(date).then((d) => {
      state.date = date; state.data = d; state.quiz = {}; state.kw = null;
      d.categories.forEach((c) => (catName[c.id] = c.name));
      $("date-select").value = date;
      const nSrc = new Set(d.cards.flatMap((c) => (c.sources || []).map((s) => s.name))).size;
      $("edition").innerHTML =
        `<b>${esc(dayLabel(d.date, { weekday: "long" }))} 아침</b>` +
        `<span>기사 ${esc(d.stats?.collected ?? "-")}건 중 ${d.cards.length}개 소식</span><span>언론사 ${nSrc}곳</span>`;
      $("stamp").textContent = `${(d.generated_at || "").replace("T", " ").slice(0, 16)} 발행`;
    });
  }

  function openCard(date, id) {
    const go = () => {
      const target = "#card-" + id;
      if (location.hash === target) render(); else location.hash = target;
    };
    if (date === state.date) go();
    else setDate(date).then(go).catch(() => notice("그날 뉴스를 불러오지 못했어요."));
  }
  function notice(msg) { $("notices").innerHTML = `<div class="notice warn">${esc(msg)}</div>`; }

  /* ───────── 내비 ───────── */
  function currentRoute() {
    const h = (location.hash || "#all").slice(1);
    if (h.startsWith("card-")) return { view: "all", card: h.slice(5) };
    if (h === "quiz" || h === "glossary") return { view: h };
    if (state.data && state.data.categories.some((c) => c.id === h)) return { view: h };
    return { view: "all" };
  }

  function renderTabs(active) {
    const d = state.data;
    const counts = {};
    d.cards.forEach((c) => (counts[c.category] = (counts[c.category] || 0) + 1));
    const tab = (id, name, n, color, plain) =>
      `<a class="tab${plain ? " plain" : ""}${id === "all" ? " home" : ""}" role="tab" href="#${id}" style="--c:${color || "var(--ink)"}" aria-selected="${id === active && !state.kw}">` +
      `${plain ? "" : `<span class="dot" aria-hidden="true">${esc(lineMark(name))}</span>`}${esc(name)}${n ? `<span class="count">${n}</span>` : ""}</a>`;
    $("tabs").innerHTML =
      tab("all", "종합", d.cards.length) +
      d.categories.map((c) => tab(c.id, c.name, counts[c.id] || 0, lineColor(c.id))).join("") +
      `<span class="tab-sep" aria-hidden="true"></span>` +
      tab("quiz", "퀴즈", (d.quiz || []).length, null, true) + tab("glossary", "용어 사전", 0, null, true);
  }

  function renderNotices() {
    const parts = [];
    if (state.data.sample) parts.push(`<div class="notice warn">지금 보이는 기사는 화면 확인용 예시예요. 매일 아침 자동 실행이 시작되면 실제 뉴스로 바뀝니다.</div>`);
    if (!isToday())
      parts.push(`<div class="notice">${esc(dayLabel(state.date, { weekday: "long" }))} 지난 신문을 보고 있어요.<button type="button" class="link-btn" data-act="today">오늘 신문으로</button></div>`);
    $("notices").innerHTML = parts.join("");
  }

  /* ───────── 기사 ───────── */
  const badge = (cat) => `<span class="badge" style="--c:${lineColor(cat)}">${esc(catName[cat] || "")}</span>`;

  function storyHTML(c, { lead = false } = {}) {
    const kws = (c.keywords || []).map((k) => `<button type="button" class="kw" data-kw="${esc(k)}">${esc(k)}</button>`).join("");
    const terms = (c.terms || []).map((t) => `<div><dt>${esc(t.word)}</dt><dd>${esc(t.meaning)}</dd></div>`).join("");
    const srcs = (c.sources || [])
      .map((s) => `<a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener" title="${esc(s.title)}">${esc(s.name)}</a>`)
      .join("");
    const related = (c.related || [])
      .map((r) => `<li><button type="button" data-open-date="${esc(r.date)}" data-open-id="${esc(r.id)}"><time datetime="${esc(r.date)}">${esc(shortDay(r.date))}</time>${esc(r.headline)}</button></li>`)
      .join("");
    const n = (c.sources || []).length;
    const H = lead ? "h2" : "h3";

    return `
<article class="story${lead ? " lead-story" : ""}" id="card-${esc(c.id)}" style="--c:${lineColor(c.category)}">
  <p class="kicker">${badge(c.category)}${kws}</p>
  <${H} class="hed">${esc(c.headline)}</${H}>
  <p class="byline"><b>언론 ${n}곳 보도</b> · ${esc(timeText(c.published))}</p>
  <div class="body">
    <div class="col-a">
      <div class="summary"><span class="label">요약</span><p>${esc(c.summary)}</p></div>
    </div>
    <div class="col-b">
      ${c.easy_summary ? `<div class="easy"><span class="label">쉽게 말해</span><p>${esc(c.easy_summary)}</p>${terms ? `<dl class="terms">${terms}</dl>` : ""}</div>` : ""}
      ${c.why_me ? `<p class="why-me"><b>이게 나랑 무슨 상관?</b>${esc(c.why_me)}</p>` : ""}
      ${related ? `<div class="related"><span class="label">지난 이야기</span><ul>${related}</ul></div>` : ""}
    </div>
  </div>
  <p class="sources">출처 ${srcs}</p>
</article>`;
  }

  const gridHTML = (list, wide) =>
    `<div class="grid${wide ? " wide" : ""}">${list.map((c) => storyHTML(c)).join("")}</div>`;

  function boardHTML() {
    const d = state.data;
    const items = (d.briefing || [])
      .map((x) =>
        `<li><button type="button" data-jump="${esc(x.id)}" style="--c:${lineColor(x.category)}">` +
        `<span class="row">${badge(x.category)}</span><span class="txt">${esc(x.text)}</span></button></li>`)
      .join("");
    if (!items) return "";
    const qn = (d.quiz || []).length;
    const words = [...new Set(d.cards.flatMap((c) => (c.terms || []).map((t) => t.word)))].slice(0, 6);
    const foot = [
      qn ? `<a href="#quiz"><b>퀴즈</b>오늘 뉴스로 ${qn}문제 풀기 →</a>` : "",
      words.length ? `<span class="words-inline"><a href="#glossary" style="border:0;color:var(--sign);font-family:var(--title)">오늘 나온 말</a> ${words.map((w) => `<a href="#glossary" data-gq="${esc(w)}">${esc(w)}</a>`).join("")}</span>` : "",
    ].join("");
    return `<section class="board" aria-label="아침 3줄 요약">
      <div class="board-head"><h2>${isToday() ? "오늘 아침" : esc(dayLabel(state.date))} 3줄</h2><span>가장 많은 언론사가 다룬 소식</span></div>
      <ol>${items}</ol>${foot ? `<div class="board-foot">${foot}</div>` : ""}</section>`;
  }

  const FRONT_N = 3; // 종합면에는 분야별로 많이 보도된 3개만

  function renderFront(focusId) {
    const d = state.data;
    const sections = d.categories
      .map((cat) => {
        const list = d.cards.filter((c) => c.category === cat.id);
        if (!list.length) return "";
        return `<section class="sec" style="--c:${lineColor(cat.id)}"><div class="sec-head"><span class="ring" aria-hidden="true"></span><h2>${esc(cat.name)}</h2>` +
          `<span class="rail" aria-hidden="true"></span>${list.length > FRONT_N ? `<a href="#${esc(cat.id)}">${list.length}개 모두 보기 →</a>` : ""}</div>${gridHTML(list.slice(0, FRONT_N))}</section>`;
      })
      .join("");
    $("view").innerHTML = boardHTML() + (sections || `<p class="empty">이날은 소식이 없어요.</p>`);
    if (focusId && !document.getElementById("card-" + focusId)) {
      const c = d.cards.find((x) => x.id === focusId);
      if (c) { renderSection(c.category); renderTabs(c.category); }
    }
    focus(focusId);
  }

  function renderSection(catId) {
    const list = state.data.cards.filter((c) => c.category === catId);
    $("view").innerHTML =
      `<div class="page-head" style="--c:${lineColor(catId)}"><span class="ring" aria-hidden="true"></span><h1>${esc(catName[catId] || "")}</h1><p>${esc(dayLabel(state.date, { weekday: "long" }))} · ${list.length}개 소식, 많이 보도된 순</p></div>` +
      (list.length ? gridHTML(list, true) : `<p class="empty">이 지면은 이날 소식이 없어요.</p>`);
  }

  function renderKeyword() {
    const list = state.data.cards.filter((c) => (c.keywords || []).includes(state.kw));
    $("view").innerHTML =
      `<div class="filter-bar"><h1>#${esc(state.kw)}</h1><span>관련 기사 ${list.length}개</span><button type="button" class="link-btn" data-act="clear-kw">모아보기 끝내기</button></div>` +
      gridHTML(list);
  }

  function focus(id) {
    if (!id) return;
    const el = document.getElementById("card-" + id);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash");
  }

  /* ───────── 퀴즈 ───────── */
  function renderQuiz() {
    const qs = state.data.quiz || [];
    const title = isToday() ? "오늘의 퀴즈" : `${dayLabel(state.date)} 퀴즈`;
    const head = `<div class="page-head"><h1>${esc(title)}</h1><p>그날 뉴스로 만든 문제예요. 보기를 누르면 바로 정답과 해설이 나와요.</p></div>`;
    if (!qs.length) { $("view").innerHTML = `<div class="panel">${head}<p class="empty">이날은 퀴즈가 없어요.</p></div>`; return; }
    const right = qs.filter((q, i) => state.quiz[i] === q.answer).length;
    const html = qs
      .map((q, i) => {
        const picked = state.quiz[i], done = picked != null;
        const opts = q.options
          .map((o, j) => {
            let cls = "opt";
            if (done && j === q.answer) cls += " right";
            else if (done && j === picked) cls += " wrong";
            return `<button type="button" class="${cls}" data-q="${i}" data-o="${j}" ${done ? "disabled" : ""}>${esc(o)}</button>`;
          })
          .join("");
        const exp = done
          ? `<p class="explain"><strong>${picked === q.answer ? "정답이에요." : "아쉬워요."}</strong> ${esc(q.explanation)}
             <button type="button" class="link-btn" data-open-date="${esc(state.date)}" data-open-id="${esc(q.card_id)}">관련 기사 보기</button></p>`
          : "";
        return `<section class="q"><h2><span class="num">${i + 1}</span>${esc(q.question)}</h2><div class="opts">${opts}</div>${exp}</section>`;
      })
      .join("");
    const score = Object.keys(state.quiz).length === qs.length
      ? `<div class="score"><div>${qs.length}문제 중</div><div class="big">${right}개 맞혔어요</div><button type="button" data-act="retry">다시 풀기</button></div>`
      : "";
    $("view").innerHTML = `<div class="panel">${head}${html}${score}</div>`;
  }

  /* ───────── 용어 사전 ───────── */
  function renderGlossary(initial) {
    const draw = (q) => {
      const all = state.glossary || [];
      const k = (q || "").trim();
      const list = k ? all.filter((g) => g.word.includes(k) || g.meaning.includes(k)) : all;
      $("gloss").innerHTML = list.length
        ? list.map((g) =>
            `<dl class="g"><dt>${esc(g.word)}</dt><dd>${esc(g.meaning)}</dd><div class="refs">${(g.refs || [])
              .map((r) => `<button type="button" data-open-date="${esc(r.date)}" data-open-id="${esc(r.id)}">${esc(shortDay(r.date))} ${esc(r.headline)}</button>`)
              .join("")}</div></dl>`).join("")
        : `<p class="empty">찾는 말이 아직 없어요.</p>`;
      $("g-count").textContent = k ? `'${k}' 찾은 결과 ${list.length}개` : `지금까지 모은 말 ${all.length}개 · 가나다순`;
    };
    $("view").innerHTML = `<div class="page-head"><h1>용어 사전</h1><p>뉴스에 나온 어려운 말을 날마다 모아 쉬운 뜻을 달아 두었어요.</p></div>
      <input class="search" id="g-search" type="search" placeholder="찾을 말을 입력하세요 (예: 기준금리)" aria-label="용어 찾기" value="${esc(initial || "")}" />
      <div class="g-count" id="g-count"></div><div class="gloss" id="gloss"></div>`;
    $("g-search").addEventListener("input", (e) => draw(e.target.value));
    if (state.glossary) draw(initial);
    else {
      $("gloss").innerHTML = `<p class="empty">불러오는 중…</p>`;
      getJSON("data/glossary.json")
        .then((g) => { state.glossary = g; draw($("g-search").value); })
        .catch(() => { $("gloss").innerHTML = `<p class="empty">용어 사전을 불러오지 못했어요.</p>`; });
    }
  }

  /* ───────── 그리기 ───────── */
  let glossQuery = "";
  function render() {
    if (!state.data) return;
    const r = currentRoute();
    renderTabs(r.view);
    renderNotices();
    if (r.view === "quiz") renderQuiz();
    else if (r.view === "glossary") { renderGlossary(glossQuery); glossQuery = ""; }
    else if (state.kw) renderKeyword();
    else if (r.view === "all") renderFront(r.card);
    else renderSection(r.view);
  }

  /* ───────── 보기 설정 ───────── */
  function applyMode(m) {
    state.mode = m;
    document.body.classList.remove("mode-both", "mode-easy", "mode-orig");
    document.body.classList.add("mode-" + m);
    document.querySelectorAll("[data-mode]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === m)));
    store.set("sm-mode", m);
  }
  function changeFont(delta) {
    const cur = root.dataset.fs == null ? 1 : +root.dataset.fs;
    const next = Math.max(0, Math.min(3, (isNaN(cur) ? 1 : cur) + delta));
    root.dataset.fs = next;
    store.set("sm-fs", String(next));
    $("fs-down").disabled = next === 0;
    $("fs-up").disabled = next === 3;
  }
  function applyTheme(t) {
    if (t) { root.dataset.theme = t; store.set("sm-theme", t); }
    const cur = root.dataset.theme === "dark" ? "dark" : "light";
    document.querySelectorAll("[data-theme-set]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.themeSet === cur)));
  }

  /* ───────── 이벤트 ───────── */
  document.addEventListener("click", (e) => {
    const s = $("settings");
    if (s.open && !s.contains(e.target)) s.open = false;

    const gq = e.target.closest("[data-gq]");
    if (gq) { glossQuery = gq.dataset.gq; return; }

    const t = e.target.closest("button");
    if (!t) return;
    if (t.dataset.kw) {
      state.kw = t.dataset.kw;
      if (location.hash && location.hash !== "#all") location.hash = "all"; else render();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else if (t.dataset.jump) openCard(state.date, t.dataset.jump);
    else if (t.dataset.openId) openCard(t.dataset.openDate, t.dataset.openId);
    else if (t.dataset.q != null) { state.quiz[+t.dataset.q] = +t.dataset.o; renderQuiz(); }
    else if (t.dataset.mode) applyMode(t.dataset.mode);
    else if (t.dataset.themeSet) applyTheme(t.dataset.themeSet);
    else if (t.dataset.act === "clear-kw") { state.kw = null; render(); }
    else if (t.dataset.act === "retry") { state.quiz = {}; renderQuiz(); window.scrollTo({ top: 0, behavior: "smooth" }); }
    else if (t.dataset.act === "today") setDate(state.latest).then(render);
  });
  $("fs-down").addEventListener("click", () => changeFont(-1));
  $("fs-up").addEventListener("click", () => changeFont(1));
  $("date-select").addEventListener("change", (e) => {
    setDate(e.target.value).then(() => { location.hash = "all"; render(); }).catch(() => notice("그날 뉴스를 불러오지 못했어요."));
  });
  window.addEventListener("hashchange", () => {
    if (location.hash !== "#all" && !location.hash.startsWith("#card-")) state.kw = null;
    render();
  });

  /* ───────── 시작 ───────── */
  applyMode(state.mode);
  applyTheme();
  changeFont(0);
  getJSON("data/news.json")
    .then((latest) => {
      state.latest = latest.date;
      state.cache[latest.date] = latest;
      return getJSON("data/dates.json").catch(() => [latest.date]).then((dates) => {
        state.dates = dates.includes(latest.date) ? dates : [latest.date].concat(dates);
        $("date-select").innerHTML = state.dates
          .map((d, i) => `<option value="${esc(d)}">${i === 0 ? "오늘 신문" : esc(dayLabel(d, { weekday: "short" })) + " 신문"}</option>`)
          .join("");
        return setDate(latest.date);
      });
    })
    .then(render)
    .catch(() => {
      $("edition").textContent = "";
      $("view").innerHTML = `<p class="empty">뉴스를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.</p>`;
    });
})();
