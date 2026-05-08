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
        r'viewHeader\(\s*["\']Operations["\']', app_js
    ), "renderMaintenance must title the section 'Operations' via viewHeader()."


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


def test_body_theme_synced_from_documentElement(index_html: str) -> None:
    """The <head> pre-paint script writes data-theme to <html>, but every
    light-mode CSS rule targets body[data-theme=...]. Without a sync
    step the persisted dark preference is silently lost on every reload
    (body keeps its inline 'light'). A second inline <script> right
    after <body> must mirror the value onto the body element."""
    # Find the body open tag, then verify a sync script appears before any
    # visible content (i.e. before the sidebar nav). We don't pin exact
    # placement — only that the html→body mirror runs early.
    body_open = index_html.find("<body")
    sidebar = index_html.find('id="sidebar"')
    assert body_open != -1 and sidebar > body_open, "body/sidebar landmarks missing"
    head_of_body = index_html[body_open:sidebar]
    assert re.search(
        r"document\.body\.dataset\.theme\s*=\s*[A-Za-z_]",
        head_of_body,
    ), (
        "An inline <script> must run between <body> and the first visible "
        "element to copy documentElement.dataset.theme onto "
        "document.body.dataset.theme."
    )
    assert "documentElement.dataset.theme" in head_of_body, (
        "The body-sync script must read from documentElement (the value "
        "the head pre-paint script wrote)."
    )


def test_apply_theme_writes_both_html_and_body(app_js: str) -> None:
    """applyTheme must keep html and body in sync, otherwise the next
    reload's pre-paint reads a stale documentElement value."""
    body = re.search(
        r"function\s+applyTheme\s*\([^)]*\)\s*\{(.*?)\n\}", app_js, flags=re.DOTALL
    )
    assert body, "applyTheme() not found"
    src = body.group(1)
    assert "document.body.dataset.theme" in src, (
        "applyTheme must set document.body.dataset.theme."
    )
    assert "document.documentElement.dataset.theme" in src, (
        "applyTheme must also set document.documentElement.dataset.theme so "
        "the next reload's pre-paint reads the fresh value."
    )


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


# ---------- Operations regrouping (Slice 6) ----------------------------------


def test_operations_has_three_blast_radius_groups(app_js: str) -> None:
    """Slice 6: renderMaintenance must render three discrete sections, one
    per blast-radius bucket (diagnostics, maintenance, destructive)."""
    maint = re.search(
        r"function\s+renderMaintenance\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js,
        flags=re.DOTALL,
    )
    assert maint, "renderMaintenance not found"
    body = maint.group(1)
    for bucket in ("diagnostics", "maintenance", "destructive"):
        assert f'data-ops-group="{bucket}"' in body, (
            f"Slice 6: Operations must have a data-ops-group=\"{bucket}\" section."
        )


def test_operations_diagnostics_links_to_read_only_views(app_js: str) -> None:
    """Slice 6: the Diagnostics section is the 'look-before-you-leap'
    triage panel — it must link to pipeline / logs / library via
    data-internal-nav so the clicks stay SPA-routed."""
    maint = re.search(
        r"function\s+renderMaintenance\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js,
        flags=re.DOTALL,
    )
    assert maint
    diagnostics = re.search(
        r'data-ops-group="diagnostics"[\s\S]*?</section>', maint.group(1)
    )
    assert diagnostics, "Slice 6: diagnostics section not found"
    diag_html = diagnostics.group(0)
    for nav in ("pipeline", "logs", "library"):
        assert f'data-internal-nav="{nav}"' in diag_html, (
            f"Slice 6: diagnostics must link to /{nav} via data-internal-nav."
        )


def test_destructive_section_has_visual_fence(app_js: str, styles_css: str) -> None:
    """Slice 6: the destructive bucket must carry a warning header AND have
    a dedicated CSS class so the rose ring works in both themes."""
    maint = re.search(
        r"function\s+renderMaintenance\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js,
        flags=re.DOTALL,
    )
    assert maint
    destructive = re.search(
        r'data-ops-group="destructive"[\s\S]*?</section>', maint.group(1)
    )
    assert destructive, "Slice 6: destructive section not found"
    dest_html = destructive.group(0)
    assert "alert-triangle" in dest_html, (
        "Slice 6: destructive section must carry an alert-triangle icon."
    )
    assert "ops-group--destructive" in dest_html, (
        "Slice 6: destructive section must carry the ops-group--destructive class."
    )
    assert ".ops-group--destructive" in styles_css, (
        "Slice 6: ops-group--destructive must be styled in styles.css."
    )
    assert re.search(
        r'body\[data-theme="light"\][^{]*\.ops-group--destructive',
        styles_css,
    ), "Slice 6: ops-group--destructive must have a light-theme override."


