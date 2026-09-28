const MAX_LIVE = 2;
const HARNESS_COLORS = [
  "var(--blinky)",
  "var(--pinky)",
  "var(--inky)",
  "var(--clyde)",
  "var(--pac)",
  "var(--maze-bright)",
  "var(--mint)",
  "var(--dot)",
];
const SVG_NS = "http://www.w3.org/2000/svg";
const COMPANIES = {
  claude: "Anthropic",
  cursor: "Cursor",
  deepseek: "DeepSeek",
  gemini: "Google",
  glm: "Z.ai",
  gpt: "OpenAI",
  grok: "xAI",
  kimi: "Moonshot AI",
  minimax: "MiniMax",
  muse: "Meta",
  qwen: "Alibaba",
};
const byName = (a, b) => a.localeCompare(b, "en", { numeric: true, sensitivity: "base" });

const state = { query: "", models: new Set(), sort: "default", descending: false };
const SORT_VALUE = {
  cost: (entry) => entry.cost_usd,
  time: (entry) => entry.duration_ms,
  tokens: (entry) => stripToken(entry).value,
};
const SORT_DIR = {
  cost: [
    ["↑ Cheap", "Lowest cost first"],
    ["↓ Pricey", "Highest cost first"],
  ],
  time: [
    ["↑ Fast", "Fastest first"],
    ["↓ Slow", "Slowest first"],
  ],
  tokens: [
    ["↑ Few", "Fewest tokens first"],
    ["↓ Most", "Most tokens first"],
  ],
};
const ui = {};
let cards = [];
const visibleScreens = new Map();
const mountedScreens = new Set();
let hoveredScreen = null;
let scrolling = false;
let scrollTimer = 0;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

const previewObserver = new IntersectionObserver(
  (records) => {
    for (const record of records) {
      if (record.isIntersecting) visibleScreens.set(record.target, record.intersectionRatio);
      else visibleScreens.delete(record.target);
    }
    schedulePreviews();
  },
  { threshold: [0, 0.25, 0.5, 0.75, 1] }
);

addEventListener(
  "scroll",
  () => {
    if (!scrolling) {
      scrolling = true;
      for (const screen of mountedScreens) freezePreview(screen);
    }
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      scrolling = false;
      schedulePreviews();
    }, 140);
  },
  { passive: true }
);

reducedMotion.addEventListener("change", schedulePreviews);

init();

async function init() {
  ui.grid = document.querySelector(".grid");
  ui.models = document.querySelector(".models");
  ui.modelsToggle = ui.models.querySelector(".models-toggle");
  ui.modelsValue = ui.models.querySelector("[data-models-value]");
  ui.modelsPanel = ui.models.querySelector(".models-panel");
  ui.modelsList = ui.models.querySelector(".models-list");
  ui.modelsClear = ui.models.querySelector(".models-clear");
  ui.search = document.querySelector("#search");
  ui.count = document.querySelector("[data-count]");
  ui.gameOver = document.querySelector(".game-over");
  ui.sortKeys = document.querySelector(".sort-keys");
  ui.sortDir = document.querySelector(".sort-dir");
  ui.sortKeyButtons = [...ui.sortKeys.querySelectorAll("[data-sort]")];
  ui.sortDirButtons = [...ui.sortDir.querySelectorAll("[data-order]")];

  const response = await fetch("./entries/meta.json");
  if (!response.ok) throw new Error(`meta.json: HTTP ${response.status}`);
  const entries = await response.json();

  const harnesses = [...new Set(entries.map((entry) => entry.harness))];
  const colors = new Map(harnesses.map((harness, i) => [harness, HARNESS_COLORS[i % HARNESS_COLORS.length]]));

  const labels = collisionLabels(entries);
  cards = entries.map((entry, i) => buildCard(entry, i, colors.get(entry.harness), labels.get(entry)));
  ui.grid.append(...cards.map((card) => card.el));
  buildModelFilter();
  ui.modelBoxes = [...ui.modelsList.querySelectorAll("input")];
  bindEvents();
  applyFilters();
  await loadSizes();
}

