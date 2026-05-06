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


# ---------- Header system chip (Slice 3) -------------------------------------


def test_top_header_with_system_chip_present(index_html: str) -> None:
    """The new top header must host the always-visible system chip."""
    assert 'id="top-header"' in index_html, (
        "Slice 3: top header must exist to host the system chip."
    )
    assert 'id="system-chip"' in index_html, (
        "Slice 3: #system-chip button must be in the top header."
    )
    assert 'id="page-breadcrumb"' in index_html, (
        "Slice 3: top header must include a #page-breadcrumb element."
    )


def test_legacy_sidebar_system_pill_removed(index_html: str) -> None:
    """The old bottom-left System button must be gone — the chip replaces it."""
    assert 'id="system-pill"' not in index_html, (
        "Slice 3: legacy sidebar #system-pill must be removed."
    )


def test_paint_system_chip_wired_into_master_tick(app_js: str) -> None:
    """paintSystemChip must run on every poll alongside paintStatusStrip,
    otherwise the chip drifts out of sync with SYSTEM state."""
    assert "function paintSystemChip" in app_js, (
        "Slice 3: paintSystemChip() must be defined in app.js."
    )
    assert re.search(
        r"function\s+masterTick\s*\([^)]*\)\s*\{[^}]*paintSystemChip\s*\(",
        app_js,
        flags=re.DOTALL,
    ), "Slice 3: masterTick() must call paintSystemChip() each cycle."


def test_system_chip_click_opens_system_dialog(app_js: str) -> None:
    """The chip must open the same dialog as the bottom status strip."""
    assert re.search(
        r"#system-chip[\s\S]{0,400}?paintSystemDialog[\s\S]{0,200}?showModal",
        app_js,
    ), "Slice 3: clicking #system-chip must call paintSystemDialog + showModal."


def test_system_chip_severity_styles_present(styles_css: str) -> None:
    """Each chip severity must be styled, otherwise warn/error look identical."""
    for sev in ("ok", "running", "warn", "error"):
        assert f'.system-chip[data-sev="{sev}"]' in styles_css, (
            f"Slice 3: chip severity '{sev}' must be styled in styles.css."
        )


# ---------- Clean path routing (Slice 4) -------------------------------------


def test_show_tab_uses_push_state_clean_path(app_js: str) -> None:
    """Slice 4: showTab must push a clean path (/nav), not a hash (#nav)."""
    body = re.search(r"function\s+showTab\s*\([^)]*\)\s*\{(.*?)\n\}", app_js, flags=re.DOTALL)
    assert body, "showTab() not found"
    assert "pushState" in body.group(1), (
        "showTab() must call history.pushState (clean-path routing)."
    )
    assert "`#${nav}`" not in body.group(1), (
        "showTab() must not write hash-style URLs anymore."
    )


def test_parse_path_helper_present(app_js: str) -> None:
    """Slice 4: a parsePath() helper is the single source of pathname parsing."""
    assert re.search(r"function\s+parsePath\s*\(", app_js), (
        "Slice 4: parsePath() helper must exist for path-based routing."
    )


def test_popstate_listener_handles_back_forward(app_js: str) -> None:
    """Slice 4: browser back/forward must re-render via popstate."""
    assert re.search(
        r'addEventListener\(\s*["\']popstate["\']', app_js
    ), "Slice 4: window must listen for 'popstate' to handle back/forward."


def test_legacy_hash_rewritten_at_boot(app_js: str) -> None:
    """Slice 4: a #workshop or #operations hash must be rewritten to a clean
    path on boot so the URL bar reflects the new format immediately."""
    # The boot block computes a `cleanPath` from the legacy hash and
    # rewrites the URL via replaceState. Look for that pair.
    assert "cleanPath" in app_js, (
        "Slice 4: boot must compute a cleanPath from the legacy hash."
    )
    assert re.search(
        r"history\.replaceState\([^)]*cleanPath", app_js
    ), "Slice 4: legacy hashes must be rewritten via replaceState to /<nav>."


def test_guide_uses_clean_path(app_js: str) -> None:
    """Boot: parsePath must recognize /guide/<path> deep links."""
    body = re.search(r"function\s+parsePath\s*\([^)]*\)\s*\{(.*?)\n\}", app_js, flags=re.DOTALL)
    assert body, "parsePath() not found"
    assert '"guide"' in body.group(1) and "guidePath" in body.group(1), (
        "parsePath must extract guide subpath into guidePath."
    )


# ---------- Logs nav (Slice 5) -----------------------------------------------


def test_sidebar_includes_logs_nav(index_html: str) -> None:
    """Slice 5: Logs is a top-level nav item with the scroll-text icon."""
    assert 'data-nav="logs"' in index_html, (
        "Slice 5: sidebar must include data-nav='logs' button."
    )
    assert ">Logs<" in index_html, "Visible label must read 'Logs'."


def test_view_logs_section_present(index_html: str) -> None:
    """The Logs nav requires a #view-logs section in the page shell."""
    assert 'id="view-logs"' in index_html, (
        "Slice 5: index.html must declare a #view-logs section."
    )


def test_nav_views_routes_logs(app_js: str) -> None:
    """NAV_VIEWS must route 'logs' to a 'logs' view (no fallback)."""
    match = re.search(r"const\s+NAV_VIEWS\s*=\s*\{(.*?)\};", app_js, flags=re.DOTALL)
    assert match
    assert re.search(r"\blogs\s*:\s*\[", match.group(1)), (
        "NAV_VIEWS must contain a 'logs' key."
    )


def test_render_logs_function_present(app_js: str) -> None:
    """renderLogs must exist and own its three subtab panes."""
    assert "function renderLogs" in app_js, (
        "Slice 5: renderLogs() must be defined."
    )
    for sub in ("stage", "audit", "live"):
        assert f'data-subtab="{sub}"' in app_js, (
            f"renderLogs must wire a subtab button for '{sub}'."
        )


def test_publish_log_search_moved_out_of_maintenance(app_js: str) -> None:
    """The publish-log search UI must live in renderLogs (Audit pane), not in
    renderMaintenance, otherwise the operations page still owns it."""
    maint = re.search(
        r"function\s+renderMaintenance\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js,
        flags=re.DOTALL,
    )
    assert maint, "renderMaintenance not found"
    assert "pl-go" not in maint.group(1), (
        "Slice 5: publish-log search button must not live in renderMaintenance."
    )
    # And the audit pane in renderLogs MUST own it.
    audit = re.search(
        r"function\s+_renderLogsAuditPane\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js,
        flags=re.DOTALL,
    )
    assert audit, "_renderLogsAuditPane not found"
    assert 'id="pl-go"' in audit.group(1), (
        "Slice 5: publish-log search must be rendered by _renderLogsAuditPane."
    )


def test_publish_log_results_render_as_table(app_js: str) -> None:
    """Results must come back as a <table>, not a <pre>JSON dump."""
    assert "renderPublishLogResults" in app_js, (
        "Slice 5: a renderPublishLogResults() helper must transform the raw "
        "CLI payload into a structured table."
    )


def test_internal_nav_link_handler_present(app_js: str) -> None:
    """Cross-tab links (e.g. Operations → Logs) must route via showTab,
    not trigger a real navigation."""
    assert re.search(
        r'data-internal-nav', app_js
    ), "Slice 5: in-app cross-tab links must use data-internal-nav."
    assert re.search(
        r'closest\(\s*"a\[data-internal-nav\]"\s*\)', app_js
    ), "Slice 5: click delegation must intercept data-internal-nav links."

