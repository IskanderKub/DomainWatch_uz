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
    ? badge(`${stats.suspected_defacements} подозрений`, "bad")
    : badge("нет", "neutral");

  return `
    <tr data-domain-id="${domain.id}">
      <td>
        <div>${escapeHtml(domain.name)}</div>
        <div style="color: var(--text-dim); font-size: 12px;">${escapeHtml(domain.url)}</div>
      </td>
      <td>${statusBadge}</td>
      <td>${hasChecks ? formatPercent(stats.uptime_percent) : "—"}</td>
      <td>${hasChecks ? formatMs(stats.avg_response_time_ms) : "—"}</td>
      <td>${defacementBadge}</td>
      <td>
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
      showToast("Домен удалён");
      await loadDomains();
    } catch (err) {
      showToast(`Ошибка удаления: ${err.message}`, true);
    }
  }

  if (action === "history") {
    await openHistory(id, button.dataset.name);
  }
}

async function openHistory(domainId, domainName) {
  historyTitle.textContent = `История проверок — ${domainName}`;
  historyPanel.hidden = false;
  historyBody.innerHTML = `<tr><td colspan="6">Загрузка…</td></tr>`;

  try {
    const checks = await apiRequest(`/domains/${domainId}/checks`);
    if (checks.length === 0) {
      historyBody.innerHTML = `<tr><td colspan="6">Проверок пока не было</td></tr>`;
      return;
    }
    historyBody.innerHTML = checks.map(renderHistoryRow).join("");
  } catch (err) {
    historyBody.innerHTML = `<tr><td colspan="6">Ошибка загрузки: ${escapeHtml(err.message)}</td></tr>`;
  }
}

function renderHistoryRow(check) {
  const time = new Date(check.checked_at).toLocaleString("ru-RU");
  const availableBadge = check.is_available ? badge("да", "ok") : badge("нет", "bad");
  const defacementBadge = check.is_suspected_defacement
    ? badge("подозрение", "bad")
    : badge("нет", "neutral");
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
  `;
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
historyClose.addEventListener("click", () => {
  historyPanel.hidden = true;
});

loadDomains().catch((err) => showToast(`Не удалось загрузить домены: ${err.message}`, true));