function buildCard(entry, index, color, asked) {
  const el = h("article", "cab");
  el.style.setProperty("--c", color);
  el.style.setProperty("--i", index);

  const screen = h("div", "cab-screen");
  screen.inert = true;
  screen.setAttribute("aria-hidden", "true");
  screen.dataset.src = entryUrl(entry);
  screen.dataset.title = `${entry.display_model} preview`;
  screen.append(h("span", "cab-coin", "INSERT COIN"), h("span", "cab-start", "▶ PRESS START"));

  const top = h("div", "cab-top");
  const harness = h("span", "cab-harness");
  harness.append(ghostIcon(), document.createTextNode(entry.harness));
  top.append(harness, h("span", "cab-no", `#${String(index + 1).padStart(2, "0")}`));

  const link = h("a", "cab-link", entry.display_model);
  link.href = entryUrl(entry);
  link.target = "_blank";
  link.rel = "noopener";
  const qualifier = asked ? `, ${asked}` : "";
  link.append(h("span", "visually-hidden", ` (${entry.harness}${qualifier}, opens in a new tab)`));
  const title = h("h3", "cab-model");
  title.append(link);

  const body = h("div", "cab-body");
  body.append(top, title);
  if (asked) body.append(h("p", "cab-asked", asked));

  const tags = h("div", "cab-tags");
  if (entry.phase != null) tags.append(h("span", "cab-tag", `PHASE ${entry.phase}`));
  if (entry.effort) tags.append(h("span", "cab-tag", `${entry.effort} effort`));
  const sizeTag = h("span", "cab-tag");
  sizeTag.hidden = true;
  tags.append(sizeTag);

  const details = h("details", "cab-details");
  details.append(h("summary", "cab-details-toggle", "RUN DATA"), statList("cab-detail-list", detailRows(entry)));
  const sizeValue = details.querySelector('[data-field="size"]');

  body.append(tags, statList("cab-stats", stripRows(entry)), details);
  el.append(screen, body);
  el.addEventListener("pointerenter", () => holdPreview(screen));
  el.addEventListener("pointerleave", () => releasePreview(screen));
  el.addEventListener("focusin", () => holdPreview(screen));
  el.addEventListener("focusout", (event) => {
    if (!el.contains(event.relatedTarget)) releasePreview(screen);
  });
  el.addEventListener("animationend", () => {
    el.style.animation = "none";
  }, { once: true });
  previewObserver.observe(screen);

  const haystack = [entry.display_model, entry.requested, entry.actual, entry.harness, entry.slug, entry.run, asked]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  const setSize = (bytes) => {
    sizeTag.textContent = sizeValue.textContent = formatBytes(bytes);
    sizeTag.hidden = false;
    sizeValue.classList.remove("is-empty");
  };
  return { el, entry, model: modelName(entry), haystack, setSize };
}

function modelName(entry) {
  const name = shortName(entry.display_model);
  const effort = `-${entry.effort}`;
  return entry.effort && name.endsWith(effort) ? name.slice(0, -effort.length) : name;
}

function shortName(name) {
  return name.split("/").pop();
}

function collisionLabels(entries) {
  const counts = new Map();
  for (const entry of entries) counts.set(entry.display_model, (counts.get(entry.display_model) ?? 0) + 1);

  const labels = new Map();
  for (const entry of entries) {
    if (counts.get(entry.display_model) < 2) continue;
    const asked = entry.requested && shortName(entry.requested);
    if (entry.actual && asked && asked !== shortName(entry.display_model)) labels.set(entry, `asked ${asked}`);
  }

  const stillTied = new Map();
  for (const entry of entries) {
    if (counts.get(entry.display_model) < 2 || labels.has(entry)) continue;
    stillTied.set(entry.display_model, (stillTied.get(entry.display_model) ?? 0) + 1);
  }
  for (const entry of entries) {
    if (labels.has(entry)) continue;
    if ((stillTied.get(entry.display_model) ?? 0) > 1) labels.set(entry, entry.slug);
  }
  return labels;
}

function companyOf(model) {
  const prefix = model.match(/^[a-z]+/)?.[0];
  const company = COMPANIES[prefix];
  if (!company) throw new Error(`No company mapped for model ${model}`);
  return company;
}

