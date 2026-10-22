import re
from pathlib import Path

import pytest

from database import db

ROOT = Path(__file__).resolve().parent.parent
PROFILE_TEMPLATE = ROOT / "templates" / "profile.html"
PROFILE_CSS = ROOT / "static" / "css" / "profile.css"
HEX_COLOUR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    # Import after patching DB_PATH so the app's startup init/seed
    # runs against the temp DB, never the real one.
    from app import app as flask_app

    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def log_in(client, user_id=1, user_name="Alice"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = user_name


def get_profile_html(client):
    log_in(client)
    resp = client.get("/profile")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


# ------------------------------------------------------------------ #
# Access                                                              #
# ------------------------------------------------------------------ #

def test_logged_out_user_is_redirected_to_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_logged_out_redirect_lands_on_login_page(client):
    resp = client.get("/profile", follow_redirects=True)
    assert resp.request.path == "/login"


def test_logged_in_user_gets_200(client):
    log_in(client)
    assert client.get("/profile").status_code == 200


def test_profile_is_protected_again_after_logout(client):
    log_in(client)
    client.get("/logout")
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


# ------------------------------------------------------------------ #
# Page content                                                        #
# ------------------------------------------------------------------ #

def test_user_info_card(client):
    html = get_profile_html(client)
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "Member since" in html
    assert 'class="profile-avatar"' in html


def test_summary_stats(client):
    html = get_profile_html(client)
    for label in ("Total spent", "Transactions", "Top category"):
        assert label in html
    assert "₹289.44" in html
    assert html.count('class="profile-card profile-stat"') >= 3


def test_transaction_table_has_at_least_three_rows(client):
    html = get_profile_html(client)
    assert "<table" in html
    assert html.count('class="profile-badge cat--') >= 3
    assert "Electricity bill" in html
    assert "₹85.00" in html


def test_category_badges_use_css_classes(client):
    html = get_profile_html(client)
    assert 'class="profile-badge cat--food"' in html
    assert 'class="profile-badge cat--bills"' in html


def test_category_breakdown_has_at_least_three_categories(client):
    html = get_profile_html(client)
    assert "By category" in html
    assert html.count('class="profile-bar"') >= 3


def test_navbar_shows_logged_in_state(client):
    html = get_profile_html(client)
    assert '<span class="nav-user">Alice</span>' in html
    assert "Sign out" in html
    assert "Get started" not in html


def test_page_loads_its_stylesheet(client):
    html = get_profile_html(client)
    assert "css/profile.css" in html


def test_hardcoded_data_is_consistent(client):
    # Uses the client fixture so `app` is first imported against the temp DB.
    from app import PROFILE_CATEGORIES, PROFILE_STATS, PROFILE_TRANSACTIONS

    tx_total = sum(tx["amount"] for tx in PROFILE_TRANSACTIONS)
    cat_total = sum(cat["total"] for cat in PROFILE_CATEGORIES)
    assert round(tx_total, 2) == PROFILE_STATS["total_spent"]
    assert round(cat_total, 2) == PROFILE_STATS["total_spent"]
    assert len(PROFILE_TRANSACTIONS) == PROFILE_STATS["transaction_count"]
    top = max(PROFILE_CATEGORIES, key=lambda cat: cat["total"])
    assert top["name"] == PROFILE_STATS["top_category"]


# ------------------------------------------------------------------ #
# Template and stylesheet rules                                       #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("path", [PROFILE_TEMPLATE, PROFILE_CSS])
def test_no_hex_colours(path):
    assert HEX_COLOUR_RE.findall(path.read_text()) == []


def test_template_has_no_inline_styles():
    text = PROFILE_TEMPLATE.read_text()
    assert "style=" not in text
    assert "<style" not in text


def test_template_has_no_hardcoded_internal_links():
    assert 'href="/' not in PROFILE_TEMPLATE.read_text()
