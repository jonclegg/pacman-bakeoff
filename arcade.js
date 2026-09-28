const PREVIEW_SIZE = 760;
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

const previewObserver = new IntersectionObserver(
  (records) => {
    for (const record of records) {
      if (record.isIntersecting) mountPreview(record.target);
      else unmountPreview(record.target);
    }
  },
  { rootMargin: "300px 0px" }
);

const scaleObserver = new ResizeObserver((records) => {
  for (const record of records) {
    record.target.style.setProperty("--s", record.contentRect.width / PREVIEW_SIZE);
  }
});

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

  cards = entries.map((entry, i) => buildCard(entry, i, colors.get(entry.harness)));
  ui.grid.append(...cards.map((card) => card.el));
  buildModelFilter();
  ui.modelBoxes = [...ui.modelsList.querySelectorAll("input")];
  bindEvents();
  applyFilters();
  await loadSizes();
}

function buildCard(entry, index, color) {
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
  link.append(h("span", "visually-hidden", ` (${entry.harness}, opens in a new tab)`));
  const title = h("h3", "cab-model");
  title.append(link);

  const body = h("div", "cab-body");
  body.append(top, title);

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
  previewObserver.observe(screen);
  scaleObserver.observe(screen);

  const haystack = [entry.display_model, entry.requested, entry.actual, entry.harness, entry.slug, entry.run, entry.note]
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
  const name = entry.display_model.split("/").pop();
  const effort = `-${entry.effort}`;
  return entry.effort && name.endsWith(effort) ? name.slice(0, -effort.length) : name;
}

function companyOf(model) {
  const company = COMPANIES[model.match(/^[a-z]+/)[0]];
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
      const response = await fetch(entryUrl(card.entry));
      if (!response.ok) throw new Error(`${card.entry.slug}: HTTP ${response.status}`);
      card.setSize((await response.blob()).size);
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
}

function bindEvents() {
  ui.search.addEventListener("input", () => {
    state.query = ui.search.value;
    applyFilters();
  });

  ui.modelsToggle.addEventListener("click", () => setModelsOpen(ui.modelsPanel.hidden));

  ui.modelsList.addEventListener("change", (event) => {
    toggle(state.models, event.target.value);
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
  ui.grid.append(...ordered.map((card) => card.el));

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
  if (aMissing && bMissing) return a.index - b.index;
  if (aMissing || bMissing) return aMissing ? direction : -direction;
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

function mountPreview(screen) {
  if (screen.querySelector("iframe")) return;
  const frame = document.createElement("iframe");
  frame.src = screen.dataset.src;
  frame.title = screen.dataset.title;
  frame.tabIndex = -1;
  frame.setAttribute("scrolling", "no");
  frame.addEventListener("load", () => frame.classList.add("is-live"), { once: true });
  screen.prepend(frame);
}

function unmountPreview(screen) {
  screen.querySelector("iframe")?.remove();
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

function toggle(set, value) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
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
