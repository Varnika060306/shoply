# Spec: Login and Logout

## Overview

This step makes the sign-in form work and adds sign-out. Today `GET /login` only shows the form, and `/logout` returns a placeholder string. This step adds `POST /login`, which looks up the user by email, checks the password against the stored werkzeug hash, and stores the user's id and name in Flask's `session`. It also implements `GET /logout`, which clears the session and sends the user back to the login page with a message. The navbar changes based on whether someone is signed in. Login comes right after registration because users now have real accounts, and every later step (profile, adding and editing expenses) needs to know who the current user is.

## Depends on

- **Step 1 — Database setup**: the `users` table and `get_db()` in `database/db.py`.
- **Step 2 — Registration**: `get_user_by_email()` in `database/db.py`, `app.secret_key` in `app.py`, and flash-message rendering in `templates/login.html`.

## Routes

- `GET /login` — already exists; still renders `login.html`. If the user is already signed in, redirect to `landing` instead — public
- `POST /login` — checks the email and password. On success, stores the user in the session and redirects to `landing`. On failure, re-renders `login.html` with an error and the typed email — public
- `GET /logout` — replaces the existing stub. Clears the session, flashes "You have been signed out.", and redirects to `login`. Works the same whether or not anyone is signed in — public

Implement `GET` and `POST /login` as one view function, `login()`, with `methods=["GET", "POST"]`. Keep the endpoint names `login` and `logout` so that existing `url_for()` calls keep working.

## Database changes

No database changes. The `users` table already has `id`, `name`, `email` and `password_hash`.

No new helper functions are needed either. Reuse the existing `get_user_by_email(email)` from `database/db.py`. It expects an email that is already trimmed and lowercased.

## Templates

- **Create:** none
- **Modify:**
  - `templates/login.html`
    - Fill the email input with the previously submitted value (`value="{{ email or '' }}"`). Never fill the password back in.
    - Keep the existing flash and `error` blocks as they are.
  - `templates/base.html`
    - Navbar: when `session.user_id` is set, show the user's name (`session.user_name`) and a "Sign out" link to `url_for('logout')`. Otherwise, show the current "Sign in" and "Get started" links.
    - Footer: replace the hardcoded `/terms` and `/privacy` links with `url_for('terms')` and `url_for('privacy')`. CLAUDE.md forbids hardcoded URLs, and this file is already being edited.

## Files to change

- `app.py`
  - Add `session` to the Flask import.
  - Import `check_password_hash` from `werkzeug.security`.
  - Make `login()` accept GET and POST and put the sign-in logic in it.
  - Replace the `/logout` stub with the real logout route.
- `templates/login.html` — see Templates.
- `templates/base.html` — see Templates.
- `static/css/style.css` — only if the signed-in navbar needs styling (for example a `.nav-user` class for the name). Use CSS variables only.
- `CLAUDE.md` — in the routes table, mark `GET /logout` as implemented and note that `/login` now handles POST.

## Files to create

- `tests/test_login.py` — route tests that use the Flask test client. Point the database at a temp file by monkeypatching `database.db.DB_PATH`, the same way `tests/test_register.py` does. Create test users with `db.create_user()`.

## New dependencies

No new dependencies. `flask` and `werkzeug` are already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only. Never build SQL with f-strings or `.format()`
- Passwords hashed with werkzeug. Check them with `check_password_hash`. Never compare plain text, and never store or log passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No DB logic inside the route. All SQL lives in `database/db.py`
- Use `url_for()` for every internal link and redirect. No hardcoded paths
- Trim whitespace from `email` and lowercase it before the lookup. Do not trim the password
- Do not apply the 8-character minimum at login. The seeded demo account uses `demo123` (7 characters) and must still be able to sign in
- Validation rules:
  - Email and password are both required. Error: "Please enter your email and password." Status 400
  - Unknown email and wrong password show the same message, so the form does not reveal which emails are registered. Error: "Invalid email or password." Status 401
- On success:
  - Call `session.clear()` first, then set `session["user_id"]` and `session["user_name"]`. Clearing first drops any old session data
  - Redirect to `url_for("landing")` (POST/Redirect/GET). Step 4 may change this to the profile page
- Store only the user's id and name in the session. Never store the password hash or the whole row
- Logout uses `session.clear()`, then `flash("You have been signed out.", "success")`, then `redirect(url_for("login"))`
- Keep `/logout` as GET to match the existing route table
- Do not add a `login_required` decorator or protect any routes yet. That comes with the steps that need it
- Do not implement `/profile` or any expense stubs
- Do not change registration behaviour. Registering must still not sign the user in

## Definition of done

- [ ] `GET /login` renders the sign-in form when signed out
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/` and the navbar shows "Demo User" and a "Sign out" link
- [ ] Signing in with an email in mixed case or with surrounding spaces works
- [ ] A wrong password shows "Invalid email or password.", returns 401, and leaves no `user_id` in the session
- [ ] An unregistered email shows the same "Invalid email or password." message
- [ ] A blank email or password shows "Please enter your email and password." and returns 400
- [ ] After any error, the email field holds what the user typed and the password field is empty
- [ ] Visiting `/login` while signed in redirects to `/`
- [ ] Clicking "Sign out" clears the session, redirects to `/login`, and shows "You have been signed out."
- [ ] Visiting `/logout` while signed out also redirects to `/login` without an error
- [ ] After signing out, the navbar shows "Sign in" and "Get started" again
- [ ] A user created through `/register` can then sign in with the same password
- [ ] `base.html` has no hardcoded URLs, including the footer links
- [ ] `pytest` passes, including the new `tests/test_login.py` and the existing `tests/test_register.py`
- [ ] The app starts on port 5001 without errors
