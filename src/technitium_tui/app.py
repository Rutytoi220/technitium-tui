"""Main Textual TUI application for Technitium DNS Server (tnt-tui)."""

from __future__ import annotations

import json
from typing import Any

from textual import events, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label, ListItem, ListView, Static

from .api import TechnitiumAPI, TechnitiumError
from .config import AppConfig
from .settings_meta import HIDDEN_SETTINGS, SETTINGS_TABS, get_setting_meta
from .modals import (
    AddRecordModal,
    ConfirmModal,
    CreateZoneModal,
    EditSettingModal,
    HelpModal,
    InputModal,
    LoginModal,
)

TABS: list[tuple[str, str, str]] = [
    ("dashboard", "1", "◈  Dashboard"),
    ("zones", "2", "⊞  Zones"),
    ("cache", "3", "◫  Cache"),
    ("allowed", "4", "✓  Allowed"),
    ("blocked", "5", "✕  Blocked"),
    ("apps", "6", "◰  Apps"),
    ("dnsclient", "7", "⌕  DNS Client"),
    ("settings", "8", "⚙  Settings"),
    ("dhcp", "9", "⇄  DHCP"),
    ("admin", "0", "◉  Admin"),
    ("logs", "-", "≡  Logs"),
]

STATS_RANGES = ["LastHour", "LastDay", "LastWeek", "LastMonth", "LastYear"]

DASH_SUBVIEWS = [
    ("topDomains", "Top Domains"),
    ("topBlocked", "Top Blocked Domains"),
    ("topClients", "Top Clients"),
]

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int | float], width: int = 52) -> str:
    if not values:
        return "─" * min(width, 24)
    # Downsample or pad to fit width
    if len(values) > width:
        step = len(values) / width
        sampled = [max(values[int(i * step) : max(int(i * step) + 1, int((i + 1) * step))]) for i in range(width)]
    else:
        sampled = list(values)
    mx = max(sampled) if sampled else 0
    if mx <= 0:
        return SPARK_CHARS[0] * len(sampled)
    out = []
    for v in sampled:
        idx = min(len(SPARK_CHARS) - 1, int((v / mx) * (len(SPARK_CHARS) - 1)))
        out.append(SPARK_CHARS[idx])
    return "".join(out)


