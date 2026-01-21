// app/static/js/admin.js

// --------------------
// Session / header
// --------------------
async function loadMe() {
  try {
    const me = await api("/auth/me", { method: "GET" });
    const who = document.getElementById("whoami");
    if (who && me && me.authenticated) {
      who.textContent = `${me.email} · ${me.role}`;
    }
  } catch (_) {
    window.location.href = "/login";
  }
}

async function doLogout() {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch (_) {}
  window.location.href = "/login";
}

// --------------------
// Helpers
// --------------------
function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function badge(text, cls) {
  return `<span class="badge ${cls}">${escapeHtml(text)}</span>`;
}

function showToast(text, isError = false) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }

  el.textContent = text || "";
  el.classList.toggle("toast-error", isError);
  el.classList.add("show");

  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => el.classList.remove("show"), 2200);
}

// --------------------
// Nav highlight
// --------------------
function highlightNav() {
  const key = (window.__NAV_ACTIVE__ || "").trim();
  if (!key) return;

  document.querySelectorAll(".nav-item").forEach((a) => {
    a.classList.toggle("active", a.dataset.nav === key);
  });
}

// --------------------
// Users: filters
// --------------------
function buildUsersQuery() {
  const q = (document.getElementById("fQ")?.value || "").trim();
  const role = (document.getElementById("fRole")?.value || "").trim();
  const active = (document.getElementById("fActive")?.value || "").trim();
  const blocked = (document.getElementById("fBlocked")?.value || "").trim();

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (role) params.set("role", role);
  if (active) params.set("active", active);
  if (blocked) params.set("blocked", blocked);

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
// --------------------
// Dashboard
// --------------------
function statCard(title, value, hint = "") {
  const div = document.createElement("div");
  div.className = "stat";
  div.innerHTML = `
    <div class="stat-title">${escapeHtml(title)}</div>
    <div class="stat-value">${escapeHtml(String(value))}</div>
    ${hint ? `<div class="stat-hint muted">${escapeHtml(hint)}</div>` : ""}
  `;
  return div;
}

async function loadDashboard() {
  const wrap = document.getElementById("dashStats");
  if (!wrap) return;

  wrap.innerHTML = "Cargando…";

  try {
    // Llamadas en paralelo
    const [users, books, reqs, audit, sec] = await Promise.all([
      api("/api/admin/users", { method: "GET" }),
      api("/admin/books", { method: "GET" }),
      api("/api/admin/book-requests", { method: "GET" }),
      api("/admin/audit?per_page=1", { method: "GET" }),
      api("/admin/security-events?limit=1", { method: "GET" }),
    ]);

    const usersArr = Array.isArray(users) ? users : (users.items || []);
    const booksArr = Array.isArray(books) ? books : (books.items || books || []);
    const reqArr = Array.isArray(reqs) ? reqs : (reqs.items || []);

    const totalUsers = usersArr.length;
    const blockedUsers = usersArr.filter(u => !!u.is_blocked).length;

    const totalBooks = booksArr.length;
    const availableBooks = booksArr.filter(b => b.is_available !== false).length;

    const totalReq = reqArr.length;
    const pendingReq = reqArr.filter(r => (r.status || "").toLowerCase() === "pending").length;

    // audit viene paginado: {items, total, ...}
    const totalAudit = audit?.total ?? "—";

    // security-events es array
    const lastSec = Array.isArray(sec) && sec.length ? sec[0] : null;
    const lastSecTxt = lastSec
      ? `${lastSec.event_type || "event"} · ${lastSec.status_code || ""}`
      : "—";

    wrap.innerHTML = "";
    wrap.appendChild(statCard("Usuarios", totalUsers, `${blockedUsers} bloqueados`));
    wrap.appendChild(statCard("Libros", totalBooks, `${availableBooks} disponibles`));
    wrap.appendChild(statCard("Solicitudes", totalReq, `${pendingReq} pendientes`));
    wrap.appendChild(statCard("Auditoría", totalAudit, "Total registros"));
    wrap.appendChild(statCard("Último evento", lastSecTxt, "Seguridad"));
  } catch (err) {
    console.error(err);
    wrap.innerHTML = `<div class="muted">No se pudo cargar el dashboard.</div>`;
  }
}

// --------------------
// Users: list + actions
// --------------------
async function loadUsers() {
  const tbody = document.querySelector("#usersTable tbody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5">Cargando…</td></tr>`;

  try {
    const qs = buildUsersQuery();
    const res = await api(`/api/admin/users${qs}`, { method: "GET" });
    const users = Array.isArray(res) ? res : (res.items || []);

    if (!users.length) {
      tbody.innerHTML = `<tr><td colspan="5">Sin resultados</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    for (const u of users) tbody.appendChild(renderUserRow(u));
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="5">Error cargando usuarios</td></tr>`;
  }
}

function renderUserRow(u) {
  const isBlocked = !!u.is_blocked;
  const isActive = (u.is_active !== false);

  const statusHtml = isBlocked
    ? badge("Bloqueado", "badge-red")
    : (isActive ? badge("Activo", "badge-green") : badge("Inactivo", "badge-gray"));

  const roleHtml = badge(
    u.role || "—",
    `badge-role badge-${String(u.role || "").toLowerCase()}`
  );

  const tr = document.createElement("tr");
  tr.dataset.userId = String(u.id);

  tr.innerHTML = `
    <td>${u.id ?? "—"}</td>
    <td>${escapeHtml(u.email ?? "")}</td>
    <td class="cell-role">${roleHtml}</td>
    <td class="cell-status">${statusHtml}</td>
    <td class="cell-actions">
      <button class="btn btn-xs" type="button"
        data-action="toggle-block"
        data-id="${u.id}"
        data-blocked="${isBlocked ? "1" : "0"}">
        ${isBlocked ? "Desbloquear" : "Bloquear"}
      </button>
    </td>
  `;
  return tr;
}

async function toggleUserBlock(userId, isBlocked) {
  const next = !isBlocked;
  return api(`/api/admin/users/${userId}/block`, {
    method: "PATCH",
    body: JSON.stringify({ is_blocked: next }),
  });
}

function setRowBlockedState(tr, nextBlocked) {
  const btn = tr.querySelector('button[data-action="toggle-block"]');
  const statusCell = tr.querySelector(".cell-status");

  if (btn) {
    btn.dataset.blocked = nextBlocked ? "1" : "0";
    btn.textContent = nextBlocked ? "Desbloquear" : "Bloquear";
  }

  if (statusCell) {
    statusCell.innerHTML = nextBlocked
      ? badge("Bloqueado", "badge-red")
      : badge("Activo", "badge-green");
  }
}

function wireUsersActions() {
  const table = document.getElementById("usersTable");
  if (!table) return;

  table.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    if (action !== "toggle-block") return;

    const userId = Number(btn.dataset.id);
    if (!userId) return;

    const tr = btn.closest("tr");
    if (!tr) return;

    const isBlocked = btn.dataset.blocked === "1";
    const ok = confirm(isBlocked ? "¿Desbloquear este usuario?" : "¿Bloquear este usuario?");
    if (!ok) return;

    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Guardando…";

    try {
      const res = await toggleUserBlock(userId, isBlocked);
      const nextBlocked = !!res.is_blocked;

      setRowBlockedState(tr, nextBlocked);
      showToast(nextBlocked ? "Usuario bloqueado" : "Usuario desbloqueado", false);
    } catch (err) {
      console.error(err);
      showToast(err.message || "Error", true);
    } finally {
      btn.disabled = false;
      btn.textContent = oldText;
    }
  });
}

function wireUsersFilters() {
  const btnApply = document.getElementById("btnApplyFilters");
  const btnClear = document.getElementById("btnClearFilters");
  const fQ = document.getElementById("fQ");

  if (btnApply) btnApply.addEventListener("click", () => loadUsers());

  if (btnClear) {
    btnClear.addEventListener("click", () => {
      ["fQ", "fRole", "fActive", "fBlocked"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });
      loadUsers();
    });
  }

  if (fQ) {
    fQ.addEventListener("keydown", (e) => {
      if (e.key === "Enter") loadUsers();
    });
  }
}
// --------------------
// Requests: filters
// --------------------
function buildRequestsQuery() {
  const status = (document.getElementById("rStatus")?.value || "").trim();
  const bookId = (document.getElementById("rBookId")?.value || "").trim();
  const requesterId = (document.getElementById("rRequesterId")?.value || "").trim();

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (bookId) params.set("book_id", bookId);
  if (requesterId) params.set("requester_id", requesterId);

  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function badgeReqStatus(status) {
  const s = String(status || "").toLowerCase();
  if (s === "accepted") return badge("accepted", "badge-green");
  if (s === "rejected") return badge("rejected", "badge-red");
  if (s === "cancelled") return badge("cancelled", "badge-gray");
  return badge(s || "pending", "badge-gray");
}

// --------------------
// Requests: list + actions
// --------------------
async function loadRequests() {
  const tbody = document.querySelector("#requestsTable tbody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5">Cargando…</td></tr>`;

  try {
    const qs = buildRequestsQuery();
    const res = await api(`/api/admin/book-requests${qs}`, { method: "GET" });
    const items = Array.isArray(res) ? res : (res.items || []);

    if (!items.length) {
      tbody.innerHTML = `<tr><td colspan="5">Sin resultados</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    for (const r of items) tbody.appendChild(renderRequestRow(r));
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="5">Error cargando solicitudes</td></tr>`;
  }
}

function renderRequestRow(r) {
  const tr = document.createElement("tr");
  tr.dataset.requestId = String(r.id);

  const st = String(r.status || "").toLowerCase();

  tr.innerHTML = `
    <td>${r.id ?? "—"}</td>
    <td>${r.book_id ?? "—"}</td>
    <td>${r.requester_id ?? "—"}</td>
    <td class="cell-status">${badgeReqStatus(st)}</td>
    <td class="cell-actions">
      <button class="btn btn-xs" type="button" data-action="req-accept" data-id="${r.id}" ${st === "accepted" ? "disabled" : ""}>
        Aceptar
      </button>
      <button class="btn btn-xs btn-ghost" type="button" data-action="req-reject" data-id="${r.id}" ${st === "rejected" ? "disabled" : ""}>
        Rechazar
      </button>
    </td>
  `;
  return tr;
}

async function setRequestStatus(requestId, status) {
  return api(`/api/admin/book-requests/${requestId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

function wireRequestsActions() {
  const table = document.getElementById("requestsTable");
  if (!table) return;

  table.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    const requestId = Number(btn.dataset.id);
    if (!requestId) return;

    let status = null;
    if (action === "req-accept") status = "accepted";
    if (action === "req-reject") status = "rejected";
    if (!status) return;

    const ok = confirm(`¿Cambiar solicitud #${requestId} a "${status}"?`);
    if (!ok) return;

    const oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Guardando…";

    try {
      await setRequestStatus(requestId, status);
      showToast(`Solicitud #${requestId} → ${status}`, false);
      await loadRequests();
    } catch (err) {
      console.error(err);
      showToast(err.message || "Error", true);
    } finally {
      btn.disabled = false;
      btn.textContent = oldText;
    }
  });
}

function wireRequestsFilters() {
  const btnApply = document.getElementById("btnApplyReqFilters");
  const btnClear = document.getElementById("btnClearReqFilters");

  if (btnApply) btnApply.addEventListener("click", () => loadRequests());

  if (btnClear) {
    btnClear.addEventListener("click", () => {
      ["rStatus", "rBookId", "rRequesterId"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });
      loadRequests();
    });
  }
}
// --------------------
// Book Requests
// --------------------
async function loadRequests() {
  const tbody = document.querySelector("#requestsTable tbody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5">Cargando…</td></tr>`;

  try {
    const res = await api("/api/admin/book-requests", { method: "GET" });
    const items = Array.isArray(res) ? res : (res.items || []);

    if (!items.length) {
      tbody.innerHTML = `<tr><td colspan="5">No hay solicitudes</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    for (const r of items) {
      tbody.appendChild(renderRequestRow(r));
    }
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="5">Error cargando solicitudes</td></tr>`;
  }
}

function renderRequestRow(r) {
  const tr = document.createElement("tr");
  tr.dataset.id = r.id;

  tr.innerHTML = `
    <td>${r.id}</td>
    <td>${r.book_id}</td>
    <td>${r.requester_id}</td>
    <td>${badge(r.status, "badge-gray")}</td>
    <td>
      <button class="btn btn-xs" data-action="accept" data-id="${r.id}">Aceptar</button>
      <button class="btn btn-xs btn-ghost" data-action="reject" data-id="${r.id}">Rechazar</button>
    </td>
  `;
  return tr;
}

async function setRequestStatus(id, status) {
  return api(`/admin/book-requests/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

function wireRequestActions() {
  const table = document.getElementById("requestsTable");
  if (!table) return;

  table.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const id = Number(btn.dataset.id);
    const action = btn.dataset.action;
    if (!id) return;

    const status = action === "accept" ? "accepted" : "rejected";
    if (!confirm(`¿Marcar solicitud como ${status}?`)) return;

    btn.disabled = true;
    try {
      await setRequestStatus(id, status);
      showToast(`Solicitud ${status}`);
      await loadRequests();
    } catch (err) {
      console.error(err);
      showToast(err.message || "Error", true);
    } finally {
      btn.disabled = false;
    }
  });
}

// --------------------
// Boot
// --------------------
document.addEventListener("DOMContentLoaded", () => {
  loadMe();
  highlightNav();

  const btn = document.getElementById("btnLogout");
  if (btn) btn.addEventListener("click", doLogout);

  if (document.getElementById("usersTable")) {
    wireUsersActions();
    loadUsers();
  }

  if (document.getElementById("dashStats")) {
    loadDashboard();
  }

  if (document.getElementById("requestsTable")) {
    wireRequestsActions();
    loadRequests();
  }
});