def test_publish_log_pointer_removed_from_operations(app_js: str) -> None:
    """Slice 6: the Slice 5 'Looking for publish-log search?' pointer is
    gone — Diagnostics already cross-links to /logs."""
    maint = re.search(
        r"function\s+renderMaintenance\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js,
        flags=re.DOTALL,
    )
    assert maint
    assert "Looking for publish-log search" not in maint.group(1), (
        "Slice 6: the transitional pointer must be removed."
    )


# ---------- View-header consistency (Theme 0) --------------------------------


def test_view_header_helper_defined(app_js: str) -> None:
    """Theme 0: a single viewHeader() helper is the source of truth for
    every top-of-view title. Before this existed, Overview was bare,
    LiveRun used mb-4, and the rest used mb-3 with a flex wrapper —
    six render functions, three different patterns."""
    assert re.search(r"function\s+viewHeader\s*\(", app_js), (
        "Theme 0: viewHeader() helper must be defined in app.js."
    )


def test_view_header_class_styled(styles_css: str) -> None:
    """Theme 0: .view-header / .view-header-title / .view-header-sub must
    be defined in styles.css so the helper renders consistently."""
    for cls in (".view-header", ".view-header-title", ".view-header-sub"):
        assert cls in styles_css, (
            f"Theme 0: {cls} must be styled in styles.css."
        )


def test_view_header_used_by_every_render_function(app_js: str) -> None:
    """Every top-level render* function (except the Guide doc viewer, which
    has its own layout) MUST emit its title via viewHeader(). Catching
    drift early prevents the Operations/Logs 'messy UI' regression that
    Theme 0 set out to fix."""
    expected_titles = {
        "renderOverview":    "Published Inventory",
        "renderAdapters":    "Adapters",
        "renderLiveRun":     "Live Run",
        "renderHistory":     "Run History",
        "renderMaintenance": "Operations",
        "renderLogs":        "Logs",
    }
    for fn_name, title in expected_titles.items():
        body = re.search(
            rf"function\s+{fn_name}\s*\([^)]*\)\s*\{{(.*?)\n\}}",
            app_js, flags=re.DOTALL,
        )
        assert body, f"{fn_name}() not found in app.js"
        assert re.search(
            rf'viewHeader\(\s*["\']{re.escape(title)}["\']', body.group(1)
        ), (
            f"Theme 0: {fn_name}() must emit its '{title}' title via "
            "viewHeader() — not a bare h2 or hand-rolled flex wrapper."
        )


def test_no_legacy_hand_rolled_view_header_remains(app_js: str) -> None:
    """No render* site may still hand-roll the old
    `<h2 class="text-xs uppercase tracking-wider text-slate-500">VIEW</h2>`
    pattern. The helper exists; everyone uses it."""
    # We allow the pattern to appear in nested contexts (h3 column headers,
    # form labels, inline stat labels). The legacy *view-level* shape was
    # `<h2 class="text-xs uppercase tracking-wider text-slate-500">` —
    # that's what we're forbidding.
    assert not re.search(
        r'<h2\s+class="text-xs uppercase tracking-wider text-slate-500">',
        app_js,
    ), (
        "Theme 0: a render function still hand-rolls the legacy view-header "
        "<h2>. Use viewHeader() instead so the typography stays pinned."
    )


# ---------- Logs stage pane responsive grid (Theme 0) ------------------------


def test_logs_stage_grid_is_responsive(app_js: str, styles_css: str) -> None:
    """Theme 0: the stage-logs aside used to be a fixed 20rem column at
    lg+ which ate horizontal space on narrow desktops. The new
    .logs-stage-grid CSS class must own the column template, and the
    JS markup must reference it instead of inlining the grid template."""
    # JS must use the class, not a Tailwind arbitrary-value template.
    assert "logs-stage-grid" in app_js, (
        "Theme 0: stage logs pane must use the .logs-stage-grid class."
    )
    assert "lg:grid-cols-[20rem,1fr]" not in app_js, (
        "Theme 0: legacy fixed 20rem column template must be removed."
    )
    # CSS must define the responsive template.
    assert ".logs-stage-grid" in styles_css, (
        "Theme 0: .logs-stage-grid must be defined in styles.css."
    )
    assert re.search(
        r"\.logs-stage-grid\s*\{[^}]*grid-template-columns",
        styles_css, flags=re.DOTALL,
    ), "Theme 0: .logs-stage-grid must define grid-template-columns."