function stripRows(entry) {
  const tokens = stripToken(entry);
  return [
    ["TIME", show(entry.duration_ms, formatDuration)],
    [tokens.label, show(tokens.value, formatCount)],
    ["THINK", show(entry.thinking_tokens, formatCount)],
    ["COST", show(entry.cost_usd, formatCost)],
  ];
}

function stripToken(entry) {
  const total = entry.output_tokens == null && entry.tokens_total != null;
  return {
    label: total ? "TOTAL" : "OUT",
    value: total ? entry.tokens_total : entry.output_tokens,
  };
}

function detailRows(entry) {
  return [
    ["HARNESS", entry.harness],
    ["PHASE", show(entry.phase, String)],
    ["RUN", show(entry.run, String)],
    ["EFFORT", show(entry.effort, String)],
    ["REQUESTED", show(entry.requested, String)],
    ["ACTUAL", show(entry.actual, String)],
    ["WALL TIME", show(entry.duration_ms, formatDurationLong)],
    ["INPUT", show(entry.input_tokens, formatFull)],
    ...(entry.cached_input_tokens == null ? [] : [["CACHED", formatFull(entry.cached_input_tokens)]]),
    ...(entry.cache_write_tokens == null ? [] : [["CACHE WRITE", formatFull(entry.cache_write_tokens)]]),
    ["OUTPUT", show(entry.output_tokens, formatFull)],
    ["THINKING", show(entry.thinking_tokens, formatFull)],
    ["TOTAL", show(entry.tokens_total, formatFull)],
    ["COST", show(entry.cost_usd, formatCost)],
    ["HTML SIZE", null, "size"],
  ];
}

function statList(className, rows) {
  const list = h("dl", className);
  for (const [label, value, field] of rows) {
    const cell = h("div", "cab-stat");
    const dd = h("dd", value == null ? "is-empty" : "", value ?? "—");
    if (field) dd.dataset.field = field;
    cell.append(h("dt", "", label), dd);
    list.append(cell);
  }
  return list;
}

async function loadSizes() {
  await Promise.all(
    cards.map(async (card) => {
      const response = await fetch(entryUrl(card.entry), { method: "HEAD" });
      if (!response.ok) throw new Error(`${card.entry.slug}: HTTP ${response.status}`);
      const bytes = Number(response.headers.get("content-length"));
      if (!Number.isFinite(bytes)) throw new Error(`${card.entry.slug}: no content-length`);
      card.setSize(bytes);
    })
  );
}

function buildModelFilter() {
  const counts = new Map();
  for (const card of cards) counts.set(card.model, (counts.get(card.model) ?? 0) + 1);

  const groups = new Map();
  for (const model of [...counts.keys()].sort(byName)) {
    const company = companyOf(model);
    if (!groups.has(company)) groups.set(company, []);
    groups.get(company).push(model);
  }

  for (const company of [...groups.keys()].sort(byName)) {
    const group = h("fieldset", "models-group");
    group.append(h("legend", "models-company", company));
    for (const model of groups.get(company)) {
      const box = h("input");
      box.type = "checkbox";
      box.value = model;
      const option = h("label", "models-option");
      option.append(box, h("span", "models-name", model), h("span", "models-count", String(counts.get(model))));
      group.append(option);
    }
    ui.modelsList.append(group);
  }
}

function setModelsOpen(open) {
  ui.modelsPanel.hidden = !open;
  ui.modelsToggle.setAttribute("aria-expanded", String(open));
  if (!open) return;
  const top = ui.modelsPanel.getBoundingClientRect().top;
  ui.modelsPanel.style.maxHeight = `${Math.max(160, window.innerHeight - top - 12)}px`;
}