def fmt_num(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


def fmt_pct(part: Any, total: Any) -> str:
    try:
        t = float(total)
        p = float(part)
        if t <= 0:
            return "0.0%"
        return f"{(p / t) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"


def fmt_setting_val(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        if not v:
            return "(empty)"
        if len(v) <= 2:
            return ", ".join(str(x) for x in v)
        return f"[{len(v)} items] {v[0]}, …"
    if isinstance(v, dict):
        return json.dumps(v)
    if v is None or v == "":
        return "(none)"
    return str(v)


def _match_section(key: str, prefixes: tuple[str, ...]) -> bool:
    if not prefixes:
        return True
    kl = key.lower()
    return any(kl.startswith(p.lower()) for p in prefixes)


class TechnitiumApp(App):
    """Full-featured Technitium DNS Server TUI (tnt-tui)."""

    TITLE = "Technitium DNS"
    CSS = """
    Screen {
        background: ansi_default;
        color: #eef0f7;
    }

    #body {
        height: 1fr;
        background: transparent;
    }

    #sidebar {
        width: 20;
        background: transparent;
        border-right: solid #2a2d3d;
        padding: 1 0;
    }

    #nav-list {
        background: transparent;
        border: none;
        height: 1fr;
    }

    #nav-list > ListItem {
        padding: 0 2;
        height: 2;
        content-align: left middle;
        color: #9aa0b8;
        background: transparent;
    }

    #nav-list > ListItem.--highlight {
        background: #252942;
        color: #eef0f7;
        text-style: bold;
    }

    #nav-list:focus > ListItem.--highlight {
        background: #4c8bf5;
        color: #ffffff;
        text-style: bold;
    }

    #server-badge {
        padding: 1 2 0 2;
        color: #7c829d;
        height: auto;
        background: transparent;
    }

    #main-pane {
        width: 1fr;
        background: transparent;
    }

    #top-bar {
        height: 3;
        background: transparent;
        border-bottom: solid #2a2d3d;
        padding: 0 2;
        align-vertical: middle;
    }

    #view-title {
        width: 1fr;
        color: #eef0f7;
        text-style: bold;
        content-align: left middle;
        background: transparent;
    }

    #top-badge {
        width: auto;
        color: #74c0fc;
        background: transparent;
        border: round #2c4a7c;
        padding: 0 1;
        content-align: right middle;
    }

    #filter-bar {
        display: none;
        height: 3;
        margin: 0 1;
        background: transparent;
        border: round #4c8bf5;
    }

    #filter-bar.visible {
        display: block;
    }

    #dash-summary {
        display: none;
        height: auto;
        padding: 1 2 0 2;
        background: transparent;
    }

    #dash-summary.visible {
        display: block;
    }

    #dns-client-bar {
        display: none;
        height: 3;
        padding: 0 1;
        background: transparent;
    }

    #dns-client-bar.visible {
        display: block;
    }

    #dns-domain { width: 1fr; background: transparent; }
    #dns-type { width: 10; background: transparent; margin-left: 1; }
    #dns-server { width: 18; background: transparent; margin-left: 1; }
    #dns-proto { width: 10; background: transparent; margin-left: 1; }
    #dns-go { width: 12; margin-left: 1; }

    #log-viewer {
        display: none;
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
        background: transparent;
        color: #d0d4e4;
    }

    #log-viewer.visible {
        display: block;
    }

    #content-table {
        height: 1fr;
        background: transparent;
        border: none;
        padding: 0 1;
    }

    #content-table.hidden {
        display: none;
    }

    #content-table > .datatable--header {
        background: transparent;
        color: #858ba3;
        text-style: bold;
    }

    #content-table > .datatable--cursor {
        background: #252942;
        color: #ffffff;
        text-style: bold;
    }

    #content-table:focus > .datatable--cursor {
        background: #4c8bf5;
        color: #ffffff;
        text-style: bold;
    }

    #status-line {
        height: 2;
        padding: 0 2;
        border-top: solid #2a2d3d;
        background: transparent;
        color: #858ba3;
    }
    """

    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=False),
        Binding("ctrl+c", "quit_app", "Quit", show=False, priority=True),
        Binding("question_mark", "show_help", "Help", show=False),
        Binding("r", "refresh_view", "Refresh", show=False),
        Binding("tab", "toggle_sidebar", "Switch Pane", show=False),
        Binding("slash", "open_filter", "Filter", show=False),
        Binding("v", "cycle_subview", "Sub-view", show=False),
        Binding("[", "prev_range", "Prev Range", show=False),
        Binding("]", "next_range", "Next Range", show=False),
        Binding("a", "action_add", "Add", show=False),
        Binding("e", "action_edit", "Edit/Toggle", show=False),
        Binding("d", "action_delete", "Delete", show=False),
        Binding("b", "quick_block", "Quick Block", show=False),
        Binding("X", "action_flush", "Flush", show=False),
        Binding("T", "temp_disable_blocking", "Temp Disable", show=False),
        Binding("U", "force_update_blocklists", "Update Blocklists", show=False),
        Binding("L", "open_login", "Login", show=False),
        Binding("1", "tab_1", "Dashboard", show=False),
        Binding("2", "tab_2", "Zones", show=False),
        Binding("3", "tab_3", "Cache", show=False),
        Binding("4", "tab_4", "Allowed", show=False),
        Binding("5", "tab_5", "Blocked", show=False),
        Binding("6", "tab_6", "Apps", show=False),
        Binding("7", "tab_7", "DNS Client", show=False),
        Binding("8", "tab_8", "Settings", show=False),
        Binding("9", "tab_9", "DHCP", show=False),
        Binding("0", "tab_0", "Admin", show=False),
        Binding("minus", "tab_logs", "Logs", show=False),
    ]

    def __init__(self) -> None:
        super().__init__(ansi_color=True)
        self.cfg = AppConfig.load()
        self.api = TechnitiumAPI(self.cfg.server_url, self.cfg.token)

        self.current_tab: str = "dashboard"
        self.dash_sub_idx: int = 0
        self.settings_sec_idx: int = 0
        self.dhcp_sub: str = "leases"  # leases | scopes
        self.admin_sub: str = "users"  # users | groups | sessions | cluster
        self.apps_sub: str = "installed"  # installed | store
        self.logs_sub: str = "files"  # files | viewer | query

        self.active_zone: str = ""
        self.cache_domain: str = ""
        self.allowed_domain: str = ""
        self.blocked_domain: str = ""
        self.filter_text: str = ""

        self.rows_meta: list[tuple[str, Any]] = []
        self._last_stats: dict[str, Any] = {}
        self._last_settings: dict[str, Any] = {}
        self._server_name: str = ""
        self._server_version: str = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield ListView(
                    *[ListItem(Label(label), id=f"tab-{key}") for key, _, label in TABS],
                    id="nav-list",
                )
                yield Static("Not connected", id="server-badge")
            with Vertical(id="main-pane"):
                with Horizontal(id="top-bar"):
                    yield Static("Dashboard", id="view-title")
                    yield Static(f"{self.cfg.stats_type}", id="top-badge", markup=False)
                yield Input(placeholder="Filter rows… (Enter to apply, Esc to clear)", id="filter-bar")
                yield Static("", id="dash-summary")
                with Horizontal(id="dns-client-bar"):
                    yield Input(placeholder="Domain (e.g. archlinux.org)", id="dns-domain")
                    yield Input(value="A", placeholder="Type", id="dns-type")
                    yield Input(value="this-server", placeholder="Server", id="dns-server")
                    yield Input(value="Udp", placeholder="Proto", id="dns-proto")
                    yield Button("Resolve", variant="primary", id="dns-go")
                yield Static("", id="log-viewer")
                yield DataTable(id="content-table", cursor_type="row")
                yield Static("1-0,-: Tabs  j/k: Move  h/l: Back/Open  v: Sub-view  r: Refresh  ?: Help", id="status-line")

    def on_mount(self) -> None:
        table = self.query_one("#content-table", DataTable)
        table.zebra_stripes = False
        table.focus()
        if not self.cfg.token:
            self.action_open_login()
        else:
            self._verify_session()

    def _set_status(self, msg: str) -> None:
        self.query_one("#status-line", Static).update(msg)

    def _update_badge(self, text: str) -> None:
        self.query_one("#top-badge", Static).update(text)

    def _update_server_badge(self) -> None:
        host = self.cfg.server_url.replace("http://", "").replace("https://", "")
        name = self._server_name or host
        ver = f" v{self._server_version}" if self._server_version else ""
        self.query_one("#server-badge", Static).update(f"[#51cf66]●[/] {name}\n[dim]{self.cfg.username}{ver}[/]")

    @work(thread=True)
    def _verify_session(self) -> None:
        try:
            info = self.api.session_info()
            srv = info.get("info") or {}
            self._server_name = str(srv.get("dnsServerDomain") or "")
            self._server_version = str(srv.get("version") or "")
            self.call_from_thread(self._update_server_badge)
            self.call_from_thread(self._load_tab)
        except Exception as exc:
            self.call_from_thread(self._open_login_with_error, str(exc))

    def _open_login_with_error(self, msg: str) -> None:
        self.push_screen(LoginModal(self.cfg.server_url, self.cfg.username, msg), self._handle_login)

    def action_open_login(self) -> None:
        self.push_screen(LoginModal(self.cfg.server_url, self.cfg.username), self._handle_login)

    def _handle_login(self, result: tuple[str, str, str, str] | None) -> None:
        if result is None:
            if not self.cfg.token:
                self._set_status("Not connected — press L to log in to your Technitium DNS server")
            return
        url, user, pw, tok = result
        self._do_login(url, user, pw, tok)

    @work(thread=True)
    def _do_login(self, url: str, user: str, pw: str, tok: str) -> None:
        self.call_from_thread(self._set_status, f"Connecting to {url}…")
        try:
            if tok:
                self.api.configure(url, tok)
                info = self.api.session_info()
                srv = info.get("info") or {}
                self._server_name = str(srv.get("dnsServerDomain") or "")
                self._server_version = str(srv.get("version") or "")
                self.cfg.server_url = url
                self.cfg.username = str(info.get("username") or user)
                self.cfg.token = tok
            else:
                body = self.api.login(url, user, pw)
                srv = body.get("info") or {}
                self._server_name = str(srv.get("dnsServerDomain") or "")
                self._server_version = str(srv.get("version") or "")
                self.cfg.server_url = url
                self.cfg.username = user
                self.cfg.token = self.api.token
            self.cfg.save()
            self.call_from_thread(self._update_server_badge)
            self.call_from_thread(self._load_tab)
        except Exception as exc:
            self.call_from_thread(self._open_login_with_error, str(exc))

    # --- Tab switching ---
    def _select_tab(self, tab_key: str) -> None:
        self.current_tab = tab_key
        self.filter_text = ""
        self.query_one("#filter-bar", Input).remove_class("visible")
        self.query_one("#filter-bar", Input).value = ""
        lv = self.query_one("#nav-list", ListView)
        for idx, (k, _, _) in enumerate(TABS):
            if k == tab_key:
                lv.index = idx
                break
        self._load_tab()
        if tab_key == "dnsclient":
            self.query_one("#dns-domain", Input).focus()
        else:
            self.query_one("#content-table", DataTable).focus()

    def action_tab_1(self) -> None: self._select_tab("dashboard")
    def action_tab_2(self) -> None: self._select_tab("zones")
    def action_tab_3(self) -> None: self._select_tab("cache")
    def action_tab_4(self) -> None: self._select_tab("allowed")
    def action_tab_5(self) -> None: self._select_tab("blocked")
    def action_tab_6(self) -> None: self._select_tab("apps")
    def action_tab_7(self) -> None: self._select_tab("dnsclient")
    def action_tab_8(self) -> None: self._select_tab("settings")
    def action_tab_9(self) -> None: self._select_tab("dhcp")
    def action_tab_0(self) -> None: self._select_tab("admin")
    def action_tab_logs(self) -> None: self._select_tab("logs")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "nav-list" and event.item.id and event.item.id.startswith("tab-"):
            self._select_tab(event.item.id[4:])

    def action_toggle_sidebar(self) -> None:
        nav = self.query_one("#nav-list", ListView)
        table = self.query_one("#content-table", DataTable)
        if nav.has_focus:
            table.focus()
        else:
            nav.focus()

    def action_refresh_view(self) -> None:
        self._load_tab()

    # --- Loaders ---
    def _configure_widgets_for_tab(self) -> None:
        dash = self.query_one("#dash-summary", Static)
        dns_bar = self.query_one("#dns-client-bar", Horizontal)
        log_view = self.query_one("#log-viewer", Static)
        table = self.query_one("#content-table", DataTable)

        dash.set_class(self.current_tab in ("dashboard", "settings"), "visible")
        dns_bar.set_class(self.current_tab == "dnsclient", "visible")
        show_log = self.current_tab == "logs" and self.logs_sub == "viewer"
        log_view.set_class(show_log, "visible")
        table.set_class(show_log, "hidden")

    def _load_tab(self) -> None:
        self._configure_widgets_for_tab()
        if self.current_tab == "dnsclient":
            self.query_one("#view-title", Static).update("DNS Client — Live Query Resolver")
            self._update_badge("Enter domain & press Enter")
            self._set_status("Type domain, Tab between fields, Enter to resolve • Esc to return to table")
            return
        self._fetch_tab_worker(
            self.current_tab,
            self.cfg.stats_type,
            self.active_zone,
            self.cache_domain,
            self.allowed_domain,
            self.blocked_domain,
            self.dhcp_sub,
            self.admin_sub,
            self.apps_sub,
            self.logs_sub,
        )

    @work(thread=True, exclusive=True)
    def _fetch_tab_worker(
        self,
        tab: str,
        stats_type: str,
        active_zone: str,
        cache_domain: str,
        allowed_domain: str,
        blocked_domain: str,
        dhcp_sub: str,
        admin_sub: str,
        apps_sub: str,
        logs_sub: str,
    ) -> None:
        self.call_from_thread(self._set_status, "Loading…")
        try:
            if tab == "dashboard":
                data = self.api.get_stats(stats_type)
                self._last_stats = data
                self.call_from_thread(self._render_dashboard, data)
            elif tab == "zones":
                if active_zone:
                    data = self.api.get_records(active_zone)
                    self.call_from_thread(self._render_zone_records, active_zone, data)
                else:
                    data = self.api.list_zones()
                    self.call_from_thread(self._render_zones, data)
            elif tab == "cache":
                data = self.api.list_cache(cache_domain)
                self.call_from_thread(self._render_tree_list, "Cache", cache_domain, data, "cache")
            elif tab == "allowed":
                data = self.api.list_allowed(allowed_domain)
                self.call_from_thread(self._render_tree_list, "Allowed Zones", allowed_domain, data, "allowed")
            elif tab == "blocked":
                data = self.api.list_blocked(blocked_domain)
                self.call_from_thread(self._render_tree_list, "Blocked Zones", blocked_domain, data, "blocked")
            elif tab == "apps":
                if apps_sub == "store":
                    data = self.api.list_store_apps()
                    self.call_from_thread(self._render_store_apps, data)
                else:
                    data = self.api.list_apps()
                    self.call_from_thread(self._render_installed_apps, data)
            elif tab == "settings":
                data = self.api.get_settings()
                self._last_settings = data
                self.call_from_thread(self._render_settings, data)
            elif tab == "dhcp":
                if dhcp_sub == "scopes":
                    data = self.api.list_dhcp_scopes()
                    self.call_from_thread(self._render_dhcp_scopes, data)
                else:
                    data = self.api.list_dhcp_leases()
                    self.call_from_thread(self._render_dhcp_leases, data)
            elif tab == "admin":
                if admin_sub == "users":
                    data = self.api.list_users()
                    self.call_from_thread(self._render_users, data)
                elif admin_sub == "groups":
                    data = self.api.list_groups()
                    self.call_from_thread(self._render_groups, data)
                elif admin_sub == "sessions":
                    data = self.api.list_sessions()
                    self.call_from_thread(self._render_sessions, data)
                else:
                    data = self.api.get_cluster_state()
                    self.call_from_thread(self._render_cluster, data)
            elif tab == "logs":
                if logs_sub == "files":
                    data = self.api.list_logs()
                    self.call_from_thread(self._render_log_files, data)
                elif logs_sub == "query":
                    apps = self.api.list_apps().get("apps") or []
                    qapp = None
                    for app in apps:
                        for da in app.get("dnsApps") or []:
                            if da.get("isQueryLogger"):
                                qapp = (app["name"], da["classPath"])
                                break
                        if qapp:
                            break
                    if qapp:
                        qdata = self.api.query_logs(qapp[0], qapp[1], qname=self.filter_text)
                        self.call_from_thread(self._render_query_logs, qdata)
                    else:
                        self.call_from_thread(self._set_status, "No Query Logger DNS App installed (install Query Logs (Sqlite) in Apps [6])")
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[#ff6b81]Error: {exc}[/]")

    def _reset_table(self, cols: list[str]) -> DataTable:
        table = self.query_one("#content-table", DataTable)
        table.clear(columns=True)
        for c in cols:
            table.add_column(c)
        self.rows_meta.clear()
        return table

    def _passes_filter(self, *fields: Any) -> bool:
        if not self.filter_text:
            return True
        needle = self.filter_text.lower()
        return any(needle in str(f).lower() for f in fields)

    # --- Renderers ---
    def _render_dashboard(self, data: dict[str, Any]) -> None:
        st = data.get("stats") or {}
        total = st.get("totalQueries", 0)
        noerr = st.get("totalNoError", 0)
        servfail = st.get("totalServerFailure", 0)
        nxdom = st.get("totalNxDomain", 0)
        refused = st.get("totalRefused", 0)
        auth = st.get("totalAuthoritative", 0)
        rec = st.get("totalRecursive", 0)
        cached = st.get("totalCached", 0)
        blocked = st.get("totalBlocked", 0)
        dropped = st.get("totalDropped", 0)
        clients = st.get("totalClients", 0)

        # Extract total series for sparkline
        chart = data.get("mainChartData") or {}
        datasets = chart.get("datasets") or []
        total_series = datasets[0].get("data", []) if datasets else []
        blocked_series = []
        for ds in datasets:
            if str(ds.get("label", "")).lower() == "blocked":
                blocked_series = ds.get("data", [])
                break

        summary = (
            f"[on #3b6fd8] [b]{fmt_num(total)}[/] Total [/] "
            f"[on #2f7d32] [b]{fmt_num(noerr)}[/] NoErr {fmt_pct(noerr, total)} [/] "
            f"[on #8d3232] [b]{fmt_num(servfail)}[/] Fail [/] "
            f"[on #4a4e5a] [b]{fmt_num(nxdom)}[/] NXDom {fmt_pct(nxdom, total)} [/] "
            f"[on #2a7b88] [b]{fmt_num(refused)}[/] Refused [/] "
            f"[on #1b7f79] [b]{fmt_num(rec)}[/] Rec {fmt_pct(rec, total)} [/] "
            f"[on #5e3d8f] [b]{fmt_num(cached)}[/] Cache {fmt_pct(cached, total)} [/] "
            f"[on #b57614] [b]{fmt_num(blocked)}[/] Blk {fmt_pct(blocked, total)} [/] "
            f"[on #2c5282] [b]{fmt_num(clients)}[/] Clients [/]\n"
            f"[dim]Zones:[/] [b]{fmt_num(st.get('zones', 0))}[/]  "
            f"[dim]Cache:[/] [b]{fmt_num(st.get('cachedEntries', 0))}[/]  "
            f"[dim]Allowed:[/] [b]{fmt_num(st.get('allowedZones', 0))}[/]  "
            f"[dim]Blocked:[/] [b]{fmt_num(st.get('blockedZones', 0))}[/]  "
            f"[dim]Block List:[/] [b #fcc419]{fmt_num(st.get('blockListZones', 0))}[/]  "
            f"[dim]Auth:[/] {fmt_num(auth)}  [dim]Drop:[/] {fmt_num(dropped)}\n"
            f"[#4c8bf5]Total  [/] [#74c0fc]{sparkline(total_series, 54)}[/]   "
            f"[#f59f00]Blocked[/] [#fcc419]{sparkline(blocked_series, 34)}[/]"
        )
        self.query_one("#dash-summary", Static).update(summary)

        sub_key, sub_label = DASH_SUBVIEWS[self.dash_sub_idx % len(DASH_SUBVIEWS)]
        self.query_one("#view-title", Static).update(f"Dashboard  •  {sub_label}")
        self._update_badge(f"{self.cfg.stats_type}  [ / ]  •  v: Switch Table")

        if sub_key == "topClients":
            table = self._reset_table(["#", "Client IP", "Domain / Host", "Queries", "Rate Limited"])
            for i, row in enumerate(data.get("topClients") or [], start=1):
                ip = row.get("name", "")
                dom = row.get("domain", "")
                if not self._passes_filter(ip, dom):
                    continue
                table.add_row(str(i), str(ip), str(dom), fmt_num(row.get("hits", 0)), "Yes" if row.get("rateLimited") else "No")
                self.rows_meta.append(("client", row))
        else:
            table = self._reset_table(["#", "Domain", "Hits"])
            src = data.get("topBlockedDomains" if sub_key == "topBlocked" else "topDomains") or []
            for i, row in enumerate(src, start=1):
                dom = row.get("name", "")
                if not self._passes_filter(dom):
                    continue
                table.add_row(str(i), str(dom), fmt_num(row.get("hits", 0)))
                self.rows_meta.append(("domain", dom))

        self._set_status("[ / ]: Time range  v: Switch Top Domains/Blocked/Clients  b: Block domain  a: Allow domain  T: Temp disable  r: Refresh")

    def _render_zones(self, data: dict[str, Any]) -> None:
        zones = data.get("zones") or []
        self.query_one("#view-title", Static).update(f"Zones ({len(zones)})")
        self._update_badge("Enter/l: Records • a: New • e: Toggle • d: Delete")
        table = self._reset_table(["Zone", "Type", "Status", "DNSSEC", "Internal"])
        for z in zones:
            name = z.get("name", "")
            ztype = z.get("type", "")
            if not self._passes_filter(name, ztype):
                continue
            status = "Disabled" if z.get("disabled") else "Enabled"
            table.add_row(name, ztype, status, str(z.get("dnssecStatus", "")), "Yes" if z.get("internal") else "No")
            self.rows_meta.append(("zone", z))
        self._set_status(f"{len(self.rows_meta)} zones • Enter/l: Inspect records  a: Create zone  e: Enable/Disable  d: Delete")

    def _render_zone_records(self, zone: str, data: dict[str, Any]) -> None:
        records = data.get("records") or []
        self.query_one("#view-title", Static).update(f"Zones  ›  {zone}  ({len(records)} records)")
        self._update_badge("h: Back • a: Add Record • d: Delete")
        table = self._reset_table(["Domain", "Type", "TTL", "Value", "Status"])
        for rec in records:
            dom = rec.get("name", "")
            rtype = rec.get("type", "")
            rdata = rec.get("rData") or {}
            val = (
                rdata.get("ipAddress")
                or rdata.get("cname")
                or rdata.get("nameServer")
                or rdata.get("text")
                or rdata.get("exchange")
                or rdata.get("ptrName")
                or rdata.get("primaryNameServer")
                or json.dumps(rdata)
            )
            if not self._passes_filter(dom, rtype, val):
                continue
            table.add_row(dom, rtype, str(rec.get("ttl", "")), str(val), "Disabled" if rec.get("disabled") else "Enabled")
            self.rows_meta.append(("record", {"zone": zone, "domain": dom, "type": rtype, "value": str(val)}))
        self._set_status(f"{len(self.rows_meta)} records in {zone} • h: Back to Zones  a: Add Record  d: Delete Record")

    def _render_tree_list(self, title: str, cur_domain: str, data: dict[str, Any], kind: str) -> None:
        zones = data.get("zones") or []
        records = data.get("records") or []
        bc = f"  ›  {cur_domain}" if cur_domain else ""
        self.query_one("#view-title", Static).update(f"{title}{bc}")
        self._update_badge("a: Add • d: Delete • X: Flush")
        table = self._reset_table(["Kind", "Name / Domain", "Info"])
        if cur_domain:
            table.add_row("..", "↰  .. (Up)", "")
            self.rows_meta.append(("tree_up", kind))
        for z in zones:
            if not self._passes_filter(z):
                continue
            table.add_row("zone", str(z), "")
            self.rows_meta.append((f"{kind}_zone", str(z)))
        for rec in records:
            dom = rec.get("name", "")
            rtype = rec.get("type", "")
            val = json.dumps(rec.get("rData") or {})
            if not self._passes_filter(dom, rtype, val):
                continue
            table.add_row(rtype, dom, val[:80])
            self.rows_meta.append((f"{kind}_rec", dom))
        self._set_status(f"{len(zones)} zones, {len(records)} records • Enter/l: Drill in  h: Up  a: Add  d: Delete  X: Flush")

    def _render_installed_apps(self, data: dict[str, Any]) -> None:
        apps = data.get("apps") or []
        self.query_one("#view-title", Static).update(f"DNS Apps — Installed ({len(apps)})")
        self._update_badge("v: App Store • e: Edit Config • d: Uninstall")
        table = self._reset_table(["App Name", "Version", "Modules"])
        for a in apps:
            name = a.get("name", "")
            mods = ", ".join(m.get("classPath", "").split(".")[-1] for m in (a.get("dnsApps") or []))
            if not self._passes_filter(name, mods):
                continue
            table.add_row(name, str(a.get("version", "")), mods)
            self.rows_meta.append(("app", a))
        self._set_status(f"{len(apps)} installed apps • v: Browse Store  e: Edit JSON Config  d: Uninstall")

    def _render_store_apps(self, data: dict[str, Any]) -> None:
        apps = data.get("storeApps") or []
        self.query_one("#view-title", Static).update(f"DNS Apps — Store ({len(apps)})")
        self._update_badge("v: Installed • Enter/a: Install")
        table = self._reset_table(["App Name", "Version", "Installed", "Description"])
        for a in apps:
            name = a.get("name", "")
            desc = a.get("description", "")
            if not self._passes_filter(name, desc):
                continue
            table.add_row(name, str(a.get("version", "")), "Yes" if a.get("installed") else "No", desc[:70])
            self.rows_meta.append(("store_app", a))
        self._set_status(f"{len(apps)} store apps • Enter/a: Install selected app  v: Back to Installed")

    def _render_settings(self, data: dict[str, Any]) -> None:
        sec_key, sec_label = SETTINGS_TABS[self.settings_sec_idx % len(SETTINGS_TABS)]
        self.query_one("#view-title", Static).update(f"Settings  •  {sec_label}")

        # Build clean section pill strip in dash-summary slot!
        pills = []
        for idx, (_, lbl) in enumerate(SETTINGS_TABS):
            if idx == self.settings_sec_idx % len(SETTINGS_TABS):
                pills.append(f"[on #4c8bf5] [b]{lbl}[/] [/]")
            else:
                pills.append(f"[dim] {lbl} [/]")
        self.query_one("#dash-summary", Static).update(" ".join(pills))
        self.query_one("#dash-summary", Static).add_class("visible")
        self._update_badge("[ / ]: Section • Enter/e: Edit • U: Update Blocklists")

        table = self._reset_table(["Setting", "Value", "Description"])
        rows: list[tuple[str, str, Any, str]] = []
        for k, v in data.items():
            if k in HIDDEN_SETTINGS:
                continue
            s_sec, label, desc = get_setting_meta(k)
            if sec_key != "all" and s_sec != sec_key:
                continue
            vstr = fmt_setting_val(v)
            if not self._passes_filter(k, label, vstr, desc):
                continue
            rows.append((k, label, v, desc))

        rows.sort(key=lambda r: r[1].lower())
        for k, label, v, desc in rows:
            if isinstance(v, bool):
                val_display = "[#51cf66]● ON[/]" if v else "[dim]○ OFF[/]"
            else:
                val_display = fmt_setting_val(v)[:42]
            table.add_row(label, val_display, desc)
            self.rows_meta.append(("setting", (k, v, label, desc)))

        self._set_status(
            f"{len(rows)} settings in {sec_label} • [ / ] or v: Switch section  Enter/e: Toggle/Edit  /: Search  T: Temp disable  U: Update blocklists"
        )

    def _render_dhcp_leases(self, data: dict[str, Any]) -> None:
        leases = data.get("leases") or []
        self.query_one("#view-title", Static).update(f"DHCP — Leases ({len(leases)})")
        self._update_badge("v: Scopes • e: Reserve/Dynamic • d: Remove")
        table = self._reset_table(["Scope", "IP Address", "MAC", "Hostname", "Type", "Expires"])
        for l in leases:
            if not self._passes_filter(l.get("address"), l.get("hostName"), l.get("hardwareAddress")):
                continue
            table.add_row(
                str(l.get("scope", "")),
                str(l.get("address", "")),
                str(l.get("hardwareAddress", "")),
                str(l.get("hostName", "")),
                str(l.get("type", "")),
                str(l.get("leaseExpires", "")),
            )
            self.rows_meta.append(("lease", l))
        self._set_status(f"{len(leases)} leases • v: Switch to Scopes  e: Toggle Reserved/Dynamic  d: Remove lease")

    def _render_dhcp_scopes(self, data: dict[str, Any]) -> None:
        scopes = data.get("scopes") or []
        self.query_one("#view-title", Static).update(f"DHCP — Scopes ({len(scopes)})")
        self._update_badge("v: Leases • e: Enable/Disable • d: Delete")
        table = self._reset_table(["Name", "Status", "Network", "Start", "End", "Interface"])
        for s in scopes:
            if not self._passes_filter(s.get("name"), s.get("networkAddress")):
                continue
            table.add_row(
                str(s.get("name", "")),
                "Enabled" if s.get("enabled") else "Disabled",
                str(s.get("networkAddress", "")),
                str(s.get("startingAddress", "")),
                str(s.get("endingAddress", "")),
                str(s.get("interfaceAddress", "")),
            )
            self.rows_meta.append(("scope", s))
        self._set_status(f"{len(scopes)} scopes • v: Switch to Leases  e: Enable/Disable  d: Delete scope")

    def _render_users(self, data: dict[str, Any]) -> None:
        users = data.get("users") or []
        self.query_one("#view-title", Static).update(f"Administration — Users ({len(users)})")
        self._update_badge("v: Groups/Sessions/Cluster • a: Create • d: Delete")
        table = self._reset_table(["Username", "Display Name", "Status", "Recent Login"])
        for u in users:
            table.add_row(
                str(u.get("username", "")),
                str(u.get("displayName", "")),
                "Disabled" if u.get("disabled") else "Active",
                str(u.get("recentSessionLoggedOn", "")),
            )
            self.rows_meta.append(("user", u))
        self._set_status("v: Cycle Users/Groups/Sessions/Cluster • a: Create User  d: Delete User")

    def _render_groups(self, data: dict[str, Any]) -> None:
        groups = data.get("groups") or []
        self.query_one("#view-title", Static).update(f"Administration — Groups ({len(groups)})")
        self._update_badge("v: Sessions/Cluster/Users")
        table = self._reset_table(["Group", "Description"])
        for g in groups:
            table.add_row(str(g.get("name", "")), str(g.get("description", "")))
            self.rows_meta.append(("group", g))
        self._set_status("v: Cycle Users/Groups/Sessions/Cluster")

    def _render_sessions(self, data: dict[str, Any]) -> None:
        sessions = data.get("sessions") or []
        self.query_one("#view-title", Static).update(f"Administration — Sessions ({len(sessions)})")
        self._update_badge("v: Cluster/Users/Groups • d: Revoke")
        table = self._reset_table(["User", "Type", "Token", "Last Seen", "Remote IP"])
        for s in sessions:
            table.add_row(
                str(s.get("username", "")),
                str(s.get("type", "")),
                str(s.get("partialToken", "")),
                str(s.get("lastSeen", "")),
                str(s.get("lastSeenRemoteAddress", "")),
            )
            self.rows_meta.append(("session", s))
        self._set_status("v: Cycle Users/Groups/Sessions/Cluster • d: Revoke selected session")

    def _render_cluster(self, data: dict[str, Any]) -> None:
        self.query_one("#view-title", Static).update("Administration — Cluster State")
        self._update_badge("v: Users/Groups/Sessions")
        table = self._reset_table(["Property", "Value"])
        for k, v in data.items():
            table.add_row(str(k), fmt_setting_val(v)[:90])
            self.rows_meta.append(("cluster", k))
        self._set_status("v: Cycle Users/Groups/Sessions/Cluster")

    def _render_log_files(self, data: dict[str, Any]) -> None:
        files = data.get("logFiles") or []
        self.query_one("#view-title", Static).update(f"Logs — Server Files ({len(files)})")
        self._update_badge("Enter/l: View • v: Query Logs • d: Delete")
        table = self._reset_table(["Log File", "Size"])
        for f in files:
            name = f.get("fileName", "")
            if not self._passes_filter(name):
                continue
            table.add_row(name, str(f.get("size", "")))
            self.rows_meta.append(("logfile", name))
        self._set_status("Enter/l: View log tail  v: Switch to Query Logs  d: Delete log  X: Delete all logs")

    def _render_query_logs(self, data: dict[str, Any]) -> None:
        entries = data.get("entries") or []
        self.query_one("#view-title", Static).update(f"Logs — Query Logs ({len(entries)})")
        self._update_badge("v: Server Files • /: Filter Domain")
        table = self._reset_table(["Time", "Client", "QName", "Type", "RCODE", "Response"])
        for e in entries:
            table.add_row(
                str(e.get("timestamp", ""))[11:19],
                str(e.get("clientIpAddress", "")),
                str(e.get("qname", "")),
                str(e.get("qtype", "")),
                str(e.get("rcode", "")),
                str(e.get("responseType", "")),
            )
            self.rows_meta.append(("qlog", e))
        self._set_status("v: Switch to Server Log Files • /: Filter by domain • r: Refresh")

    # --- DNS Client ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dns-go":
            self._run_dns_client()

    @work(thread=True)
    def _run_dns_client(self) -> None:
        dom = self.query_one("#dns-domain", Input).value.strip()
        qtype = self.query_one("#dns-type", Input).value.strip() or "A"
        srv = self.query_one("#dns-server", Input).value.strip() or "this-server"
        proto = self.query_one("#dns-proto", Input).value.strip() or "Udp"
        if not dom:
            return
        self.call_from_thread(self._set_status, f"Resolving {dom} ({qtype}) via {srv}…")
        try:
            data = self.api.resolve_query(dom, qtype, srv, proto)
            self.call_from_thread(self._render_dns_result, data)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[#ff6b81]Resolve error: {exc}[/]")

    def _render_dns_result(self, data: dict[str, Any]) -> None:
        res = data.get("result") or data
        meta = res.get("Metadata") or {}
        rcode = res.get("RCODE", "")
        rtt = meta.get("RoundTripTime", "")
        self.query_one("#view-title", Static).update(f"DNS Client  •  RCODE: {rcode}  ({rtt})")
        table = self._reset_table(["Section", "Name", "Type", "TTL", "Data"])
        for sec in ("Answer", "Authority", "Additional"):
            for rec in res.get(sec) or []:
                rdata = rec.get("RDATA") or {}
                val = (
                    rdata.get("IPAddress")
                    or rdata.get("Domain")
                    or rdata.get("NameServer")
                    or rdata.get("Text")
                    or rdata.get("Exchange")
                    or json.dumps(rdata)
                )
                table.add_row(sec, str(rec.get("Name", "")), str(rec.get("Type", "")), str(rec.get("TTL", "")), str(val))
                self.rows_meta.append(("dns_ans", rec))
        self._set_status(f"Resolved ({len(self.rows_meta)} records) • RCODE={rcode} • Server={meta.get('NameServer', '')}")
        self.query_one("#content-table", DataTable).focus()

    # --- Row activation & HJKL ---
    def _selected_meta(self) -> tuple[str, Any] | None:
        table = self.query_one("#content-table", DataTable)
        if 0 <= table.cursor_row < len(self.rows_meta):
            return self.rows_meta[table.cursor_row]
        return None

    def _activate_row(self) -> None:
        sel = self._selected_meta()
        if not sel:
            return
        kind, obj = sel
        if kind == "zone":
            self.active_zone = obj["name"]
            self._load_tab()
        elif kind == "tree_up":
            self._go_back()
        elif kind == "cache_zone":
            self.cache_domain = obj
            self._load_tab()
        elif kind == "allowed_zone":
            self.allowed_domain = obj
            self._load_tab()
        elif kind == "blocked_zone":
            self.blocked_domain = obj
            self._load_tab()
        elif kind == "setting":
            self._edit_setting(obj[0], obj[1])
        elif kind == "app":
            self._open_app_config(obj["name"])
        elif kind == "store_app":
            self._install_app_confirm(obj)
        elif kind == "logfile":
            self._view_log_file(obj)

    def _go_back(self) -> bool:
        if self.current_tab == "zones" and self.active_zone:
            self.active_zone = ""
            self._load_tab()
            return True
        if self.current_tab == "cache" and self.cache_domain:
            self.cache_domain = ".".join(self.cache_domain.split(".")[1:]) if "." in self.cache_domain else ""
            self._load_tab()
            return True
        if self.current_tab == "allowed" and self.allowed_domain:
            self.allowed_domain = ".".join(self.allowed_domain.split(".")[1:]) if "." in self.allowed_domain else ""
            self._load_tab()
            return True
        if self.current_tab == "blocked" and self.blocked_domain:
            self.blocked_domain = ".".join(self.blocked_domain.split(".")[1:]) if "." in self.blocked_domain else ""
            self._load_tab()
            return True
        if self.current_tab == "logs" and self.logs_sub == "viewer":
            self.logs_sub = "files"
            self._load_tab()
            return True
        return False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._activate_row()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-bar":
            self.filter_text = event.value.strip()
            event.input.remove_class("visible")
            self.query_one("#content-table", DataTable).focus()
            self._load_tab()
        elif event.input.id in ("dns-domain", "dns-type", "dns-server", "dns-proto"):
            self._run_dns_client()

    def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if isinstance(focused, Input):
            if event.key == "escape":
                event.stop()
                if focused.id == "filter-bar":
                    focused.remove_class("visible")
                    self.filter_text = ""
                    self._load_tab()
                self.query_one("#content-table", DataTable).focus()
            return

        nav = self.query_one("#nav-list", ListView)
        table = self.query_one("#content-table", DataTable)

        if nav.has_focus:
            if event.key == "j":
                event.stop()
                nav.action_cursor_down()
            elif event.key == "k":
                event.stop()
                nav.action_cursor_up()
            elif event.key == "l":
                event.stop()
                nav.action_select_cursor()
        elif self.current_tab == "logs" and self.logs_sub == "viewer":
            if event.key in ("h", "escape"):
                event.stop()
                self._go_back()
        elif table.has_focus:
            if event.key == "j":
                event.stop()
                table.action_cursor_down()
            elif event.key == "k":
                event.stop()
                table.action_cursor_up()
            elif event.key == "g":
                event.stop()
                table.move_cursor(row=0)
            elif event.key == "G":
                event.stop()
                if table.row_count > 0:
                    table.move_cursor(row=table.row_count - 1)
            elif event.key == "l":
                event.stop()
                self._activate_row()
            elif event.key == "h":
                event.stop()
                if not self._go_back():
                    nav.focus()

    # --- Context actions ---
    def action_open_filter(self) -> None:
        fb = self.query_one("#filter-bar", Input)
        fb.add_class("visible")
        fb.focus()

    def action_prev_range(self) -> None:
        if self.current_tab == "dashboard":
            idx = (STATS_RANGES.index(self.cfg.stats_type) - 1) % len(STATS_RANGES)
            self.cfg.stats_type = STATS_RANGES[idx]
            self.cfg.save()
            self._load_tab()
        elif self.current_tab == "settings":
            self.settings_sec_idx = (self.settings_sec_idx - 1) % len(SETTINGS_TABS)
            if self._last_settings:
                self._render_settings(self._last_settings)

    def action_next_range(self) -> None:
        if self.current_tab == "dashboard":
            idx = (STATS_RANGES.index(self.cfg.stats_type) + 1) % len(STATS_RANGES)
            self.cfg.stats_type = STATS_RANGES[idx]
            self.cfg.save()
            self._load_tab()
        elif self.current_tab == "settings":
            self.settings_sec_idx = (self.settings_sec_idx + 1) % len(SETTINGS_TABS)
            if self._last_settings:
                self._render_settings(self._last_settings)

    def action_cycle_subview(self) -> None:
        if self.current_tab == "dashboard":
            self.dash_sub_idx = (self.dash_sub_idx + 1) % len(DASH_SUBVIEWS)
            if self._last_stats:
                self._render_dashboard(self._last_stats)
        elif self.current_tab == "settings":
            self.settings_sec_idx = (self.settings_sec_idx + 1) % len(SETTINGS_TABS)
            if self._last_settings:
                self._render_settings(self._last_settings)
        elif self.current_tab == "dhcp":
            self.dhcp_sub = "scopes" if self.dhcp_sub == "leases" else "leases"
            self._load_tab()
        elif self.current_tab == "admin":
            order = ["users", "groups", "sessions", "cluster"]
            self.admin_sub = order[(order.index(self.admin_sub) + 1) % len(order)]
            self._load_tab()
        elif self.current_tab == "apps":
            self.apps_sub = "store" if self.apps_sub == "installed" else "installed"
            self._load_tab()
        elif self.current_tab == "logs":
            self.logs_sub = "query" if self.logs_sub != "query" else "files"
            self._load_tab()

    def action_quick_block(self) -> None:
        sel = self._selected_meta()
        if not sel or sel[0] != "domain":
            return
        dom = str(sel[1])
        self._run_bg(f"Blocking {dom}…", lambda: self.api.block_zone(dom), f"Blocked {dom}")

    def action_add(self) -> None:
        if self.current_tab == "dashboard":
            sel = self._selected_meta()
            if sel and sel[0] == "domain":
                dom = str(sel[1])
                self._run_bg(f"Allowing {dom}…", lambda: self.api.allow_zone(dom), f"Allowed {dom}")
        elif self.current_tab == "zones":
            if self.active_zone:
                self.push_screen(
                    AddRecordModal(self.active_zone),
                    lambda res: self._run_bg(
                        "Adding record…",
                        lambda: self.api.add_record(self.active_zone, res[0], res[1], res[2], res[3]),
                        f"Added {res[1]} {res[0]}",
                    )
                    if res
                    else None,
                )
            else:
                self.push_screen(
                    CreateZoneModal(),
                    lambda res: self._run_bg(
                        "Creating zone…",
                        lambda: self.api.create_zone(res[0], res[1], res[2]),
                        f"Created zone {res[0]}",
                    )
                    if res
                    else None,
                )
        elif self.current_tab == "allowed":
            self.push_screen(
                InputModal("Allow Domain", "example.com"),
                lambda d: self._run_bg(f"Allowing {d}…", lambda: self.api.allow_zone(d), f"Allowed {d}") if d else None,
            )
        elif self.current_tab == "blocked":
            self.push_screen(
                InputModal("Block Domain", "ads.example.com"),
                lambda d: self._run_bg(f"Blocking {d}…", lambda: self.api.block_zone(d), f"Blocked {d}") if d else None,
            )
        elif self.current_tab == "apps" and self.apps_sub == "store":
            sel = self._selected_meta()
            if sel and sel[0] == "store_app":
                self._install_app_confirm(sel[1])
        elif self.current_tab == "admin" and self.admin_sub == "users":
            self.push_screen(
                InputModal("Create User (username:password)", "alice:secret123"),
                self._create_user_from_input,
            )

    def _create_user_from_input(self, val: str | None) -> None:
        if not val or ":" not in val:
            return
        u, p = val.split(":", 1)
        self._run_bg(f"Creating user {u}…", lambda: self.api.create_user(u.strip(), p), f"Created user {u.strip()}")

    def action_edit(self) -> None:
        sel = self._selected_meta()
        if not sel:
            return
        kind, obj = sel
        if kind == "setting":
            self._edit_setting(obj[0], obj[1])
        elif kind == "zone":
            name = obj["name"]
            if obj.get("disabled"):
                self._run_bg(f"Enabling {name}…", lambda: self.api.enable_zone(name), f"Enabled {name}")
            else:
                self._run_bg(f"Disabling {name}…", lambda: self.api.disable_zone(name), f"Disabled {name}")
        elif kind == "app":
            self._open_app_config(obj["name"])
        elif kind == "scope":
            name = obj["name"]
            if obj.get("enabled"):
                self._run_bg(f"Disabling scope {name}…", lambda: self.api.disable_dhcp_scope(name), f"Disabled {name}")
            else:
                self._run_bg(f"Enabling scope {name}…", lambda: self.api.enable_dhcp_scope(name), f"Enabled {name}")
        elif kind == "lease":
            scope = obj.get("scope", "")
            hw = obj.get("hardwareAddress", "")
            if obj.get("type") == "Reserved":
                self._run_bg("Converting to dynamic…", lambda: self.api.convert_to_dynamic(scope, hw), "Converted to Dynamic")
            else:
                self._run_bg("Converting to reserved…", lambda: self.api.convert_to_reserved(scope, hw), "Converted to Reserved")

    def _edit_setting(self, key: str, current_val: Any) -> None:
        _, label, desc = get_setting_meta(key)
        title = f"{label} ({key})"
        if isinstance(current_val, bool):
            new_val = not current_val
            self._run_bg(f"Setting {label} -> {'ON' if new_val else 'OFF'}…", lambda: self.api.set_settings({key: new_val}), f"Saved {label} = {'ON' if new_val else 'OFF'}")
            return
        if isinstance(current_val, list):
            initial = "\n".join(str(x) for x in current_val)
            hint = f"{desc} • One item per line • Ctrl+S to Save" if desc else "One item per line • Ctrl+S to Save"
            self.push_screen(
                EditSettingModal(title, initial, hint),
                lambda txt: self._save_list_setting(key, txt),
            )
            return
        self.push_screen(
            InputModal(title, desc or str(current_val or ""), str(current_val if current_val is not None else "")),
            lambda val: self._run_bg(f"Saving {label}…", lambda: self.api.set_settings({key: val}), f"Saved {label}")
            if val is not None
            else None,
        )

    def _save_list_setting(self, key: str, txt: str | None) -> None:
        if txt is None:
            return
        items = [line.strip() for line in txt.splitlines() if line.strip()]
        self._run_bg(f"Saving {key}…", lambda: self.api.set_settings({key: items}), f"Saved {key} ({len(items)} items)")

    @work(thread=True)
    def _open_app_config(self, app_name: str) -> None:
        try:
            data = self.api.get_app_config(app_name)
            cfg_txt = str(data.get("config") or "")
            self.call_from_thread(
                self.push_screen,
                EditSettingModal(f"App Config: {app_name}", cfg_txt, "Edit JSON config • Ctrl+S to Save • Esc to Cancel"),
                lambda txt: self._run_bg(
                    f"Saving {app_name} config…",
                    lambda: self.api.set_app_config(app_name, txt),
                    f"Saved {app_name} config",
                )
                if txt is not None
                else None,
            )
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[#ff6b81]Error: {exc}[/]")

    def _install_app_confirm(self, app_obj: dict[str, Any]) -> None:
        name = app_obj.get("name", "")
        url = app_obj.get("url", "")
        if not name or not url:
            return
        self.push_screen(
            ConfirmModal(f"Download & install DNS App '{name}'?"),
            lambda ok: self._run_bg(f"Installing {name}…", lambda: self.api.install_store_app(name, url), f"Installed {name}")
            if ok
            else None,
        )

    @work(thread=True)
    def _view_log_file(self, file_name: str) -> None:
        self.call_from_thread(self._set_status, f"Loading {file_name}…")
        try:
            txt = self.api.download_log(file_name, limit_mb=1)
            lines = txt.splitlines()[-150:]
            self.logs_sub = "viewer"
            self.call_from_thread(self._configure_widgets_for_tab)
            self.call_from_thread(self.query_one("#view-title", Static).update, f"Logs  ›  {file_name}  (last {len(lines)} lines)")
            self.call_from_thread(self.query_one("#log-viewer", Static).update, "\n".join(lines))
            self.call_from_thread(self._set_status, "Press h or Esc to return to log file list")
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[#ff6b81]Error: {exc}[/]")

    def action_delete(self) -> None:
        sel = self._selected_meta()
        if not sel:
            return
        kind, obj = sel
        if kind == "zone":
            name = obj["name"]
            self.push_screen(
                ConfirmModal(f"Delete zone '{name}'?"),
                lambda ok: self._run_bg(f"Deleting {name}…", lambda: self.api.delete_zone(name), f"Deleted {name}") if ok else None,
            )
        elif kind == "record":
            self.push_screen(
                ConfirmModal(f"Delete {obj['type']} {obj['domain']} -> {obj['value']}?"),
                lambda ok: self._run_bg(
                    "Deleting record…",
                    lambda: self.api.delete_record(obj["zone"], obj["domain"], obj["type"], obj["value"]),
                    "Deleted record",
                )
                if ok
                else None,
            )
        elif kind in ("cache_zone", "cache_rec"):
            self._run_bg(f"Deleting cached {obj}…", lambda: self.api.delete_cached_zone(obj), f"Deleted {obj}")
        elif kind in ("allowed_zone", "allowed_rec"):
            self._run_bg(f"Removing allowed {obj}…", lambda: self.api.delete_allowed(obj), f"Removed {obj}")
        elif kind in ("blocked_zone", "blocked_rec"):
            self._run_bg(f"Removing blocked {obj}…", lambda: self.api.delete_blocked(obj), f"Removed {obj}")
        elif kind == "app":
            name = obj["name"]
            self.push_screen(
                ConfirmModal(f"Uninstall DNS App '{name}'?"),
                lambda ok: self._run_bg(f"Uninstalling {name}…", lambda: self.api.uninstall_app(name), f"Uninstalled {name}")
                if ok
                else None,
            )
        elif kind == "lease":
            self._run_bg(
                "Removing lease…",
                lambda: self.api.remove_dhcp_lease(obj.get("scope", ""), obj.get("hardwareAddress", "")),
                "Removed lease",
            )
        elif kind == "scope":
            name = obj["name"]
            self.push_screen(
                ConfirmModal(f"Delete DHCP scope '{name}'?"),
                lambda ok: self._run_bg(f"Deleting {name}…", lambda: self.api.delete_dhcp_scope(name), f"Deleted {name}")
                if ok
                else None,
            )
        elif kind == "user":
            u = obj["username"]
            self.push_screen(
                ConfirmModal(f"Delete user '{u}'?"),
                lambda ok: self._run_bg(f"Deleting {u}…", lambda: self.api.delete_user(u), f"Deleted {u}") if ok else None,
            )
        elif kind == "session":
            tok = obj["partialToken"]
            self._run_bg("Revoking session…", lambda: self.api.delete_session(tok), "Revoked session")
        elif kind == "logfile":
            self.push_screen(
                ConfirmModal(f"Delete log file '{obj}'?"),
                lambda ok: self._run_bg(f"Deleting {obj}…", lambda: self.api.delete_log(obj), f"Deleted {obj}") if ok else None,
            )

    def action_flush(self) -> None:
        if self.current_tab == "cache":
            self.push_screen(
                ConfirmModal("Flush entire DNS cache?"),
                lambda ok: self._run_bg("Flushing cache…", self.api.flush_cache, "DNS cache flushed") if ok else None,
            )
        elif self.current_tab == "allowed":
            self.push_screen(
                ConfirmModal("Flush ALL allowed zones?"),
                lambda ok: self._run_bg("Flushing allowed…", self.api.flush_allowed, "Allowed zones flushed") if ok else None,
            )
        elif self.current_tab == "blocked":
            self.push_screen(
                ConfirmModal("Flush ALL blocked zones?"),
                lambda ok: self._run_bg("Flushing blocked…", self.api.flush_blocked, "Blocked zones flushed") if ok else None,
            )
        elif self.current_tab == "logs":
            self.push_screen(
                ConfirmModal("Delete ALL server log files?"),
                lambda ok: self._run_bg("Deleting logs…", self.api.delete_all_logs, "All logs deleted") if ok else None,
            )

    def action_temp_disable_blocking(self) -> None:
        self.push_screen(
            InputModal("Temporarily Disable Blocking (minutes)", "10", "10"),
            lambda m: self._run_bg(
                f"Disabling blocking for {m}m…",
                lambda: self.api.temp_disable_blocking(int(m)),
                f"Blocking disabled for {m} minutes",
            )
            if (m and m.isdigit())
            else None,
        )

    def action_force_update_blocklists(self) -> None:
        self._run_bg("Updating block lists…", self.api.force_update_block_lists, "Triggered block list update")

    @work(thread=True)
    def _run_bg(self, pending_msg: str, fn, done_msg: str) -> None:
        self.call_from_thread(self._set_status, pending_msg)
        try:
            fn()
            self.call_from_thread(self._set_status, f"[#51cf66]{done_msg}[/]")
            self.call_from_thread(self._load_tab)
        except Exception as exc:
            self.call_from_thread(self._set_status, f"[#ff6b81]Error: {exc}[/]")

    def action_show_help(self) -> None:
        self.push_screen(HelpModal())

    def action_quit_app(self) -> None:
        self.exit()


def run() -> None:
    TechnitiumApp().run()


if __name__ == "__main__":
    run()