# ---------- Dry-run preview modal (Theme 1e) ---------------------------------


def test_preview_dialog_present(index_html: str) -> None:
    """Theme 1e: a #preview-dialog modal must exist in index.html, with the
    title slot, body slot, and 'Run for real' confirm button."""
    assert 'id="preview-dialog"' in index_html, (
        "Theme 1e: index.html must declare <dialog id='preview-dialog'>."
    )
    assert 'id="pv-title"' in index_html
    assert 'id="pv-body"' in index_html
    assert 'id="pv-go"' in index_html, (
        "Theme 1e: preview dialog must expose a #pv-go 'Run for real' button."
    )


def test_preview_dialog_styled(styles_css: str) -> None:
    """Theme 1e: the preview dialog needs a wider modal + stat/list styling
    so long file paths and big counts don't overflow."""
    assert "dialog.preview-dialog" in styles_css, (
        "Theme 1e: styles.css must define dialog.preview-dialog overrides."
    )
    assert ".preview-stat" in styles_css and ".preview-list" in styles_css, (
        "Theme 1e: stat-row and sample-list classes must be styled."
    )


def test_open_preview_modal_defined(app_js: str) -> None:
    """Theme 1e: openPreviewModal() owns the GET-preview → modal → run flow."""
    assert "function openPreviewModal" in app_js or "openPreviewModal({" in app_js, (
        "Theme 1e: openPreviewModal() must be defined and invoked."
    )
    # Renderers map must wire all three ops.
    assert "PREVIEW_RENDERERS" in app_js, (
        "Theme 1e: PREVIEW_RENDERERS map must dispatch per-op rendering."
    )
    for op_key in ('clean', 'rollback', '"vacuum-db"'):
        assert op_key in app_js, (
            f"Theme 1e: PREVIEW_RENDERERS must include {op_key}."
        )


def test_maintenance_cards_have_preview_buttons(app_js: str) -> None:
    """Theme 1e: each Operations card must expose a Preview button alongside Run."""
    maint = re.search(
        r"function\s+renderMaintenance\s*\([^)]*\)\s*\{(.*?)\n\}",
        app_js, flags=re.DOTALL,
    )
    assert maint, "renderMaintenance not found"
    body = maint.group(1)
    for pid in ("mv-preview", "mc-preview", "mr-preview"):
        assert pid in body, (
            f"Theme 1e: renderMaintenance must wire a Preview button #{pid}."
        )


def test_preview_endpoints_used_by_ui(app_js: str) -> None:
    """Theme 1e: the Preview clicks must hit the GET /api/{op}/preview endpoints."""
    for url in ("/api/vacuum-db/preview", "/api/clean/preview", "/api/rollback/preview"):
        assert url in app_js, (
            f"Theme 1e: app.js must call {url} from a Preview handler."
        )


# ---------- Theme 4c: Logs grep search box ---------------------------------


def test_logs_grep_search_box_present(app_js: str) -> None:
    """Theme 4c: Stage Logs pane must include a regex search form with the
    documented input ids so future renames don't silently break the wire-up."""
    for input_id in ("lg-pattern", "lg-stage", "lg-from", "lg-to", "lg-limit", "lg-go", "lg-results"):
        assert f'id="{input_id}"' in app_js, (
            f"Theme 4c: Stage Logs pane must expose #{input_id}."
        )


def test_logs_grep_calls_endpoint(app_js: str) -> None:
    """Theme 4c: search must hit the dashboard's logs grep endpoint."""
    assert "/api/logs/grep?" in app_js, (
        "Theme 4c: app.js must call GET /api/logs/grep with query params."
    )


def test_logs_grep_open_button_jumps_to_file(app_js: str) -> None:
    """Theme 4c: each result row's Open button must select the matching
    stage-file-btn so the existing tail viewer kicks in (no duplicate
    fetch logic, no separate viewer)."""
    assert "lg-open-btn" in app_js, "Theme 4c: result rows must mark Open buttons with class lg-open-btn."
    assert "stage-file-btn" in app_js, "Theme 4c: Open must dispatch through stage-file-btn click."