function bindEvents() {
  ui.search.addEventListener("input", () => {
    state.query = ui.search.value;
    applyFilters();
  });

  ui.modelsToggle.addEventListener("click", () => setModelsOpen(ui.modelsPanel.hidden));

  ui.modelsList.addEventListener("change", (event) => {
    const box = event.target;
    if (box.checked) state.models.add(box.value);
    else state.models.delete(box.value);
    applyFilters();
  });

  ui.modelsClear.addEventListener("click", () => {
    state.models.clear();
    applyFilters();
  });

  ui.models.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || ui.modelsPanel.hidden) return;
    setModelsOpen(false);
    ui.modelsToggle.focus();
  });

  document.addEventListener("click", (event) => {
    if (!ui.models.contains(event.target)) setModelsOpen(false);
  });

  bindRadioGroup(ui.sortKeys, ui.sortKeyButtons, (button) => {
    state.sort = button.dataset.sort;
    applyFilters();
  });

  bindRadioGroup(ui.sortDir, ui.sortDirButtons, (button) => {
    state.descending = button.dataset.order === "desc";
    applyFilters();
  });

  document.querySelector(".game-over-reset").addEventListener("click", () => {
    ui.search.value = "";
    state.query = "";
    state.models.clear();
    applyFilters();
    ui.search.focus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.target.closest("input, textarea, [contenteditable]")) return;
    event.preventDefault();
    ui.search.focus();
  });
}

function applyFilters() {
  const terms = state.query.toLowerCase().split(/\s+/).filter(Boolean);
  const ordered = sortedCards();
  orderGrid(ordered);

  let shown = 0;
  for (const card of ordered) {
    const visible = cardMatches(card, terms);
    card.el.hidden = !visible;
    if (visible) shown += 1;
  }

  syncModels();
  syncSort();
  ui.count.textContent = `${shown} / ${cards.length}`;
  ui.gameOver.hidden = shown > 0;
  schedulePreviews();
}

function orderGrid(ordered) {
  const kids = ui.grid.children;
  if (ordered.length === kids.length && ordered.every((card, i) => card.el === kids[i])) return;
  ui.grid.append(...ordered.map((card) => card.el));
}

function cardMatches(card, terms) {
  const modelOk = !state.models.size || state.models.has(card.model);
  return modelOk && terms.every((term) => card.haystack.includes(term));
}

function syncModels() {
  for (const box of ui.modelBoxes) box.checked = state.models.has(box.value);
  const picked = [...state.models];
  if (!picked.length) ui.modelsValue.textContent = "All";
  else if (picked.length === 1) ui.modelsValue.textContent = picked[0];
  else ui.modelsValue.textContent = `${picked.length} models`;
  ui.modelsToggle.classList.toggle("is-active", picked.length > 0);
  ui.modelsClear.disabled = !picked.length;
}

function sortedCards() {
  if (state.sort === "default") return cards;
  const valueOf = SORT_VALUE[state.sort];
  const direction = state.descending ? -1 : 1;
  return cards
    .map((card, index) => ({ card, index, value: valueOf(card.entry) }))
    .sort((a, b) => compareMetric(a, b, direction))
    .map((item) => item.card);
}

function compareMetric(a, b, direction) {
  const aMissing = a.value == null;
  const bMissing = b.value == null;
  if (aMissing || bMissing) {
    if (aMissing && bMissing) return a.index - b.index;
    return aMissing ? 1 : -1;
  }
  if (a.value !== b.value) return (a.value - b.value) * direction;
  return a.index - b.index;
}

function syncSort() {
  for (const button of ui.sortKeyButtons) markRadio(button, button.dataset.sort === state.sort);
  if (state.sort === "default") {
    ui.sortDir.hidden = true;
    return;
  }
  const labels = SORT_DIR[state.sort];
  for (const button of ui.sortDirButtons) {
    const descending = button.dataset.order === "desc";
    const [text, name] = labels[descending ? 1 : 0];
    button.textContent = text;
    button.setAttribute("aria-label", name);
    markRadio(button, descending === state.descending);
  }
  ui.sortDir.hidden = false;
}

function markRadio(button, selected) {
  button.setAttribute("aria-checked", String(selected));
  button.tabIndex = selected ? 0 : -1;
}

function bindRadioGroup(group, buttons, onChoose) {
  group.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || !buttons.includes(button)) return;
    onChoose(button);
  });

  group.addEventListener("keydown", (event) => {
    let delta = 0;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") delta = 1;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") delta = -1;
    if (!delta) return;
    const index = buttons.indexOf(document.activeElement);
    if (index < 0) return;
    event.preventDefault();
    const button = buttons[(index + delta + buttons.length) % buttons.length];
    onChoose(button);
    button.focus();
  });
}

function holdPreview(screen) {
  hoveredScreen = screen;
  schedulePreviews();
}

