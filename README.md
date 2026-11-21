# technitium-tui (`tnt-tui`)

A full-featured, keyboard-first (`HJKL`) terminal UI for **[Technitium DNS Server](https://technitium.com/dns/)**, bringing every major tab and setting from the Technitium Web UI into a fast, transparent-friendly terminal interface.

## Features

- **Dashboard (`1`)** — Live colored KPI cards (Total Queries, No Error, Server Failure, NX Domain, Refused, Authoritative, Recursive, Cached, Blocked, Dropped, Clients), query sparkline chart, time range switching (`LastHour` → `LastYear`), and Top Clients / Top Domains / Top Blocked Domains with 1-key quick block/allow.
- **Zones (`2`)** — List, create, enable/disable, and delete authoritative & forwarder zones, plus drill into and manage DNS records (`A`, `AAAA`, `CNAME`, `MX`, `TXT`, `NS`, `PTR`).
- **Cache (`3`)** — Browse cached domains & records, delete individual entries, or flush the entire DNS cache.
- **Allowed (`4`) & Blocked (`5`)** — Browse, add, delete, flush, temporarily disable blocking (`T`), and force update block lists (`U`).
- **Apps (`6`)** — View installed DNS Apps, edit JSON app configs, uninstall, or browse and install from the DNS App Store.
- **DNS Client (`7`)** — Run live DNS queries (`Udp`, `Tcp`, `Tls`, `Https`, `Quic`) against `this-server` or any upstream resolver.
- **Settings (`8`)** — View and edit every Technitium setting across all Web UI sections (General, Web Service, Optional Protocols, Recursion, Cache, Blocking, Proxy & Forwarders, Logging) with live toggle/text/list editing.
- **DHCP (`9`)** — Manage DHCP Leases (convert dynamic ↔ reserved, remove) and DHCP Scopes (enable/disable/delete).
- **Administration (`0`)** — View & manage Users, Groups, Active Sessions, and Cluster State.
- **Logs (`-`)** — View server log files, tail logs right inside the TUI, delete logs, and query Query Logs (when a Query Logs app is installed).

## Installation

### One-line install (Linux / macOS)
```bash
curl -fsSL https://raw.githubusercontent.com/Rutytoi220/technitium-tui/main/install.sh | bash
```

### Using `uv` or `pipx` directly from GitHub
```bash
uv tool install git+https://github.com/Rutytoi220/technitium-tui
# or
pipx install git+https://github.com/Rutytoi220/technitium-tui
```

### Pre-built wheel / tarball
Download from **[GitHub Releases](https://github.com/Rutytoi220/technitium-tui/releases)**.

Run:
```bash
tnt-tui
```

## Keybindings

| Key | Action |
| --- | --- |
| `1`–`9`, `0`, `-` | Switch tabs (Dashboard, Zones, Cache, Allowed, Blocked, Apps, DNS Client, Settings, DHCP, Admin, Logs) |
| `j` / `k`, `g` / `G` | Move cursor down/up, jump to top/bottom |
| `h` / `l`, `Enter` | Back / focus sidebar · Open / Edit item |
| `Tab` | Toggle focus between Sidebar and Main Pane |
| `[` / `]` | Change Dashboard time range (`LastHour`, `LastDay`, `LastWeek`, `LastMonth`, `LastYear`) |
| `v` | Cycle sub-view (Dashboard tables, Settings sections, DHCP Leases/Scopes, Admin Users/Groups/Sessions, Logs) |
| `a` / `e` / `d` | Add · Enable/Disable or Edit · Delete |
| `b` | Quick-block highlighted domain (on Dashboard) |
| `X` | Flush Cache / Allowed / Blocked |
| `T` / `U` | Temporarily disable blocking · Force update block lists |
| `/` | Filter current table |
| `r` | Refresh |
| `L` / `?` / `q` | Login · Help · Quit |

## License

MIT