def test_failures_summary_card_present(app_js: str) -> None:
    """Theme 2b: Pipeline (history) view must mount a placeholder for the
    Top failure modes card and call the dashboard endpoint to populate it."""
    assert 'id="failures-summary-card"' in app_js, (
        "Theme 2b: history view must include #failures-summary-card placeholder."
    )
    assert "/api/status/failures-summary?last=" in app_js, (
        "Theme 2b: app.js must call GET /api/status/failures-summary."
    )


def test_failures_summary_row_navigates_to_logs(app_js: str) -> None:
    """Theme 2c: clicking a failure-mode row prefills the Logs grep form via
    sessionStorage and navigates to /logs."""
    assert "failures-row" in app_js, (
        "Theme 2c: failure-mode rows must be marked with class failures-row."
    )
    assert "yengo-dashboard:logsGrepPrefill" in app_js, (
        "Theme 2c: row click must seed the documented sessionStorage prefill key."
    )


# ---------- Theme 3b: runtime footprint -----------------------------------


def test_system_dialog_has_footprint_section(index_html: str, app_js: str) -> None:
    """Theme 3b: System dialog must expose a footprint container and app.js
    must populate it on dialog open via paintSystemDialog."""
    assert 'id="system-footprint"' in index_html, (
        "Theme 3b: index.html must declare #system-footprint inside the system dialog."
    )
    assert "_loadFootprint" in app_js, (
        "Theme 3b: paintSystemDialog must call _loadFootprint."
    )


def test_runtime_info_endpoint_called(app_js: str) -> None:
    """Theme 3b: footprint must come from /api/runtime-info (cockpit principle
    #6 — never read disk directly from the browser)."""
    assert "/api/runtime-info" in app_js, (
        "Theme 3b: app.js must call GET /api/runtime-info."
    )


def test_clean_target_dropdown_decorated(app_js: str) -> None:
    """Theme 3b: Clean target dropdown must show per-target byte estimates."""
    assert "_decorateCleanTargets" in app_js, (
        "Theme 3b: clean form mount must invoke _decorateCleanTargets."
    )
    assert "_CLEAN_TARGET_BYTE_KEYS" in app_js, (
        "Theme 3b: target→bytes mapping must be present so options show estimates."
    )


# ---------- Theme 13b: Activity timeline -----------------------------------


def test_activity_nav_and_view_present(index_html: str) -> None:
    """Theme 13b: Activity nav button + view section must exist in the SPA shell."""
    assert 'data-nav="activity"' in index_html, (
        "Theme 13b: index.html must declare a data-nav=\"activity\" sidebar entry."
    )
    assert 'id="view-activity"' in index_html, (
        "Theme 13b: index.html must declare a #view-activity section for the renderer."
    )


def test_activity_endpoint_and_renderer_present(app_js: str) -> None:
    """Theme 13b: app.js must wire renderActivity and call /api/activity."""
    assert "renderActivity" in app_js, (
        "Theme 13b: app.js must define renderActivity and register it in RENDERERS."
    )
    assert "/api/activity" in app_js, (
        "Theme 13b: app.js must call GET /api/activity (no client-side merge)."
    )
    # Kind chips drive the CLI's --kinds filter.
    assert "activity-chip" in app_js, (
        "Theme 13b: kind-filter chips must be present so users can scope the timeline."
    )


def test_inventory_check_endpoint_and_block_wired(app_js: str) -> None:
    """Theme 14b: app.js must call /api/inventory/check and render an
    integrity block with badge + per-issue table on the Library/Overview view."""
    assert "/api/inventory/check" in app_js, (
        "Theme 14b: app.js must call GET /api/inventory/check from renderOverview."
    )
    assert "integrityBlock" in app_js, (
        "Theme 14b: app.js must define integrityBlock() that renders the badge + table."
    )
    assert "id=\"integrity-block\"" in app_js, (
        "Theme 14b: integrity block must carry a stable id so pin tests + future "
        "interactions can target it."
    )
    # Both Theme 14a issue kinds must be reachable from the renderer.
    assert "missing_file" in app_js
    assert "orphan_file" in app_js


