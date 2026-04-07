import os
import csv
import json
import io
import secrets
import functools
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    make_response,
    g,
)

import config
import database

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY


@app.before_request
def before_request():
    database.get_db()


@app.teardown_appcontext
def teardown_db(exception):
    database.close_db(exception)


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            token = request.headers.get("X-CSRF-Token")
            if token != session.get("csrf_token"):
                if request.method == "POST" and request.path == "/admin/logout":
                    pass
                else:
                    return jsonify({"error": "Invalid CSRF token"}), 403
        return f(*args, **kwargs)
    return decorated


# ---- Public routes ----

@app.route("/")
def index():
    return render_template("feedback.html")


@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    rating = data.get("rating")
    feedback_text = (data.get("feedback_text") or "").strip()
    category = (data.get("category") or "").strip().lower()

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Valid email is required"}), 400
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be 1-5"}), 400
    if not feedback_text:
        return jsonify({"error": "Feedback text is required"}), 400
    if category not in ("general", "bug", "feature"):
        category = "general"

    new_id = database.add_feedback(name, email, rating, feedback_text, category)
    return jsonify({"success": True, "id": new_id}), 201


# ---- Admin routes ----

@app.route("/admin")
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/admin/login", methods=["POST"])
def admin_auth():
    data = request.get_json(silent=True) or {}
    submitted_key = data.get("secret_key", "")
    stored_key = database.get_config("admin_secret_key")

    if submitted_key == stored_key:
        session["admin_logged_in"] = True
        session["csrf_token"] = secrets.token_hex(32)
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Invalid secret key"}), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    session.pop("csrf_token", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "DESC")
    category = request.args.get("category", "all")
    rating = request.args.get("rating", "all")
    search = request.args.get("search", "").strip()

    if page < 1:
        page = 1
    if per_page not in (10, 20, 50, 100):
        per_page = 20

    feedbacks, total = database.get_all_feedback(
        sort_by=sort_by,
        sort_order=sort_order,
        category=category,
        rating=rating,
        search=search if search else None,
        page=page,
        per_page=per_page,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages

    star_map = {1: "&#9733;", 2: "&#9733;&#9733;", 3: "&#9733;&#9733;&#9733;", 4: "&#9733;&#9733;&#9733;&#9733;", 5: "&#9733;&#9733;&#9733;&#9733;&#9733;"}

    return render_template(
        "admin_dashboard.html",
        feedbacks=[dict(r) for r in feedbacks],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        sort_by=sort_by,
        sort_order=sort_order,
        category=category,
        rating=rating,
        search=search,
        star_map=star_map,
    )


@app.route("/admin/export/csv")
@login_required
def export_csv():
    rows = database.get_all_for_export()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "email", "rating", "feedback_text", "category", "reply", "created_at"])
    for r in rows:
        writer.writerow([r["id"], r["name"], r["email"], r["rating"], r["feedback_text"], r["category"], r["reply"] or "", r["created_at"]])
    output.seek(0)
    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=feedback_export.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


@app.route("/admin/export/json")
@login_required
def export_json():
    rows = database.get_all_for_export()
    data = [dict(r) for r in rows]
    output = json.dumps(data, indent=2, default=str)
    resp = make_response(output)
    resp.headers["Content-Disposition"] = "attachment; filename=feedback_export.json"
    resp.headers["Content-Type"] = "application/json"
    return resp


@app.route("/admin/response/<int:feedback_id>", methods=["DELETE"])
@login_required
def delete_feedback_endpoint(feedback_id):
    deleted = database.delete_feedback(feedback_id)
    if deleted:
        return jsonify({"success": True}), 200
    return jsonify({"error": "Feedback not found"}), 404


@app.route("/admin/response/<int:feedback_id>", methods=["PATCH"])
@login_required
def reply_feedback_endpoint(feedback_id):
    data = request.get_json(silent=True)
    if not data or "reply" not in data:
        return jsonify({"error": "Reply text is required"}), 400
    if not database.get_feedback_by_id(feedback_id):
        return jsonify({"error": "Feedback not found"}), 404
    database.update_feedback_reply(feedback_id, data["reply"])
    return jsonify({"success": True}), 200


if __name__ == "__main__":
    database.init_db()
    app.run(debug=config.DEBUG, host="127.0.0.1", port=5000)
