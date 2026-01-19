async function api(path, opts = {}) {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });

  // intenta parsear json siempre
  let data = null;
  try { data = await res.json(); } catch (_) {}

  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
    const err = new Error(msg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function setMsg(id, text, isError=false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text || "";
  el.style.color = isError ? "#ff3b5c" : "";
}
