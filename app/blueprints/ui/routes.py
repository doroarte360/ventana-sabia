from flask import render_template, redirect, url_for, session
from . import bp

def _require_login():
    if not session.get("user_id"):
        return redirect(url_for("ui.login_page"))
    return None

@bp.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("ui.admin_dashboard"))
    return redirect(url_for("ui.login_page"))

@bp.get("/login")
def login_page():
    return render_template("login/login.html")

@bp.get("/admin")
def admin_dashboard():
    r = _require_login()
    if r: return r
    return render_template("admin/dashboard.html")

@bp.get("/admin/book-requests")
def admin_book_requests_page():
    r = _require_login()
    if r: return r
    return render_template("admin/book_requests.html")

@bp.get("/admin/users")
def admin_users_page():
    r = _require_login()
    if r: return r
    return render_template("admin/users.html")

@bp.get("/admin/audit")
def admin_audit_page():
    r = _require_login()
    if r: return r
    return render_template("admin/audit.html")

@bp.get("/admin/security")
def admin_security_page():
    r = _require_login()
    if r: return r
    return render_template("admin/security.html")
