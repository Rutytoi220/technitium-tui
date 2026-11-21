"""Complete HTTP API client for Technitium DNS Server."""

from __future__ import annotations

from typing import Any

import httpx


class TechnitiumError(Exception):
    """Raised when Technitium returns a non-ok API status."""


class TechnitiumAPI:
    def __init__(self, base_url: str = "", token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.Client(timeout=15.0, follow_redirects=True)

    def configure(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        raw_text: bool = False,
    ) -> Any:
        if not self.base_url:
            raise TechnitiumError("No server URL configured")
        q = dict(params or {})
        if self.token and "token" not in q:
            q["token"] = self.token
        url = f"{self.base_url}{path}"
        if method == "POST":
            resp = self._client.post(url, params=q, data=data)
        else:
            resp = self._client.get(url, params=q)
        resp.raise_for_status()
        if raw_text:
            return resp.text
        body = resp.json()
        status = body.get("status")
        if status == "ok":
            return body.get("response", body)
        if status == "invalid-token":
            raise TechnitiumError("Invalid or expired session token")
        raise TechnitiumError(body.get("errorMessage") or f"API error ({status})")

    # --- Auth ---
    def login(self, server_url: str, username: str, password: str) -> dict[str, Any]:
        """Mint a non-expiring API token via /api/user/createToken (fallback to /api/user/login)."""
        import socket as _socket

        self.configure(server_url, "")
        token_name = f"tnt-tui-{_socket.gethostname()}"

        # 1. Try creating a permanent non-expiring API token so the user never has to re-login
        try:
            resp = self._client.get(
                f"{self.base_url}/api/user/createToken",
                params={"user": username, "pass": password, "tokenName": token_name},
            )
            if resp.status_code == 200:
                body = resp.json()
                if body.get("status") == "ok" and body.get("token"):
                    self.token = str(body["token"])
                    try:
                        info = self.session_info()
                        body["info"] = info.get("info") or {}
                    except Exception:
                        pass
                    return body
        except Exception:
            pass

        # 2. Fallback to standard session login
        url = f"{self.base_url}/api/user/login"
        resp = self._client.get(
            url,
            params={"user": username, "pass": password, "includeInfo": "true"},
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("status") != "ok":
            raise TechnitiumError(body.get("errorMessage") or f"Login failed ({body.get('status')})")
        self.token = str(body.get("token") or "")
        return body

    def session_info(self) -> dict[str, Any]:
        return self._request("/api/user/session/get")

    # --- Dashboard ---
    def get_stats(self, stats_type: str = "LastDay") -> dict[str, Any]:
        return self._request("/api/dashboard/stats/get", {"type": stats_type, "utc": "true"})

    def get_top_stats(self, stats_type: str = "LastDay", top_type: str = "TopClients", limit: int = 25) -> dict[str, Any]:
        return self._request(
            "/api/dashboard/stats/getTop",
            {"type": stats_type, "statsType": top_type, "limit": str(limit)},
        )

    def delete_all_stats(self) -> Any:
        return self._request("/api/dashboard/stats/deleteAll")

    # --- Zones & Records ---
    def list_zones(self, page: int = 1, per_page: int = 200) -> dict[str, Any]:
        return self._request("/api/zones/list", {"pageNumber": str(page), "zonesPerPage": str(per_page)})

    def create_zone(self, zone: str, zone_type: str = "Primary", forwarder: str = "") -> Any:
        params: dict[str, Any] = {"zone": zone, "type": zone_type}
        if forwarder:
            params["forwarder"] = forwarder
        return self._request("/api/zones/create", params)

    def enable_zone(self, zone: str) -> Any:
        return self._request("/api/zones/enable", {"zone": zone})

    def disable_zone(self, zone: str) -> Any:
        return self._request("/api/zones/disable", {"zone": zone})

    def delete_zone(self, zone: str) -> Any:
        return self._request("/api/zones/delete", {"zone": zone})

    def get_records(self, zone: str, domain: str = "", list_zone: bool = True) -> dict[str, Any]:
        return self._request(
            "/api/zones/records/get",
            {"zone": zone, "domain": domain or zone, "listZone": "true" if list_zone else "false"},
        )

    def add_record(self, zone: str, domain: str, rtype: str, value: str, ttl: int = 3600) -> Any:
        params: dict[str, Any] = {
            "zone": zone,
            "domain": domain,
            "type": rtype.upper(),
            "ttl": str(ttl),
        }
        rt = rtype.upper()
        if rt in ("A", "AAAA"):
            params["ipAddress"] = value
        elif rt == "CNAME":
            params["cname"] = value
        elif rt == "PTR":
            params["ptrName"] = value
        elif rt == "NS":
            params["nameServer"] = value
        elif rt == "TXT":
            params["text"] = value
        elif rt == "MX":
            parts = value.split(None, 1)
            if len(parts) == 2 and parts[0].isdigit():
                params["preference"] = parts[0]
                params["exchange"] = parts[1]
            else:
                params["preference"] = "10"
                params["exchange"] = value
        else:
            params["rdata"] = value
        return self._request("/api/zones/records/add", params)

    def delete_record(self, zone: str, domain: str, rtype: str, value: str) -> Any:
        params: dict[str, Any] = {"zone": zone, "domain": domain, "type": rtype.upper()}
        rt = rtype.upper()
        if rt in ("A", "AAAA"):
            params["ipAddress"] = value
        elif rt == "CNAME":
            params["cname"] = value
        elif rt == "PTR":
            params["ptrName"] = value
        elif rt == "NS":
            params["nameServer"] = value
        elif rt == "TXT":
            params["text"] = value
        elif rt == "MX":
            params["exchange"] = value
        else:
            params["rdata"] = value
        return self._request("/api/zones/records/delete", params)

    # --- Cache ---
    def list_cache(self, domain: str = "") -> dict[str, Any]:
        params = {"domain": domain} if domain else {}
        return self._request("/api/cache/list", params)

    def delete_cached_zone(self, domain: str) -> Any:
        return self._request("/api/cache/delete", {"domain": domain})

    def flush_cache(self) -> Any:
        return self._request("/api/cache/flush")

    # --- Allowed ---
    def list_allowed(self, domain: str = "") -> dict[str, Any]:
        params = {"domain": domain} if domain else {}
        return self._request("/api/allowed/list", params)

    def allow_zone(self, domain: str) -> Any:
        return self._request("/api/allowed/add", {"domain": domain})

    def delete_allowed(self, domain: str) -> Any:
        return self._request("/api/allowed/delete", {"domain": domain})

    def flush_allowed(self) -> Any:
        return self._request("/api/allowed/flush")

    # --- Blocked ---
    def list_blocked(self, domain: str = "") -> dict[str, Any]:
        params = {"domain": domain} if domain else {}
        return self._request("/api/blocked/list", params)

    def block_zone(self, domain: str) -> Any:
        return self._request("/api/blocked/add", {"domain": domain})

    def delete_blocked(self, domain: str) -> Any:
        return self._request("/api/blocked/delete", {"domain": domain})

    def flush_blocked(self) -> Any:
        return self._request("/api/blocked/flush")

    # --- Apps ---
    def list_apps(self) -> dict[str, Any]:
        return self._request("/api/apps/list")

    def list_store_apps(self) -> dict[str, Any]:
        return self._request("/api/apps/listStoreApps")

    def get_app_config(self, name: str) -> dict[str, Any]:
        return self._request("/api/apps/config/get", {"name": name})

    def set_app_config(self, name: str, config_text: str) -> Any:
        return self._request("/api/apps/config/set", {"name": name}, method="POST", data={"config": config_text})

    def uninstall_app(self, name: str) -> Any:
        return self._request("/api/apps/uninstall", {"name": name})

    def install_store_app(self, name: str, url: str) -> Any:
        return self._request("/api/apps/downloadAndInstall", {"name": name, "url": url})

    # --- DNS Client ---
    def resolve_query(
        self,
        domain: str,
        qtype: str = "A",
        server: str = "this-server",
        protocol: str = "Udp",
        dnssec: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "/api/dnsClient/resolve",
            {
                "server": server or "this-server",
                "domain": domain,
                "type": qtype.upper(),
                "protocol": protocol,
                "dnssec": "true" if dnssec else "false",
            },
        )

    # --- Settings ---
    def get_settings(self) -> dict[str, Any]:
        return self._request("/api/settings/get")

    def set_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        form: dict[str, str] = {}
        for k, v in updates.items():
            if isinstance(v, bool):
                form[k] = "true" if v else "false"
            elif isinstance(v, list):
                form[k] = ",".join(str(x) for x in v)
            elif v is None:
                form[k] = ""
            else:
                form[k] = str(v)
        return self._request("/api/settings/set", method="POST", data=form)

    def force_update_block_lists(self) -> Any:
        return self._request("/api/settings/forceUpdateBlockLists")

    def temp_disable_blocking(self, minutes: int) -> dict[str, Any]:
        return self._request("/api/settings/temporaryDisableBlocking", {"minutes": str(minutes)})

    # --- DHCP ---
    def list_dhcp_leases(self) -> dict[str, Any]:
        return self._request("/api/dhcp/leases/list")

    def remove_dhcp_lease(self, scope: str, hw_addr: str) -> Any:
        return self._request("/api/dhcp/leases/remove", {"name": scope, "hardwareAddress": hw_addr})

    def convert_to_reserved(self, scope: str, hw_addr: str) -> Any:
        return self._request("/api/dhcp/leases/convertToReserved", {"name": scope, "hardwareAddress": hw_addr})

    def convert_to_dynamic(self, scope: str, hw_addr: str) -> Any:
        return self._request("/api/dhcp/leases/convertToDynamic", {"name": scope, "hardwareAddress": hw_addr})

    def list_dhcp_scopes(self) -> dict[str, Any]:
        return self._request("/api/dhcp/scopes/list")

    def enable_dhcp_scope(self, name: str) -> Any:
        return self._request("/api/dhcp/scopes/enable", {"name": name})

    def disable_dhcp_scope(self, name: str) -> Any:
        return self._request("/api/dhcp/scopes/disable", {"name": name})

    def delete_dhcp_scope(self, name: str) -> Any:
        return self._request("/api/dhcp/scopes/delete", {"name": name})

    # --- Administration ---
    def list_users(self) -> dict[str, Any]:
        return self._request("/api/admin/users/list")

    def create_user(self, username: str, password: str, display_name: str = "") -> Any:
        return self._request(
            "/api/admin/users/create",
            {"user": username, "pass": password, "displayName": display_name or username},
        )

    def delete_user(self, username: str) -> Any:
        return self._request("/api/admin/users/delete", {"user": username})

    def list_groups(self) -> dict[str, Any]:
        return self._request("/api/admin/groups/list")

    def list_sessions(self) -> dict[str, Any]:
        return self._request("/api/admin/sessions/list")

    def delete_session(self, partial_token: str) -> Any:
        return self._request("/api/admin/sessions/delete", {"partialToken": partial_token})

    def get_cluster_state(self) -> dict[str, Any]:
        return self._request("/api/admin/cluster/state")

    # --- Logs ---
    def list_logs(self) -> dict[str, Any]:
        return self._request("/api/logs/list")

    def download_log(self, file_name: str, limit_mb: int = 1) -> str:
        return self._request("/api/logs/download", {"fileName": file_name, "limit": str(limit_mb)}, raw_text=True)

    def delete_log(self, file_name: str) -> Any:
        return self._request("/api/logs/delete", {"fileName": file_name})

    def delete_all_logs(self) -> Any:
        return self._request("/api/logs/deleteAll")

    def query_logs(
        self,
        app_name: str,
        class_path: str,
        qname: str = "",
        client_ip: str = "",
        entries_per_page: int = 80,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "name": app_name,
            "classPath": class_path,
            "entriesPerPage": str(entries_per_page),
            "descendingOrder": "true",
        }
        if qname:
            params["qname"] = qname
        if client_ip:
            params["clientIpAddress"] = client_ip
        return self._request("/api/logs/query", params)
