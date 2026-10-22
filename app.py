import os
import re
import sqlite3

from flask import (
    Flask, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

with app.app_context():
    init_db()
    seed_db()


EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
DUPLICATE_EMAIL_ERROR = "An account with that email already exists."
LOGIN_REQUIRED_ERROR = "Please enter your email and password."
INVALID_LOGIN_ERROR = "Invalid email or password."

# Hardcoded profile data for Step 4. It mirrors the seeded demo user so the
# numbers add up; Step 5 replaces these with real database queries.
PROFILE_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "initials": "DU",
    "member_since": "October 2026",
}

PROFILE_TRANSACTIONS = [
    {"date": "22 Oct 2026", "description": None, "category": "Other", "amount": 10.00},
    {"date": "18 Oct 2026", "description": "Dinner out", "category": "Food", "amount": 23.75},
    {"date": "15 Oct 2026", "description": "New shoes", "category": "Shopping", "amount": 64.20},
    {"date": "12 Oct 2026", "description": "Movie tickets", "category": "Entertainment", "amount": 18.99},
    {"date": "08 Oct 2026", "description": "Pharmacy", "category": "Health", "amount": 30.00},
    {"date": "05 Oct 2026", "description": "Metro card top-up", "category": "Transport", "amount": 15.00},
    {"date": "03 Oct 2026", "description": "Weekly groceries", "category": "Food", "amount": 42.50},
    {"date": "01 Oct 2026", "description": "Electricity bill", "category": "Bills", "amount": 85.00},
]

PROFILE_STATS = {
    "total_spent": 289.44,
    "transaction_count": 8,
    "top_category": "Bills",
}

PROFILE_CATEGORIES = [
    {"name": "Bills", "total": 85.00, "percent": 29},
    {"name": "Food", "total": 66.25, "percent": 23},
    {"name": "Shopping", "total": 64.20, "percent": 22},
    {"name": "Health", "total": 30.00, "percent": 10},
    {"name": "Entertainment", "total": 18.99, "percent": 7},
    {"name": "Transport", "total": 15.00, "percent": 5},
    {"name": "Other", "total": 10.00, "percent": 3},
]


def _validate_registration(name, email, password):
    """Return the first validation error message, or None if the input is valid."""
    if not name or not email or not password.strip():
        return "All fields are required."
    if not EMAIL_RE.fullmatch(email):
        return "Please enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    return None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = _validate_registration(name, email, password)
    if error is None and get_user_by_email(email) is not None:
        error = DUPLICATE_EMAIL_ERROR

    if error is None:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = DUPLICATE_EMAIL_ERROR

    if error is not None:
        return render_template(
            "register.html", error=error, name=name, email=email
        ), 400

    flash("Account created — please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(url_for("landing"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    # The password is checked exactly as typed, never trimmed.
    password = request.form.get("password", "")

    if not email or not password.strip():
        return render_template(
            "login.html", error=LOGIN_REQUIRED_ERROR, email=email
        ), 400

    user = get_user_by_email(email)
    # Same message for unknown email and wrong password, so the form
    # doesn't reveal which emails are registered.
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error=INVALID_LOGIN_ERROR, email=email
        ), 401

    # Drop any old session data before signing the user in.
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("landing"))


@app.route("/logout")
def logout():
    # Clear before flashing: flash messages are stored in the session.
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template(
        "profile.html",
        user=PROFILE_USER,
        stats=PROFILE_STATS,
        transactions=PROFILE_TRANSACTIONS,
        categories=PROFILE_CATEGORIES,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
