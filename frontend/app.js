const API_BASE = "/api/v1";

// UI strings per language; functions take values that are interpolated into the text
const I18N = {
  ru: {
    locale: "ru-RU",
    subtitle: "Мониторинг доступности и детекция подмены контента",
    addDomain: "Добавить домен",
    add: "Добавить",
    domains: "Домены",
    refresh: "Обновить",
    domainsEmpty: "Пока нет ни одного домена — добавьте первый выше.",
    colDomain: "Домен",
    colStatus: "Статус",
    colUptime: "Uptime",
    colAvgResponse: "Ср. отклик",
    colChanges: "Изменения",
    colTime: "Время",
    colCode: "Код",
    colReason: "Причина",
    colAvailable: "Доступен",
    colResponseMs: "Отклик, мс",
    colSimilarity: "Схожесть",
    history: "История проверок",
    historyFor: (name) => `История проверок — ${name}`,
    close: "Закрыть",
    tabCalendar: "Календарь",
    tabChanges: "Все изменения",
    tabOutages: "Были недоступны",
    removed: "удалено",
    added: "добавлено",
    prevMonth: "Предыдущий месяц",
    nextMonth: "Следующий месяц",
    thisMonth: "Этот месяц",
    weekdays: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    legendOk: "все проверки ок",
    legendWarn: "были недоступности",
    legendBad: "были изменения",
    ms: (value) => `${value} мс`,
    archive: "архив",
    noData: "нет данных",
    unstable: "нестабильно",
    yes: "да",
    no: "нет",
    changesCount: (n) => `${n} ${pluralRu(n, "изменение", "изменения", "изменений")}`,
    change: "изменение",
    check: "Проверить",
    historyBtn: "История",
    delete: "Удалить",
    checkDone: "Проверка выполнена",
    checkError: (msg) => `Ошибка проверки: ${msg}`,
    confirmDelete: "Удалить домен и всю историю проверок?",
    domainDeleted: "Домен удалён",
    deleteError: (msg) => `Ошибка удаления: ${msg}`,
    domainAdded: "Домен добавлен",
    loading: "Загрузка…",
    loadError: (msg) => `Ошибка загрузки: ${msg}`,
    checksCount: (n) => `${n} ${pluralRu(n, "проверка", "проверки", "проверок")}`,
    noChecksThisMonth: "В этом месяце проверок не было",
    noChanges: "Изменений нет",
    neverDown: "Сайт ни разу не был недоступен",
    serverError: (code) => `Сервер ответил ошибкой ${code}`,
    snapshotsUnavailable: "Снимки страницы недоступны — изменения показать нельзя",
    detectedAt: "Добавлено",
    similarity: "Схожесть",
    domainsLoadError: (msg) => `Не удалось загрузить домены: ${msg}`,
  },
  en: {
    locale: "en-GB",
    subtitle: "Availability monitoring and content tampering detection",
    addDomain: "Add domain",
    add: "Add",
    domains: "Domains",
    refresh: "Refresh",
    domainsEmpty: "No domains yet — add the first one above.",
    colDomain: "Domain",
    colStatus: "Status",
    colUptime: "Uptime",
    colAvgResponse: "Avg. response",
    colChanges: "Changes",
    colTime: "Time",
    colCode: "Code",
    colReason: "Reason",
    colAvailable: "Available",
    colResponseMs: "Response, ms",
    colSimilarity: "Similarity",
    history: "Check history",
    historyFor: (name) => `Check history — ${name}`,
    close: "Close",
    tabCalendar: "Calendar",
    tabChanges: "All changes",
    tabOutages: "Outages",
    removed: "removed",
    added: "added",
    prevMonth: "Previous month",
    nextMonth: "Next month",
    thisMonth: "This month",
    weekdays: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    legendOk: "all checks ok",
    legendWarn: "had outages",
    legendBad: "had changes",
    ms: (value) => `${value} ms`,
    archive: "archive",
    noData: "no data",
    unstable: "unstable",
    yes: "yes",
    no: "no",
    changesCount: (n) => `${n} ${n === 1 ? "change" : "changes"}`,
    change: "change",
    check: "Check",
    historyBtn: "History",
    delete: "Delete",
    checkDone: "Check completed",
    checkError: (msg) => `Check failed: ${msg}`,
    confirmDelete: "Delete the domain and its whole check history?",
    domainDeleted: "Domain deleted",
    deleteError: (msg) => `Delete failed: ${msg}`,
    domainAdded: "Domain added",
    loading: "Loading…",
    loadError: (msg) => `Failed to load: ${msg}`,
    checksCount: (n) => `${n} ${n === 1 ? "check" : "checks"}`,
    noChecksThisMonth: "No checks this month",
    noChanges: "No changes",
    neverDown: "The site has never been unavailable",
    serverError: (code) => `Server responded with error ${code}`,
    snapshotsUnavailable: "Page snapshots are unavailable — changes can't be shown",
    detectedAt: "Detected",
    similarity: "Similarity",
    domainsLoadError: (msg) => `Failed to load domains: ${msg}`,
  },
};

