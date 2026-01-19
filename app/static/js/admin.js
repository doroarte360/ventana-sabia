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
    // si falla /auth/me, te mandamos a login
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
// Users: list + actions
// --------------------
async function loadUsers() {
  const tbody = document.querySelector("#usersTable tbody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="5">Cargando…</td></tr>`;

  try {
    const res = await api("/api/admin/users", { method: "GET" });

    // Soporta ambos formatos: array directo o {items:[...]}
    const users = Array.isArray(res) ? res : (res.items || []);

    if (!users.length) {
      tbody.innerHTML = `<tr><td colspan="5">No hay usuarios</td></tr>`;
      return;
    }

    tbody.innerHTML = "";

    for (const u of users) {
      const isBlocked = !!u.is_blocked;
      const isActive = (u.is_active !== false); // por defecto true

      const statusHtml = isBlocked
        ? badge("Bloqueado", "badge-red")
        : (isActive ? badge("Activo", "badge-green") : badge("Inactivo", "badge-gray"));

      const roleHtml = badge(
        u.role || "—",
        `badge-role badge-${String(u.role || "").toLowerCase()}`
      );

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${u.id ?? "—"}</td>
        <td>${escapeHtml(u.email ?? "")}</td>
        <td>${roleHtml}</td>
        <td>${statusHtml}</td>
        <td>
          <button class="btn btn-xs" type="button"
            data-action="toggle-block"
            data-id="${u.id}"
            data-blocked="${isBlocked ? "1" : "0"}">
            ${isBlocked ? "Desbloquear" : "Bloquear"}
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    }
  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="5">Error cargando usuarios</td></tr>`;
  }
}

async function toggleUserBlock(userId, isBlocked) {
  const next = !isBlocked; // si está bloqueado -> desbloquear (false), si no -> bloquear (true)

  return api(`/api/admin/users/${userId}/block`, {
  method: "PATCH",
  body: JSON.stringify({ is_blocked: next }),
});
}

function wireUsersActions() {
  const table = document.getElementById("usersTable");
  if (!table) return;

  // Event delegation: 1 listener para toda la tabla
  table.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const action = btn.dataset.action;
    const userId = Number(btn.dataset.id);
    if (!userId) return;

    if (action === "toggle-block") {
      const isBlocked = btn.dataset.blocked === "1";

      const ok = confirm(
        isBlocked ? "¿Desbloquear este usuario?" : "¿Bloquear este usuario?"
      );
      if (!ok) return;

      btn.disabled = true;

      try {
        await toggleUserBlock(userId, isBlocked);
        await loadUsers(); // refresca tabla para ver cambios
      } catch (err) {
        console.error(err);
        alert(err.message || "Error");
      } finally {
        btn.disabled = false;
      }
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

  // Solo en /admin/users
  if (document.getElementById("usersTable")) {
    wireUsersActions();
    loadUsers();
  }
});
