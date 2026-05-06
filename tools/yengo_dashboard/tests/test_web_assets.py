"""Static-asset smoke tests for tools/yengo_dashboard/web.

The dashboard ships vanilla ES modules with no JS test runner. These tests
read the static files as text and pin invariants that have broken silently
in the past (e.g. a sidebar rename that left the NAV_VIEWS map out of sync,
so the new tab routed to the fallback view).

The assertions intentionally use plain substring / regex checks rather than
parsing JS — a real parser would invite churn on every cosmetic edit. The
goal is "the symbol exists in roughly the right shape", not "the AST is
exactly X".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


@pytest.fixture(scope="module")
def index_html() -> str:
    return (WEB_DIR / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_js() -> str:
    return (WEB_DIR / "app.js").read_text(encoding="utf-8")


# ---------- Sidebar nav rename: Workshop -> Operations -----------------------


def test_sidebar_nav_uses_operations_label(index_html: str) -> None:
    """The sidebar must show 'Operations' (not 'Workshop')."""
    assert 'data-nav="operations"' in index_html, (
        "Sidebar nav button must use data-nav='operations' (renamed from 'workshop')."
    )
    assert ">Operations<" in index_html, "Visible label must read 'Operations'."
    assert 'data-nav="workshop"' not in index_html, (
        "Stale data-nav='workshop' attribute remains in index.html."
    )


def test_nav_views_map_contains_operations(app_js: str) -> None:
    """NAV_VIEWS must define 'operations' so showTab('operations') resolves
    to a real view set instead of falling through to the 'library' default."""
    # Match `operations: [...]` inside the NAV_VIEWS object literal.
    match = re.search(
        r"const\s+NAV_VIEWS\s*=\s*\{(.*?)\};", app_js, flags=re.DOTALL
    )
    assert match, "NAV_VIEWS literal not found in app.js"
    body = match.group(1)
    assert re.search(r"\boperations\s*:\s*\[", body), (
        "NAV_VIEWS must contain an 'operations' key (otherwise the sidebar "
        "Operations button routes to the 'library' fallback in showTab)."
    )
    assert "workshop:" not in body, (
        "NAV_VIEWS must not still carry the legacy 'workshop' key."
    )


def test_legacy_workshop_alias_present(app_js: str) -> None:
    """Old #workshop deep links must keep working through LEGACY_NAV_ALIASES."""
    assert "LEGACY_NAV_ALIASES" in app_js
    assert re.search(
        r"LEGACY_NAV_ALIASES\s*=\s*\{[^}]*workshop\s*:\s*[\"']operations[\"']",
        app_js,
    ), "LEGACY_NAV_ALIASES must map 'workshop' -> 'operations'."


def test_show_tab_uses_alias_resolution(app_js: str) -> None:
    """showTab must consult LEGACY_NAV_ALIASES before NAV_VIEWS, otherwise
    a stored '#workshop' hash would fall through to 'library'."""
    assert re.search(
        r"function\s+showTab\s*\([^)]*\)\s*\{[^}]*LEGACY_NAV_ALIASES",
        app_js,
        flags=re.DOTALL,
    ), "showTab() must reference LEGACY_NAV_ALIASES for alias resolution."


def test_operations_h2_uses_renamed_label(app_js: str) -> None:
    """The maintenance view header should read 'Operations'."""
    assert re.search(
        r"#view-maintenance.*?>Operations<", app_js, flags=re.DOTALL
    ), "renderMaintenance must title the section 'Operations'."


# ---------- 'Last failure' window-scope clarification ------------------------


def test_last_failure_label_carries_window_scope(app_js: str) -> None:
    """'Last failure' must disclose the run-window scope so operators don't
    read it as 'last failure ever'."""
    assert "Last failure <span" in app_js, (
        "Last-failure label must include a window-scope qualifier "
        "(e.g. '(last N runs)')."
    )
    # Tooltip is the long-form explanation.
    assert "Computed only from the most recent" in app_js, (
        "Last-failure tile must carry a tooltip explaining the scope."
    )


# ---------- Bright theme (Slice 2) -------------------------------------------


@pytest.fixture(scope="module")
def styles_css() -> str:
    return (WEB_DIR / "styles.css").read_text(encoding="utf-8")


def test_body_defaults_to_light_theme(index_html: str) -> None:
    """The handoff calls for light as default; the body must declare it
    inline so server-rendered HTML matches what the JS later persists."""
    assert 'data-theme="light"' in index_html, (
        "<body> must default to data-theme='light' (Slice 2 requirement)."
    )


def test_pre_paint_theme_script_present(index_html: str) -> None:
    """A small inline <script> in <head> must read localStorage and set
    data-theme before CSS paints, otherwise dark-mode users see a white
    flash on every reload."""
    assert "yengo-dashboard:theme" in index_html, (
        "Inline pre-paint theme script must read the persisted preference."
    )
    assert "documentElement.dataset.theme" in index_html


def test_styles_define_light_theme_overrides(styles_css: str) -> None:
    """Light theme must override the dominant dark surfaces."""
    assert 'body[data-theme="light"]' in styles_css, (
        "styles.css must define body[data-theme='light'] override block."
    )
    # A few concrete surfaces the override block must touch.
    assert "#sidebar" in styles_css
    # Override must hit at least one of the inline Tailwind dark classes.
    assert ".bg-slate-900" in styles_css or ".bg-zinc-950" in styles_css


def test_log_panels_have_no_light_theme_override(styles_css: str) -> None:
    """Log/terminal surfaces must stay dark in both themes — high-contrast
    terminal output is the whole point. The CSS file must not contain a
    light-mode rule that recolours .log-panel's background."""
    # Crude but effective: scan for any selector that targets .log-panel
    # under body[data-theme="light"]. Such a rule would defeat the design.
    bad = re.search(
        r'body\[data-theme="light"\][^{]*\.log-panel[^{]*\{[^}]*background',
        styles_css,
    )
    assert bad is None, (
        "Light-mode override must not change .log-panel background — "
        "log surfaces stay dark in both themes."
    )


def test_theme_toggle_button_present(index_html: str, app_js: str) -> None:
    """Toggle button must exist in the sidebar and be wired up."""
    assert 'id="theme-toggle"' in index_html, (
        "Sidebar must carry an explicit theme-toggle button."
    )
    assert "applyTheme" in app_js and "THEME_KEY" in app_js, (
        "app.js must expose applyTheme/THEME_KEY for the toggle to flip + persist."
    )

