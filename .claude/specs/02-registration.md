# Spec: Registration

## Overview

This step makes the registration form work. Today `GET /register` only shows the form, and submitting it does nothing. This step adds `POST /register`, which checks the name, email and password, hashes the password with werkzeug and saves a new row in the `users` table. When signup works, the user goes to the login page and sees a success message. When it fails, the form shows again with an error and keeps what the user typed. Registration is the first auth feature on the roadmap. Login and logout (Step 3) need real user accounts to sign into, so this step comes first.

## Depends on

- **Step 1 — Database setup**: the `users` table, `get_db()`, and `PRAGMA foreign_keys = ON` in `database/db.py`.

## Routes

- `GET /register` — already exists; still renders `register.html` — public
- `POST /register` — checks the form, creates the user, then redirects to `login` with a success flash. On a validation error, it re-renders `register.html` with an error and the user's input — public

Implement both as one view function, `register()`, with `methods=["GET", "POST"]`. Keep the existing endpoint name `register` so that `url_for('register')` still works everywhere.

## Database changes

No database changes. The `users` table already has every needed column (`id`, `name`, `email UNIQUE`, `password_hash`, `created_at`).

Add these helper functions to `database/db.py`. They are new functions, not schema changes:

- `get_user_by_email(email)` — returns the matching `sqlite3.Row`, or `None`.
- `create_user(name, email, password)` — hashes the password with `generate_password_hash` and inserts the user with a parameterised query. It returns the new user's id. If the email is already taken, it raises `sqlite3.IntegrityError`.

Both functions open their own connection with `get_db()` and close it in `finally`, the same way `init_db()` and `seed_db()` do.

## Templates

- **Create:** none
- **Modify:**
  - `templates/register.html`
    - Change the hardcoded `action="/register"` to `action="{{ url_for('register') }}"`.
    - Fill the `name` and `email` inputs with the previously submitted values (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`). Never fill the password back in.
    - Add `minlength="8"` to the password input.
  - `templates/login.html`
    - Show flashed messages (`get_flashed_messages(with_categories=true)`) above the form, inside `.auth-card`. Use a `.auth-success` box for the `success` category.

## Files to change

- `app.py`
  - Add `request`, `redirect`, `url_for` and `flash` to the Flask import.
  - Set `app.secret_key` from `os.environ.get("SECRET_KEY", ...)` with a dev fallback. Flash messages need a secret key.
  - Import `create_user` and `get_user_by_email` from `database.db`.
  - Make `register()` accept GET and POST and put the validation logic in it.
- `database/db.py` — add `get_user_by_email()` and `create_user()`.
- `templates/register.html` — see Templates.
- `templates/login.html` — see Templates.
- `static/css/style.css` — add an `.auth-success` rule next to `.auth-error`. Use `var(--accent)` and `var(--accent-light)`, with no hex values.

## Files to create

- `tests/test_register.py` — route tests that use the Flask test client. Point the database at a temp file by monkeypatching `database.db.DB_PATH`, the same way `tests/test_db.py` does.

## New dependencies

No new dependencies. `flask` and `werkzeug` are already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only. Never build SQL with f-strings or `.format()`
- Passwords hashed with werkzeug (`generate_password_hash`). Never store or log plain-text passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No DB logic inside the route. All SQL lives in `database/db.py`
- Use `url_for()` for every internal link and redirect. No hardcoded paths
- Trim whitespace from `name` and `email`, and lowercase `email`, before checking or saving
- Validation rules, checked on the server even though the HTML also uses `required`:
  - All three fields are required. Error: "All fields are required."
  - The email must look like an address (contain `@` with text on both sides and a `.` in the domain). Error: "Please enter a valid email address."
  - The password must be at least 8 characters. Error: "Password must be at least 8 characters."
  - The email must not already be registered. Error: "An account with that email already exists."
- Check for a duplicate email with `get_user_by_email()` first. Also catch `sqlite3.IntegrityError` from `create_user()` in case two signups race
- On success, follow the POST/Redirect/GET pattern: `flash("Account created — please sign in.", "success")` and then `redirect(url_for("login"))`
- Do not log the user in or touch `session`. That is Step 3
- Do not implement `/logout`, `/profile`, or any expense stubs
- Return a 400 status when re-rendering after a validation error

## Definition of done

- [ ] `GET /register` renders the form as it does now
- [ ] A new name, email and password (8+ characters) redirects to `/login` and shows "Account created — please sign in."
- [ ] The new user exists in the `users` table, the email is stored in lowercase, and `password_hash` is a werkzeug hash (not the plain-text password)
- [ ] Registering again with the same email (in any letter case) shows "An account with that email already exists." and creates no second row
- [ ] A password shorter than 8 characters shows the length error and creates no user
- [ ] Blank fields, including fields with only spaces, show "All fields are required."
- [ ] After any error, the name and email fields still hold what the user typed, and the password field is empty
- [ ] `register.html` has no hardcoded `/register` URL
- [ ] The success message box is styled only with CSS variables
- [ ] `pytest` passes, including the new `tests/test_register.py` (success, duplicate email, short password, missing fields)
- [ ] The app starts on port 5001 without errors
