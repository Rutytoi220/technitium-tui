# technitium-tui

A terminal UI for [Technitium DNS Server](https://technitium.com/dns/) (`tnt-tui`).

Lets you manage your Technitium server from the terminal instead of opening the web panel — dashboard stats, zones, DNS records, cache, allowed/blocked domains, apps, DNS client, settings, DHCP, users, and logs.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Rutytoi220/technitium-tui/main/install.sh | bash
```

Or with `uv` / `pipx`:

```bash
uv tool install git+https://github.com/Rutytoi220/technitium-tui
```

## Usage

```bash
tnt-tui
```

Log in with your Technitium server URL and credentials (or API token) on first launch.

### Main keys

- `1`–`9`, `0`, `-` — switch tabs (Dashboard, Zones, Cache, Allowed, Blocked, Apps, DNS Client, Settings, DHCP, Admin, Logs)
- `j` / `k`, `h` / `l`, `Enter` — navigate and open/edit items
- `v` — switch sub-views inside a tab
- `[` / `]` — change dashboard time range
- `a` / `e` / `d` — add / edit or toggle / delete
- `b` — quick-block a domain from the dashboard
- `T` / `U` — temporarily disable blocking / update blocklists
- `X` — flush cache / allowed / blocked
- `/` — filter, `r` — refresh, `?` — help, `q` — quit

## License

MIT