def test_inventory_mutation_modal_wired(app_js: str) -> None:
    """Theme 14c3: app.js must offer Preview→Apply modal entries on the
    integrity block and call the new POST endpoints."""
    # Buttons are tagged so the delegated handler can find them after each
    # renderOverview() rebuild — the wiring helper is the contract surface.
    assert "data-inv-op" in app_js, (
        "Theme 14c3: integrity block must carry data-inv-op buttons."
    )
    assert "_wireInventoryActionButtons" in app_js, (
        "Theme 14c3: app.js must wire click handlers for the inventory op buttons."
    )
    assert "openInventoryMutationModal" in app_js, (
        "Theme 14c3: a dedicated modal opener must drive the Preview→Apply flow."
    )
    assert "/api/inventory/preview" in app_js, (
        "Theme 14c3: modal must POST to /api/inventory/preview for the dry-run leg."
    )
    assert "/api/inventory/apply" in app_js, (
        "Theme 14c3: modal must POST to /api/inventory/apply for the commit leg."
    )
    # All three ops must be entry points so the operator can reach each from UI.
    for op in ("rebuild", "reconcile", "fix"):
        assert f'data-inv-op="{op}"' in app_js, (
            f"Theme 14c3: missing button for inventory op {op!r}."
        )


def test_operations_page_consumes_ops_catalog(app_js: str) -> None:
    """Theme 16b: renderMaintenance must fetch /api/ops/catalog and use it
    to drive section placement so a backend-only re-classification of an
    op (e.g., moving "clean" from maintenance → destructive) reshapes the
    Operations page without a coordinated cockpit release."""
    assert "/api/ops/catalog" in app_js, (
        "Theme 16b: Operations page must call /api/ops/catalog for blast-radius taxonomy."
    )
    assert "_fetchOpsCatalog" in app_js, (
        "Theme 16b: catalog fetch must be a named helper so callers can reuse it."
    )
    assert "OPS_CARD_SPECS" in app_js, (
        "Theme 16b: card-body specs must be keyed by catalog op token, not section."
    )
    # async signature — render must await the catalog before painting.
    assert "async function renderMaintenance" in app_js, (
        "Theme 16b: renderMaintenance must be async so it can await the catalog."
    )
    # data-op attribute carries the catalog op token through to the DOM so
    # 16c's typed-confirm can look up reversibility/scope without parsing labels.
    assert "data-op=" in app_js, (
        "Theme 16b: rendered cards must carry data-op so cross-cutting "
        "typed-confirm logic can look up the catalog row."
    )


def test_destructive_buttons_have_global_typed_confirm_guard(app_js: str) -> None:
    """Theme 16c acceptance criterion (verbatim): a button declared
    `reversible: false` and `preview_supported: false` always presents a
    typed-confirm dialog regardless of which view hosts it.

    The guard is implemented as a capture-phase document click listener so
    it intercepts before any view-local handler can run, and the strict
    catalog check (both flags negative) matches the acceptance text.
    """
    assert "_opsCatalogConfirmGuard" in app_js, (
        "Theme 16c: a named confirm-guard function must exist so the "
        "capture-phase contract is auditable."
    )
    assert "_ensureOpsCatalogGuard" in app_js, (
        "Theme 16c: install helper must be a named function reachable "
        "from boot and from renderMaintenance."
    )
    assert 'addEventListener("click", _opsCatalogConfirmGuard, true)' in app_js, (
        "Theme 16c: guard must be registered with capture=true so it "
        "intercepts before view-local click handlers."
    )
    assert "entry.reversible === false && entry.preview_supported === false" in app_js, (
        "Theme 16c: guard's predicate must mirror the acceptance criterion "
        "exactly — reversible=false AND preview_supported=false."
    )
    assert "_ensureOpsCatalogGuard();" in app_js, (
        "Theme 16c: guard must be installed at boot so destructive buttons "
        "on other views are also covered, not just Operations."
    )


def test_maint_card_uses_flex_column_for_equal_height(app_js: str) -> None:
    """Theme 0: Operations cards must stretch to the row's height and pin
    their action row to the bottom so a tall card next to a short card
    doesn't leave a ragged button alignment.

    Implemented by giving the card section ``flex flex-col`` and the body
    container ``flex-1`` / action row ``mt-auto``.
    """
    assert 'class="maint-card flex flex-col' in app_js, (
        "Theme 0: maintCard root must be a flex column so children stretch."
    )
    assert '<div class="flex-1">${opts.body}</div>' in app_js, (
        "Theme 0: body wrapper must be flex-1 so it absorbs vertical slack."
    )
    assert 'class="flex gap-2 mt-auto"' in app_js, (
        "Theme 0: action-row must use mt-auto so buttons hug the bottom edge."
    )