const LANG_STORAGE_KEY = "domainwatch.lang";

function loadSavedLang() {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    return saved in I18N ? saved : "ru";
  } catch {
    // storage can be blocked (private mode etc.) - fall back to the default
    return "ru";
  }
}

let currentLang = loadSavedLang();

function t(key, ...args) {
  const value = I18N[currentLang][key];
  return typeof value === "function" ? value(...args) : value;
}

const domainsBody = document.getElementById("domains-body");
const domainsTable = document.getElementById("domains-table");
const domainsEmpty = document.getElementById("domains-empty");
const addForm = document.getElementById("add-domain-form");
const addError = document.getElementById("add-error");
const refreshBtn = document.getElementById("refresh-btn");
const historyPanel = document.getElementById("history-panel");
const historyTitle = document.getElementById("history-title");
const historyBody = document.getElementById("history-body");
const historyClose = document.getElementById("history-close");
const historyTable = document.getElementById("history-table");
const calendarGrid = document.getElementById("calendar-grid");
const calendarMonth = document.getElementById("calendar-month");
const calendarPrev = document.getElementById("calendar-prev");
const calendarNext = document.getElementById("calendar-next");
const calendarToday = document.getElementById("calendar-today");
const dayTitle = document.getElementById("day-title");
const dayEmpty = document.getElementById("day-empty");
const defacementsBody = document.getElementById("defacements-body");
const historyTabs = document.querySelectorAll(".tabs [data-tab]");
const outagesTable = document.getElementById("outages-table");
const outagesBody = document.getElementById("outages-body");
const outagesEmpty = document.getElementById("outages-empty");
const toast = document.getElementById("toast");
const langButtons = document.querySelectorAll(".lang-switch [data-lang]");

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.hidden = false;
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    toast.hidden = true;
  }, 3500);
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      // FastAPI validation errors (422) carry a list of {loc, msg, ...} objects
      detail = Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join("; ")
        : body.detail || detail;
    } catch {
      // response had no JSON body - keep statusText
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function formatMs(ms) {
  if (ms === null || ms === undefined) return "—";
  return t("ms", Math.round(ms));
}

function formatPercent(value) {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)}%`;
}

// Russian noun plural: 1 изменение, 2 изменения, 5 изменений
function pluralRu(n, one, few, many) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

function badge(text, kind) {
  return `<span class="badge badge-${kind}">${text}</span>`;
}

// marks rows imported from the Wayback Machine rather than checked by DomainWatch
function archiveMark(item) {
  return item.source === "archive" ? ` ${badge(t("archive"), "neutral")}` : "";
}

async function loadDomains() {
  const domains = await apiRequest("/domains");

  if (domains.length === 0) {
    domainsTable.hidden = true;
    domainsEmpty.hidden = false;
    return;
  }
  domainsEmpty.hidden = true;
  domainsTable.hidden = false;

  const rows = await Promise.all(
    domains.map(async (domain) => {
      let stats = null;
      try {
        stats = await apiRequest(`/domains/${domain.id}/stats`);
      } catch {
        // stats endpoint failing shouldn't hide the domain row itself
      }
      return { domain, stats };
    })
  );

  domainsBody.innerHTML = rows.map(({ domain, stats }) => renderRow(domain, stats)).join("");

  domainsBody.querySelectorAll("[data-action]").forEach((el) => {
    el.addEventListener("click", onRowAction);
  });
}

function renderRow(domain, stats) {
  const hasChecks = stats && stats.total_checks > 0;
  // current state comes from the latest check; uptime only decides whether an
  // online domain has been flaky recently
  const statusBadge = !hasChecks
    ? badge(t("noData"), "neutral")
    : !stats.is_available_now
    ? badge("offline", "bad")
    : stats.uptime_percent >= 99.9
    ? badge("online", "ok")
    : badge(t("unstable"), "warn");

  // changes also count the ones imported from the archive, so they can exist before
  // the first live check
  const defacementBadge = stats && stats.global_changes > 0
    ? `<button class="badge badge-bad badge-button" data-action="defacements" data-id="${domain.id}" data-name="${escapeHtml(domain.name)}">${t("changesCount", stats.global_changes)}</button>`
    : badge(t("no"), "neutral");

  // data-label is shown as the field name when the table collapses into cards on narrow screens
  return `
    <tr data-domain-id="${domain.id}">
      <td class="domain-cell">
        <div>${escapeHtml(domain.name)}</div>
        <div class="domain-url">${escapeHtml(domain.url)}</div>
      </td>
      <td data-label="${t("colStatus")}">${statusBadge}</td>
      <td data-label="${t("colUptime")}">${hasChecks ? formatPercent(stats.uptime_percent) : "—"}</td>
      <td data-label="${t("colAvgResponse")}">${hasChecks ? formatMs(stats.avg_response_time_ms) : "—"}</td>
      <td data-label="${t("colChanges")}">${defacementBadge}</td>
      <td class="actions-cell">
        <div class="row-actions">
          <button class="small" data-action="check" data-id="${domain.id}">${t("check")}</button>
          <button class="small secondary" data-action="history" data-id="${domain.id}" data-name="${escapeHtml(domain.name)}">${t("historyBtn")}</button>
          <button class="small danger" data-action="delete" data-id="${domain.id}">${t("delete")}</button>
        </div>
      </td>
    </tr>
  `;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  // innerHTML serialisation of a text node escapes & < > but NOT quotes, and this
  // output is interpolated into attributes (data-name on the badge and the history
  // button). A quote in a domain name would close the attribute early and let the
  // rest of the name become real markup - an onmouseover= that fires for anyone
  // looking at the dashboard. Quotes are escaped here so both uses are safe.
  return div.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

async function onRowAction(event) {
  const button = event.currentTarget;
  const action = button.dataset.action;
  const id = button.dataset.id;

  if (action === "check") {
    button.disabled = true;
    try {
      await apiRequest(`/domains/${id}/checks`, { method: "POST" });
      showToast(t("checkDone"));
      await loadDomains();
    } catch (err) {
      showToast(t("checkError", err.message), true);
    } finally {
      button.disabled = false;
    }
  }

  if (action === "delete") {
    if (!confirm(t("confirmDelete"))) return;
    try {
      await apiRequest(`/domains/${id}`, { method: "DELETE" });
      if (historyState.domainId === id) closeHistory();
      showToast(t("domainDeleted"));
      await loadDomains();
    } catch (err) {
      showToast(t("deleteError", err.message), true);
    }
  }

  if (action === "history") {
    await openHistory(id, button.dataset.name);
  }

  if (action === "defacements") {
    await openHistory(id, button.dataset.name, "changes");
  }
}

// state of the history calendar: which domain/month is shown and which day is picked
const historyState = {
  domainId: null,
  domainName: null,
  month: null, // Date set to the 1st of the shown month, local time
  checksByDay: new Map(), // "YYYY-MM-DD" (local) -> checks, newest first
  defacementsByCheck: new Map(),
  selectedDay: null,
};

function dayKey(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// opens the history panel for one domain; both tabs (calendar and the full list
// of changes) always belong to that domain and are reloaded when switching domains
async function openHistory(domainId, domainName, tab = "calendar") {
  historyTitle.textContent = t("historyFor", domainName);
  historyPanel.hidden = false;
  historyState.domainId = domainId;
  historyState.domainName = domainName;
  showHistoryTab(tab);
  historyPanel.scrollIntoView({ behavior: "smooth" });
  await Promise.all([showCurrentMonth(), loadDefacements(domainId), loadOutages(domainId)]);
}

function closeHistory() {
  historyPanel.hidden = true;
  historyState.domainId = null;
}

function showHistoryTab(tab) {
  historyTabs.forEach((el) => el.classList.toggle("active", el.dataset.tab === tab));
  document.getElementById("tab-calendar").hidden = tab !== "calendar";
  document.getElementById("tab-changes").hidden = tab !== "changes";
  document.getElementById("tab-outages").hidden = tab !== "outages";
}

function showCurrentMonth() {
  const now = new Date();
  historyState.month = new Date(now.getFullYear(), now.getMonth(), 1);
  return loadHistoryMonth(dayKey(now));
}

async function loadHistoryMonth(preferredDay = null) {
  const { domainId, month } = historyState;
  const since = month.toISOString();
  const until = new Date(month.getFullYear(), month.getMonth() + 1, 1).toISOString();
  const range = `since=${encodeURIComponent(since)}&until=${encodeURIComponent(until)}&limit=10000`;

  calendarMonth.textContent = month.toLocaleDateString(t("locale"), { month: "long", year: "numeric" });
  calendarGrid.innerHTML = `<p class="empty">${t("loading")}</p>`;
  historyTable.hidden = true;
  dayEmpty.hidden = true;
  dayTitle.textContent = "";

  try {
    const [checks, defacements] = await Promise.all([
      apiRequest(`/domains/${domainId}/checks?${range}`),
      // diffs are a nice-to-have here - the calendar still renders without them
      apiRequest(`/domains/${domainId}/defacements?${range}`).catch(() => []),
    ]);
    // ignore a response for a month/domain the user already navigated away from
    if (domainId !== historyState.domainId || month !== historyState.month) return;

    historyState.checksByDay = new Map();
    for (const check of checks) {
      const key = dayKey(new Date(check.checked_at));
      if (!historyState.checksByDay.has(key)) historyState.checksByDay.set(key, []);
      historyState.checksByDay.get(key).push(check);
    }
    historyState.defacementsByCheck = new Map(defacements.map((item) => [item.check_id, item]));

    // open the preferred day if it has data, otherwise the latest day with checks
    const days = [...historyState.checksByDay.keys()].sort();
    historyState.selectedDay = historyState.checksByDay.has(preferredDay)
      ? preferredDay
      : days[days.length - 1] ?? null;

    renderCalendar();
    renderSelectedDay();
  } catch (err) {
    calendarGrid.innerHTML = `<p class="error">${t("loadError", escapeHtml(err.message))}</p>`;
  }
}

function renderCalendar() {
  const { month, checksByDay, selectedDay } = historyState;
  const today = dayKey(new Date());
  // Monday-first week: getDay() is 0 for Sunday
  const leadingBlanks = (month.getDay() + 6) % 7;
  const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();

  const cells = [];
  for (let i = 0; i < leadingBlanks; i++) cells.push(`<span class="calendar-day blank"></span>`);

  for (let day = 1; day <= daysInMonth; day++) {
    const key = dayKey(new Date(month.getFullYear(), month.getMonth(), day));
    const checks = checksByDay.get(key) || [];
    const classes = ["calendar-day"];
    if (key === today) classes.push("today");
    if (key === selectedDay) classes.push("selected");

    if (checks.length === 0) {
      classes.push("no-data");
      cells.push(`<button class="${classes.join(" ")}" disabled><span class="day-num">${day}</span></button>`);
      continue;
    }

    const status = checks.some((c) => c.has_global_changes)
      ? "bad"
      : checks.some((c) => !c.is_available)
      ? "warn"
      : "ok";
    classes.push(`status-${status}`);
    cells.push(`
      <button class="${classes.join(" ")}" data-day="${key}" title="${t("checksCount", checks.length)}">
        <span class="day-num">${day}</span>
        <span class="day-count">${checks.length}</span>
      </button>
    `);
  }

  calendarGrid.innerHTML = cells.join("");
  calendarGrid.querySelectorAll("[data-day]").forEach((el) => {
    el.addEventListener("click", () => {
      historyState.selectedDay = el.dataset.day;
      renderCalendar();
      renderSelectedDay();
    });
  });
}

function renderSelectedDay() {
  const { selectedDay, checksByDay, defacementsByCheck } = historyState;
  if (selectedDay === null) {
    dayTitle.textContent = "";
    historyTable.hidden = true;
    dayEmpty.textContent = t("noChecksThisMonth");
    dayEmpty.hidden = false;
    return;
  }

  const [y, m, d] = selectedDay.split("-").map(Number);
  dayTitle.textContent = new Date(y, m - 1, d).toLocaleDateString(t("locale"), {
    day: "numeric",
    month: "long",
    year: "numeric",
    weekday: "long",
  });
  dayEmpty.hidden = true;
  historyTable.hidden = false;

  const checks = checksByDay.get(selectedDay) || [];
  historyBody.innerHTML = checks
    .map((check) => renderHistoryRow(check, defacementsByCheck.get(check.id)))
    .join("");
  historyBody.querySelectorAll("[data-toggle-diff]").forEach((el) => {
    el.addEventListener("click", () => {
      const row = document.getElementById(`diff-row-${el.dataset.toggleDiff}`);
      row.hidden = !row.hidden;
    });
  });
}

function shiftHistoryMonth(delta) {
  const { month } = historyState;
  historyState.month = new Date(month.getFullYear(), month.getMonth() + delta, 1);
  loadHistoryMonth();
}

function renderHistoryRow(check, defacement) {
  const time = new Date(check.checked_at).toLocaleTimeString(t("locale"));
  const availableBadge = check.is_available ? badge(t("yes"), "ok") : badge(t("no"), "bad");
  const defacementBadge = !check.has_global_changes
    ? badge(t("no"), "neutral")
    : defacement
    ? `<button class="badge badge-bad badge-button" data-toggle-diff="${check.id}">${t("change")} ▾</button>`
    : badge(t("change"), "bad");
  const similarity = check.similarity_ratio !== null ? check.similarity_ratio.toFixed(2) : "—";

  return `
    <tr>
      <td>${time}${archiveMark(check)}</td>
      <td>${availableBadge}</td>
      <td>${check.status_code ?? "—"}</td>
      <td>${formatMs(check.response_time_ms)}</td>
      <td>${similarity}</td>
      <td>${defacementBadge}</td>
    </tr>
    ${defacement ? renderHistoryDiffRow(check.id, defacement) : ""}
  `;
}

function renderHistoryDiffRow(checkId, defacement) {
  return `
    <tr id="diff-row-${checkId}" class="diff-row" hidden>
      <td colspan="6">${renderDefacement(defacement)}</td>
    </tr>
  `;
}

async function loadDefacements(domainId) {
  defacementsBody.innerHTML = `<p class="empty">${t("loading")}</p>`;

  try {
    const defacements = await apiRequest(`/domains/${domainId}/defacements`);
    // ignore a response for a domain the user already navigated away from
    if (domainId !== historyState.domainId) return;
    if (defacements.length === 0) {
      defacementsBody.innerHTML = `<p class="empty">${t("noChanges")}</p>`;
      return;
    }
    defacementsBody.innerHTML = defacements.map(renderDefacement).join("");
  } catch (err) {
    if (domainId !== historyState.domainId) return;
    defacementsBody.innerHTML = `<p class="error">${t("loadError", escapeHtml(err.message))}</p>`;
  }
}

async function loadOutages(domainId) {
  outagesTable.hidden = true;
  outagesEmpty.textContent = t("loading");
  outagesEmpty.hidden = false;

  try {
    const outages = await apiRequest(`/domains/${domainId}/checks?is_available=false&limit=10000`);
    // ignore a response for a domain the user already navigated away from
    if (domainId !== historyState.domainId) return;
    if (outages.length === 0) {
      outagesEmpty.textContent = t("neverDown");
      return;
    }
    outagesEmpty.hidden = true;
    outagesTable.hidden = false;
    outagesBody.innerHTML = outages.map(renderOutageRow).join("");
  } catch (err) {
    if (domainId !== historyState.domainId) return;
    outagesEmpty.textContent = t("loadError", err.message);
  }
}

function renderOutageRow(check) {
  const time = new Date(check.checked_at).toLocaleString("ru-RU");
  // a failed request has no status code but an error message; a 4xx/5xx has the code only
  const reason = check.error_message
    ? escapeHtml(check.error_message)
    : check.status_code
    ? t("serverError", check.status_code)
    : "—";

  return `
    <tr>
      <td>${time}${archiveMark(check)}</td>
      <td>${check.status_code ? badge(check.status_code, "bad") : "—"}</td>
      <td class="outage-reason">${reason}</td>
    </tr>
  `;
}

function renderDefacement(item) {
  const time = new Date(item.checked_at).toLocaleString("ru-RU");
  const similarity = item.similarity_ratio !== null ? item.similarity_ratio.toFixed(2) : "—";
  const diff = item.diff === null
    ? `<p class="empty">${t("snapshotsUnavailable")}</p>`
    : `<div class="diff">${item.diff.map(renderDiffSegment).join(" ")}</div>`;

  return `
    <div class="defacement">
      <div class="defacement-meta">
        <span>${t("detectedAt")}: <strong>${time}</strong>${archiveMark(item)}</span>
        <span>${t("similarity")}: <strong>${similarity}</strong></span>
      </div>
      ${diff}
    </div>
  `;
}

function renderDiffSegment(segment) {
  const text = escapeHtml(segment.text);
  if (segment.op === "removed") return `<del class="diff-removed">${text}</del>`;
  if (segment.op === "added") return `<ins class="diff-added">${text}</ins>`;
  return `<span class="diff-equal">${text}</span>`;
}

addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  addError.hidden = true;

  const name = document.getElementById("domain-name").value.trim();
  const url = document.getElementById("domain-url").value.trim();

  try {
    await apiRequest("/domains", {
      method: "POST",
      body: JSON.stringify({ name, url }),
    });
    addForm.reset();
    showToast(t("domainAdded"));
    await loadDomains();
  } catch (err) {
    addError.textContent = err.message;
    addError.hidden = false;
  }
});

refreshBtn.addEventListener("click", () => loadDomains());
calendarPrev.addEventListener("click", () => shiftHistoryMonth(-1));
calendarNext.addEventListener("click", () => shiftHistoryMonth(1));
calendarToday.addEventListener("click", () => showCurrentMonth());
historyClose.addEventListener("click", closeHistory);

historyTabs.forEach((el) => {
  el.addEventListener("click", () => showHistoryTab(el.dataset.tab));
});

// fills the static markup from index.html with strings of the current language
function applyStaticTranslations() {
  document.documentElement.lang = currentLang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  document.getElementById("calendar-weekdays").innerHTML = t("weekdays")
    .map((day) => `<span>${day}</span>`)
    .join("");
  langButtons.forEach((el) => el.classList.toggle("active", el.dataset.lang === currentLang));
}

function setLanguage(lang) {
  if (lang === currentLang) return;
  currentLang = lang;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    // not persisted - the choice still applies to this page view
  }
  applyStaticTranslations();
  // dynamic parts are rendered from JS, so re-render whatever is on screen
  loadDomains().catch((err) => showToast(t("domainsLoadError", err.message), true));
  if (historyState.domainId !== null) {
    const { domainId, domainName, selectedDay } = historyState;
    historyTitle.textContent = t("historyFor", domainName);
    loadHistoryMonth(selectedDay);
    loadDefacements(domainId);
    loadOutages(domainId);
  }
}

langButtons.forEach((el) => {
  el.addEventListener("click", () => setLanguage(el.dataset.lang));
});

applyStaticTranslations();
loadDomains().catch((err) => showToast(t("domainsLoadError", err.message), true));
