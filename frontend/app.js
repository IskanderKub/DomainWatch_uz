const API_BASE = "/api/v1";

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
      detail = body.detail || detail;
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
  return `${Math.round(ms)} мс`;
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
  const statusBadge = !hasChecks
    ? badge("нет данных", "neutral")
    : stats.uptime_percent >= 99.9
    ? badge("online", "ok")
    : stats.uptime_percent > 0
    ? badge("нестабильно", "warn")
    : badge("offline", "bad");

  const defacementBadge = hasChecks && stats.suspected_defacements > 0
    ? `<button class="badge badge-bad badge-button" data-action="defacements" data-id="${domain.id}" data-name="${escapeHtml(domain.name)}">${stats.suspected_defacements} ${pluralRu(stats.suspected_defacements, "изменение", "изменения", "изменений")}</button>`
    : badge("нет", "neutral");

  // data-label is shown as the field name when the table collapses into cards on narrow screens
  return `
    <tr data-domain-id="${domain.id}">
      <td class="domain-cell">
        <div>${escapeHtml(domain.name)}</div>
        <div class="domain-url">${escapeHtml(domain.url)}</div>
      </td>
      <td data-label="Статус">${statusBadge}</td>
      <td data-label="Uptime">${hasChecks ? formatPercent(stats.uptime_percent) : "—"}</td>
      <td data-label="Ср. отклик">${hasChecks ? formatMs(stats.avg_response_time_ms) : "—"}</td>
      <td data-label="Изменения">${defacementBadge}</td>
      <td class="actions-cell">
        <div class="row-actions">
          <button class="small" data-action="check" data-id="${domain.id}">Проверить</button>
          <button class="small secondary" data-action="history" data-id="${domain.id}" data-name="${escapeHtml(domain.name)}">История</button>
          <button class="small danger" data-action="delete" data-id="${domain.id}">Удалить</button>
        </div>
      </td>
    </tr>
  `;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

async function onRowAction(event) {
  const button = event.currentTarget;
  const action = button.dataset.action;
  const id = button.dataset.id;

  if (action === "check") {
    button.disabled = true;
    try {
      await apiRequest(`/domains/${id}/checks`, { method: "POST" });
      showToast("Проверка выполнена");
      await loadDomains();
    } catch (err) {
      showToast(`Ошибка проверки: ${err.message}`, true);
    } finally {
      button.disabled = false;
    }
  }

  if (action === "delete") {
    if (!confirm("Удалить домен и всю историю проверок?")) return;
    try {
      await apiRequest(`/domains/${id}`, { method: "DELETE" });
      if (historyState.domainId === id) closeHistory();
      showToast("Домен удалён");
      await loadDomains();
    } catch (err) {
      showToast(`Ошибка удаления: ${err.message}`, true);
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
  historyTitle.textContent = `История проверок — ${domainName}`;
  historyPanel.hidden = false;
  historyState.domainId = domainId;
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

  calendarMonth.textContent = month.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
  calendarGrid.innerHTML = `<p class="empty">Загрузка…</p>`;
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
    calendarGrid.innerHTML = `<p class="error">Ошибка загрузки: ${escapeHtml(err.message)}</p>`;
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

    const status = checks.some((c) => c.is_suspected_defacement)
      ? "bad"
      : checks.some((c) => !c.is_available)
      ? "warn"
      : "ok";
    classes.push(`status-${status}`);
    cells.push(`
      <button class="${classes.join(" ")}" data-day="${key}" title="${checks.length} проверок">
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
    dayEmpty.textContent = "В этом месяце проверок не было";
    dayEmpty.hidden = false;
    return;
  }

  const [y, m, d] = selectedDay.split("-").map(Number);
  dayTitle.textContent = new Date(y, m - 1, d).toLocaleDateString("ru-RU", {
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
  const time = new Date(check.checked_at).toLocaleTimeString("ru-RU");
  const availableBadge = check.is_available ? badge("да", "ok") : badge("нет", "bad");
  const defacementBadge = !check.is_suspected_defacement
    ? badge("нет", "neutral")
    : defacement
    ? `<button class="badge badge-bad badge-button" data-toggle-diff="${check.id}">изменение ▾</button>`
    : badge("изменение", "bad");
  const similarity = check.similarity_ratio !== null ? check.similarity_ratio.toFixed(2) : "—";

  return `
    <tr>
      <td>${time}</td>
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
  defacementsBody.innerHTML = `<p class="empty">Загрузка…</p>`;

  try {
    const defacements = await apiRequest(`/domains/${domainId}/defacements`);
    // ignore a response for a domain the user already navigated away from
    if (domainId !== historyState.domainId) return;
    if (defacements.length === 0) {
      defacementsBody.innerHTML = `<p class="empty">Изменений нет</p>`;
      return;
    }
    defacementsBody.innerHTML = defacements.map(renderDefacement).join("");
  } catch (err) {
    if (domainId !== historyState.domainId) return;
    defacementsBody.innerHTML = `<p class="error">Ошибка загрузки: ${escapeHtml(err.message)}</p>`;
  }
}

async function loadOutages(domainId) {
  outagesTable.hidden = true;
  outagesEmpty.textContent = "Загрузка…";
  outagesEmpty.hidden = false;

  try {
    const outages = await apiRequest(`/domains/${domainId}/checks?is_available=false&limit=10000`);
    // ignore a response for a domain the user already navigated away from
    if (domainId !== historyState.domainId) return;
    if (outages.length === 0) {
      outagesEmpty.textContent = "Сайт ни разу не был недоступен";
      return;
    }
    outagesEmpty.hidden = true;
    outagesTable.hidden = false;
    outagesBody.innerHTML = outages.map(renderOutageRow).join("");
  } catch (err) {
    if (domainId !== historyState.domainId) return;
    outagesEmpty.textContent = `Ошибка загрузки: ${err.message}`;
  }
}

function renderOutageRow(check) {
  const time = new Date(check.checked_at).toLocaleString("ru-RU");
  // a failed request has no status code but an error message; a 4xx/5xx has the code only
  const reason = check.error_message
    ? escapeHtml(check.error_message)
    : check.status_code
    ? `Сервер ответил ошибкой ${check.status_code}`
    : "—";

  return `
    <tr>
      <td>${time}</td>
      <td>${check.status_code ? badge(check.status_code, "bad") : "—"}</td>
      <td class="outage-reason">${reason}</td>
    </tr>
  `;
}

function renderDefacement(item) {
  const time = new Date(item.checked_at).toLocaleString("ru-RU");
  const similarity = item.similarity_ratio !== null ? item.similarity_ratio.toFixed(2) : "—";
  const diff = item.diff === null
    ? `<p class="empty">Снимки страницы недоступны — изменения показать нельзя</p>`
    : `<div class="diff">${item.diff.map(renderDiffSegment).join(" ")}</div>`;

  return `
    <div class="defacement">
      <div class="defacement-meta">
        <span>Добавлено: <strong>${time}</strong></span>
        <span>Схожесть: <strong>${similarity}</strong></span>
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
    showToast("Домен добавлен");
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

loadDomains().catch((err) => showToast(`Не удалось загрузить домены: ${err.message}`, true));
