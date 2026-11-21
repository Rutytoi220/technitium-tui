"""Keyboard-first modal dialogs for technitium-tui."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea

MODAL_BASE_CSS = """
    align: center middle;
    background: rgba(8, 9, 14, 0.78);
"""


class LoginModal(ModalScreen[tuple[str, str, str, str] | None]):
    """Login with username/password OR paste an API token directly."""

    CSS = f"""
    LoginModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 60;
        height: auto;
        padding: 1 2;
        background: #161822;
        border: round #4c8bf5;
    }}
    #title {{ text-style: bold; color: #eef0f7; margin-bottom: 1; }}
    .lbl {{ color: #858ba3; margin-top: 1; }}
    #err {{ color: #ff6b81; margin-top: 1; height: auto; }}
    #btns {{ margin-top: 1; height: 3; align-horizontal: right; }}
    #btns Button {{ margin-left: 1; }}
    """

    def __init__(self, server_url: str = "", username: str = "admin", error_msg: str = "") -> None:
        super().__init__()
        self._url = server_url or "http://100.100.33.5:5380"
        self._user = username or "admin"
        self._err = error_msg

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static("Connect to Technitium DNS Server", id="title")
            yield Label("Server URL", classes="lbl")
            yield Input(value=self._url, placeholder="http://100.100.33.5:5380", id="in-url")
            yield Label("Username", classes="lbl")
            yield Input(value=self._user, placeholder="admin", id="in-user")
            yield Label("Password (or leave empty if using API Token below)", classes="lbl")
            yield Input(password=True, placeholder="••••••••", id="in-pass")
            yield Label("API Token (optional — overrides password)", classes="lbl")
            yield Input(password=True, placeholder="optional API token", id="in-token")
            yield Static(self._err, id="err")
            with Horizontal(id="btns"):
                yield Button("Cancel", id="cancel")
                yield Button("Connect", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#in-pass", Input).focus()

    def _submit(self) -> None:
        url = self.query_one("#in-url", Input).value.strip().rstrip("/")
        user = self.query_one("#in-user", Input).value.strip()
        pw = self.query_one("#in-pass", Input).value
        tok = self.query_one("#in-token", Input).value.strip()
        if not url:
            self.query_one("#err", Static).update("Server URL is required.")
            return
        if not url.startswith(("http://", "https://")):
            url = "http://" + url
        self.dismiss((url, user, pw, tok))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        order = ["in-url", "in-user", "in-pass", "in-token"]
        if event.input.id in order:
            idx = order.index(event.input.id)
            if event.input.id == "in-pass" and event.value:
                self._submit()
            elif idx + 1 < len(order):
                self.query_one(f"#{order[idx + 1]}", Input).focus()
            else:
                self._submit()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)


class InputModal(ModalScreen[str | None]):
    """Single-field prompt modal."""

    CSS = f"""
    InputModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 58;
        height: auto;
        padding: 1 2;
        background: #161822;
        border: round #4c8bf5;
    }}
    #title {{ text-style: bold; color: #eef0f7; margin-bottom: 1; }}
    #btns {{ margin-top: 1; height: 3; align-horizontal: right; }}
    #btns Button {{ margin-left: 1; }}
    """

    def __init__(self, title: str, placeholder: str = "", initial: str = "") -> None:
        super().__init__()
        self._title = title
        self._placeholder = placeholder
        self._initial = initial

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(self._title, id="title")
            yield Input(value=self._initial, placeholder=self._placeholder, id="val")
            with Horizontal(id="btns"):
                yield Button("Cancel", id="cancel")
                yield Button("Apply", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#val", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one("#val", Input).value.strip())
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)


class EditSettingModal(ModalScreen[str | None]):
    """Multi-line editor for Technitium settings (lists, URLs, JSON app configs, etc.)."""

    CSS = f"""
    EditSettingModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 74;
        height: auto;
        max-height: 28;
        padding: 1 2;
        background: #161822;
        border: round #8c52ff;
    }}
    #title {{ text-style: bold; color: #eef0f7; margin-bottom: 1; }}
    #hint {{ color: #858ba3; margin-bottom: 1; }}
    #editor {{ height: 12; border: solid #2a2d3d; }}
    #btns {{ margin-top: 1; height: 3; align-horizontal: right; }}
    #btns Button {{ margin-left: 1; }}
    """

    def __init__(self, title: str, value: str, hint: str = "Edit value and press Save (Ctrl+S) or Esc to cancel") -> None:
        super().__init__()
        self._title = title
        self._value = value
        self._hint = hint

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(self._title, id="title")
            yield Static(self._hint, id="hint")
            yield TextArea(self._value, id="editor")
            with Horizontal(id="btns"):
                yield Button("Cancel", id="cancel")
                yield Button("Save", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#editor", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(self.query_one("#editor", TextArea).text)
        else:
            self.dismiss(None)

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "ctrl+s":
            event.stop()
            self.dismiss(self.query_one("#editor", TextArea).text)


class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation modal."""

    CSS = f"""
    ConfirmModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 54;
        height: auto;
        padding: 1 2;
        background: #161822;
        border: round #ff6b81;
    }}
    #msg {{ color: #eef0f7; margin-bottom: 1; }}
    #btns {{ height: 3; align-horizontal: right; }}
    #btns Button {{ margin-left: 1; }}
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._msg = message

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(self._msg, id="msg")
            with Horizontal(id="btns"):
                yield Button("Cancel (n)", id="no")
                yield Button("Confirm (y)", variant="error", id="yes")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def on_key(self, event: events.Key) -> None:
        if event.key in ("y", "Y", "enter"):
            event.stop()
            self.dismiss(True)
        elif event.key in ("n", "N", "escape", "q"):
            event.stop()
            self.dismiss(False)


class CreateZoneModal(ModalScreen[tuple[str, str, str] | None]):
    """Create a new Authoritative or Forwarder Zone."""

    CSS = f"""
    CreateZoneModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 58;
        height: auto;
        padding: 1 2;
        background: #161822;
        border: round #4c8bf5;
    }}
    #title {{ text-style: bold; color: #eef0f7; margin-bottom: 1; }}
    .lbl {{ color: #858ba3; margin-top: 1; }}
    #btns {{ margin-top: 1; height: 3; align-horizontal: right; }}
    #btns Button {{ margin-left: 1; }}
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static("Create DNS Zone", id="title")
            yield Label("Zone Name (e.g. home.arpa)", classes="lbl")
            yield Input(placeholder="home.arpa", id="z-name")
            yield Label("Zone Type (Primary, Forwarder, Secondary, Stub)", classes="lbl")
            yield Input(value="Primary", id="z-type")
            yield Label("Forwarder (only for Forwarder zones, e.g. 1.1.1.1)", classes="lbl")
            yield Input(placeholder="optional", id="z-fwd")
            with Horizontal(id="btns"):
                yield Button("Cancel", id="cancel")
                yield Button("Create", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#z-name", Input).focus()

    def _submit(self) -> None:
        name = self.query_one("#z-name", Input).value.strip()
        ztype = self.query_one("#z-type", Input).value.strip() or "Primary"
        fwd = self.query_one("#z-fwd", Input).value.strip()
        if name:
            self.dismiss((name, ztype, fwd))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)


class AddRecordModal(ModalScreen[tuple[str, str, str, int] | None]):
    """Add a DNS record to the currently open zone."""

    CSS = f"""
    AddRecordModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 60;
        height: auto;
        padding: 1 2;
        background: #161822;
        border: round #4c8bf5;
    }}
    #title {{ text-style: bold; color: #eef0f7; margin-bottom: 1; }}
    .lbl {{ color: #858ba3; margin-top: 1; }}
    #btns {{ margin-top: 1; height: 3; align-horizontal: right; }}
    #btns Button {{ margin-left: 1; }}
    """

    def __init__(self, zone: str) -> None:
        super().__init__()
        self._zone = zone

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(f"Add DNS Record to {self._zone}", id="title")
            yield Label("Domain (FQDN or subdomain)", classes="lbl")
            yield Input(value=self._zone, id="r-dom")
            yield Label("Type (A, AAAA, CNAME, TXT, MX, NS, PTR)", classes="lbl")
            yield Input(value="A", id="r-type")
            yield Label("Value (IP / Target / Text)", classes="lbl")
            yield Input(placeholder="192.168.2.5", id="r-val")
            yield Label("TTL (seconds)", classes="lbl")
            yield Input(value="3600", id="r-ttl")
            with Horizontal(id="btns"):
                yield Button("Cancel", id="cancel")
                yield Button("Add", variant="primary", id="ok")

    def on_mount(self) -> None:
        self.query_one("#r-dom", Input).focus()

    def _submit(self) -> None:
        dom = self.query_one("#r-dom", Input).value.strip()
        rtype = self.query_one("#r-type", Input).value.strip().upper() or "A"
        val = self.query_one("#r-val", Input).value.strip()
        try:
            ttl = int(self.query_one("#r-ttl", Input).value.strip() or "3600")
        except ValueError:
            ttl = 3600
        if dom and val:
            self.dismiss((dom, rtype, val, ttl))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self._submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss(None)


class HelpModal(ModalScreen[None]):
    CSS = f"""
    HelpModal {{ {MODAL_BASE_CSS} }}
    #box {{
        width: 70;
        height: auto;
        padding: 1 2;
        background: #161822;
        border: round #4c8bf5;
    }}
    """

    BODY = (
        "[b #4c8bf5]Technitium DNS TUI (tnt-tui) — Keybindings[/]\n\n"
        "[b]Tabs[/]\n"
        "  1 Dashboard   2 Zones       3 Cache      4 Allowed   5 Blocked\n"
        "  6 Apps        7 DNS Client  8 Settings   9 DHCP      0 Admin   - Logs\n"
        "  Tab / h       Jump to sidebar / Back\n\n"
        "[b]Navigation (HJKL)[/]\n"
        "  j / k         Move down / up      g / G   Top / Bottom\n"
        "  l / Enter     Open / Edit item    h       Go back / Focus sidebar\n"
        "  r             Refresh current view\n\n"
        "[b]Actions (Context-Aware)[/]\n"
        "  [ / ]         Dashboard time range (Hour/Day/Week/Month/Year)\n"
        "  v             Cycle sub-view (Dashboard tables / Settings sections / DHCP / Admin / Logs)\n"
        "  a             Add (Zone / Record / Allow / Block / User)\n"
        "  e             Enable/Disable (Zone / DHCP Scope) or Edit (Setting / App Config)\n"
        "  d             Delete selected item\n"
        "  b             Quick-block highlighted domain (from Dashboard)\n"
        "  X             Flush Cache / Allowed / Blocked\n"
        "  T             Temporarily disable blocking (minutes)\n"
        "  U             Force update block lists\n"
        "  /             Filter current table\n"
        "  L             Server Login / Token settings\n"
        "  q             Quit\n\n"
        "[dim]Press Esc, q, or ? to close[/]"
    )

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Static(self.BODY)

    def on_key(self, event: events.Key) -> None:
        if event.key in ("escape", "q", "question_mark", "?"):
            event.stop()
            self.dismiss(None)