def test_taxonomy_section_present_in_overview(app_js: str) -> None:
    """Theme 5: Library/Overview view exposes a Taxonomy sub-section that
    consumes /api/tags and /api/levels and renders Tag + Level usage tables.

    The acceptance text calls for a "Taxonomy" sub-section that pins the
    new tables under the Library nav. The cockpit currently merges Library
    into the Overview view; this test pins the section, the loader, and
    the two table renderers.
    """
    assert 'id="taxonomy-section"' in app_js, (
        "Theme 5: a stable id must exist so the lazy loader can target it."
    )
    assert "_loadTaxonomySection" in app_js, (
        "Theme 5: a named loader must exist so the fetch is auditable."
    )
    assert '"/api/tags"' in app_js and '"/api/levels"' in app_js, (
        "Theme 5: loader must hit both Theme 5 endpoints."
    )
    assert "function taxonomyTable" in app_js, (
        "Theme 5: a table renderer must exist for tag/level rows."
    )


def test_adapter_detail_route_wired(app_js: str) -> None:
    """Theme 6a: /adapters/{id} resolves via parsePath + showAdapterDetail.

    Pins the SPA route (parsePath returns adapterId), the shower function,
    the renderer, and the data-adapter-link click interceptor that turns
    table id-cell anchors into in-app navigation.
    """
    assert 'head === "adapters"' in app_js, (
        "Theme 6a: parsePath must recognise the /adapters/{id} prefix."
    )
    assert "function showAdapterDetail" in app_js
    assert "async function renderAdapterDetail" in app_js
    assert "data-adapter-link" in app_js, (
        "Theme 6a: adapterRow id cell must carry data-adapter-link for the click interceptor."
    )
    assert '/api/adapters/${encodeURIComponent(adapterId)}/details' in app_js, (
        "Theme 6a: renderer must call the new details endpoint."
    )


def test_adapter_detail_view_section_in_index_html() -> None:
    """Theme 6a: a #view-adapter-detail section must exist in the SPA shell."""
    html = (
        Path(__file__).resolve().parents[1] / "web" / "index.html"
    ).read_text(encoding="utf-8")
    assert 'id="view-adapter-detail"' in html


def test_ingest_state_reset_flow_wired(app_js: str) -> None:
    """Theme 6b: adapter detail page surfaces ingest-state tile + reset modal.

    Pins the ingest-state loader, the per-source endpoints, the reset button
    selector wired through the document-level click handler, and the
    typed-confirm requirement (confirmDialog with a verb token) before the
    POST goes out.
    """
    assert "_loadIngestStateSection" in app_js, (
        "Theme 6b: adapter detail must lazy-load the ingest-state tile."
    )
    assert "function ingestStateBlock" in app_js
    assert 'data-ingest-reset' in app_js, (
        "Theme 6b: reset button must carry data-ingest-reset for the click delegate."
    )
    assert 'async function openIngestStateResetModal' in app_js
    assert '/api/adapters/${encodeURIComponent(adapterId)}/ingest-state' in app_js
    assert '/api/adapters/${encodeURIComponent(adapterId)}/ingest-state/preview' in app_js
    assert '/api/adapters/${encodeURIComponent(adapterId)}/ingest-state/reset' in app_js
    # Typed-confirm gate must wrap the apply POST.
    assert "confirmDialog({" in app_js
    assert "verb: `reset ${adapterId}`" in app_js


def test_adapter_validation_section_wired(app_js: str) -> None:
    """Theme 7a: Library/Adapters list mounts the validate-all roll-up.

    Pins the section placeholder, the loader, the renderer, and the URL it
    fetches. Per-source FAIL rows render via a `[data-adapter-validation]`
    table the test suite can target.
    """
    assert 'id="adapter-validation-section"' in app_js
    assert "_loadAdapterValidationSection" in app_js
    assert "function adapterValidationBlock" in app_js
    assert "/api/adapter-config/validate" in app_js
    assert "data-adapter-validation" in app_js


