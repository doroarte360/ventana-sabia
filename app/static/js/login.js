const form = document.getElementById("loginForm");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  setMsg("msg", "");

  const fd = new FormData(form);
  const payload = {
    email: String(fd.get("email") || "").trim(),
    password: String(fd.get("password") || ""),
  };

  try {
    await api("/auth/login", { method: "POST", body: JSON.stringify(payload) });
    window.location.href = "/admin";
  } catch (err) {
    setMsg("msg", err.message || "Error", true);
  }
});