function releasePreview(screen) {
  if (hoveredScreen !== screen) return;
  hoveredScreen = null;
  schedulePreviews();
}

function schedulePreviews() {
  if (scrolling) {
    for (const screen of mountedScreens) freezePreview(screen);
    return;
  }

  const live = new Set(reducedMotion.matches ? [] : liveScreens());
  for (const screen of [...mountedScreens]) {
    if (!visibleScreens.has(screen) || screen.closest(".cab").hidden) unmountPreview(screen);
  }
  for (const screen of visibleScreens.keys()) {
    if (screen.closest(".cab").hidden) continue;
    mountPreview(screen);
    if (live.has(screen)) thawPreview(screen);
    else freezePreview(screen);
  }
}

function liveScreens() {
  const ranked = [...visibleScreens.entries()]
    .filter(([screen]) => !screen.closest(".cab").hidden)
    .sort((a, b) => b[1] - a[1]);
  const picked = [];
  const hoveredHidden = !hoveredScreen || hoveredScreen.closest(".cab").hidden || !visibleScreens.has(hoveredScreen);
  if (!hoveredHidden) picked.push(hoveredScreen);
  for (const [screen] of ranked) {
    if (picked.length >= MAX_LIVE) break;
    if (!picked.includes(screen)) picked.push(screen);
  }
  return picked;
}

function mountPreview(screen) {
  if (screen.querySelector("iframe")) return;
  const frame = document.createElement("iframe");
  frame.src = screen.dataset.src;
  frame.title = screen.dataset.title;
  frame.tabIndex = -1;
  frame.setAttribute("scrolling", "no");
  frame.addEventListener(
    "load",
    () => {
      frame.classList.add("is-live");
      installPause(frame);
      if (scrolling || reducedMotion.matches || !liveScreens().includes(screen)) freezePreview(screen);
    },
    { once: true }
  );
  mountedScreens.add(screen);
  screen.prepend(frame);
}

function unmountPreview(screen) {
  mountedScreens.delete(screen);
  screen.querySelector("iframe")?.remove();
}

function installPause(frame) {
  const win = frame.contentWindow;
  if (win.__galleryResume) return;
  const native = win.requestAnimationFrame.bind(win);
  const queue = [];
  const root = win.document.documentElement;
  const style = win.document.createElement("style");
  style.textContent = "html.gallery-paused, html.gallery-paused * { animation-play-state: paused !important; }";
  root.append(style);
  win.__galleryPaused = false;
  win.requestAnimationFrame = (callback) => {
    if (!win.__galleryPaused) return native(callback);
    queue.push(callback);
    return 0;
  };
  win.__galleryResume = () => {
    if (!win.__galleryPaused) return;
    win.__galleryPaused = false;
    root.classList.remove("gallery-paused");
    for (const callback of queue.splice(0)) native(callback);
  };
  win.__galleryPause = () => {
    win.__galleryPaused = true;
    root.classList.add("gallery-paused");
  };
}

function freezePreview(screen) {
  screen.querySelector("iframe")?.contentWindow?.__galleryPause?.();
}

function thawPreview(screen) {
  screen.querySelector("iframe")?.contentWindow?.__galleryResume?.();
}

function formatDuration(ms) {
  const seconds = ms / 1000;
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = seconds / 60;
  return minutes < 10 ? `${minutes.toFixed(1)}m` : `${Math.round(minutes)}m`;
}

function formatDurationLong(ms) {
  const total = Math.round(ms / 1000);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return minutes ? `${minutes}m ${String(seconds).padStart(2, "0")}s` : `${seconds}s`;
}

function formatCount(n) {
  if (n < 1000) return String(n);
  return n < 10000 ? `${(n / 1000).toFixed(1)}k` : `${Math.round(n / 1000)}k`;
}

function formatFull(n) {
  return n.toLocaleString("en-US");
}

function formatCost(usd) {
  return `$${usd.toFixed(2)}`;
}

function formatBytes(bytes) {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function show(value, format) {
  return value == null ? null : format(value);
}

function entryUrl(entry) {
  return `./entries/${entry.slug}.html`;
}

function ghostIcon() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", "#ghost");
  svg.append(use);
  return svg;
}

function h(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text) el.textContent = text;
  return el;
}