def test_adapter_config_schema_section_wired(app_js: str) -> None:
    """Theme 7a: Adapter Detail page surfaces the schema-aware config block.

    The block consumes `/api/adapter-config/{id}` and renders adapter_kind,
    available_kinds, and (when present) a per-field requirement table marked
    with `[data-adapter-config-schema]` for downstream pinning.
    """
    assert 'id="adapter-config-schema-section"' in app_js
    assert "_loadAdapterConfigSchemaSection" in app_js
    assert "function adapterConfigSchemaBlock" in app_js
    assert "/api/adapter-config/${encodeURIComponent(adapterId)}" in app_js
    assert "data-adapter-config-schema" in app_js


def test_adapter_config_edit_form_wired(app_js: str) -> None:
    """Theme 7b: Adapter Detail offers an inline Edit/Remove form.

    The form posts to `/api/adapter-config/{id}/update` and `.../remove` and
    is rendered into the same host as the schema block; pinning these
    selectors guards against regressions during future UI refactors.
    """
    assert "data-adapter-config-edit-form" in app_js
    assert "data-adapter-config-edit-toggle" in app_js
    assert "data-adapter-config-remove" in app_js
    assert "_wireAdapterConfigForm" in app_js
    assert "/update" in app_js
    assert "/remove" in app_js


def test_adapter_bootstrap_section_wired(app_js: str) -> None:
    """Theme 7c: Adapter list mounts the bootstrap-from-folder wizard.

    Pin the form host + apply button + table selector so future refactors
    don't accidentally remove the only access path to bootstrap.
    """
    assert 'id="adapter-bootstrap-section"' in app_js
    assert "data-adapter-bootstrap-form" in app_js
    assert "data-adapter-bootstrap-apply" in app_js
    assert "data-adapter-bootstrap-table" in app_js
    assert "/api/adapter-config/bootstrap" in app_js
    assert "function adapterBootstrapBlock" in app_js


def test_pipeline_config_section_wired(app_js: str) -> None:
    """Theme 7d: Operations view exposes pipeline-config show + set form."""
    assert 'id="pipeline-config-section"' in app_js
    assert "data-pipeline-config-show" in app_js
    assert "data-pipeline-config-set-form" in app_js
    assert "data-pipeline-config-set-apply" in app_js
    assert "/api/pipeline-config" in app_js
    assert "_renderPipelineConfigSection" in app_js


def test_daily_view_wired(app_js: str) -> None:
    """Theme 8a: Daily nav + status badge + schedule table."""
    assert "renderDaily" in app_js
    assert 'daily:      ["daily"],' in app_js or 'daily:["daily"]' in app_js
    assert "data-daily-status" in app_js
    assert "data-daily-list" in app_js
    assert "data-daily-table" in app_js
    assert "/api/daily/status" in app_js
    assert "/api/daily/list" in app_js


def test_daily_nav_in_index(index_html: str) -> None:
    """Theme 8a: sidebar carries the Daily nav button."""
    assert 'data-nav="daily"' in index_html
    assert 'id="view-daily"' in index_html


def test_daily_preview_wired(app_js: str) -> None:
    """Theme 8b: per-row Preview button hits /api/daily/preview."""
    assert "_runDailyPreview" in app_js
    assert "data-daily-preview-btn" in app_js
    assert "data-daily-preview-target" in app_js
    assert "/api/daily/preview" in app_js


def test_daily_cancel_wired(app_js: str) -> None:
    """Theme 8c: per-row Cancel button → preview-then-confirm-then-apply."""
    assert "_runDailyCancel" in app_js
    assert "data-daily-cancel-btn" in app_js
    assert "/api/daily/cancel/preview" in app_js
    assert "/api/daily/cancel/apply" in app_js
    assert "confirmDialog" in app_js


def test_daily_backfill_wired(app_js: str) -> None:
    """Theme 8d: status block carries a Backfill missing button."""
    assert "_runDailyBackfill" in app_js
    assert "data-daily-backfill-btn" in app_js
    assert "/api/daily/backfill/preview" in app_js
    assert "/api/daily/backfill/apply" in app_js


def test_runs_diff_wired(app_js: str) -> None:
    """Theme 9: history page exposes per-row checkbox + Compare runs button."""
    assert "runs-diff-check" in app_js
    assert "data-runs-diff-compare" in app_js
    assert "data-runs-diff-clear" in app_js
    assert "_runRunsDiff" in app_js
    assert "/api/runs/diff" in app_js
    assert "_runsDiffSelection" in app_js

