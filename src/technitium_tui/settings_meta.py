"""Human-readable labels, sections, and descriptions for Technitium DNS Server settings."""

from __future__ import annotations

import re

# (section_key, section_label)
SETTINGS_TABS: list[tuple[str, str]] = [
    ("general", "General"),
    ("blocking", "Blocking"),
    ("forwarders", "Forwarders"),
    ("cache", "Cache"),
    ("recursion", "Recursion"),
    ("protocols", "Protocols"),
    ("web", "Web Service"),
    ("logging", "Logging"),
    ("all", "All"),
]

# key -> (section, Human Label, Short Description)
SETTINGS_INFO: dict[str, tuple[str, str, str]] = {
    # General
    "dnsServerDomain": ("general", "DNS Server Domain", "Primary FQDN used to identify this DNS server"),
    "dnsServerLocalEndPoints": ("general", "Local End Points", "IP:port interfaces the DNS server listens on"),
    "dnsServerIPv4SourceAddresses": ("general", "IPv4 Source Addresses", "Outbound IPv4 source addresses for upstream requests"),
    "dnsServerIPv6SourceAddresses": ("general", "IPv6 Source Addresses", "Outbound IPv6 source addresses for upstream requests"),
    "defaultRecordTtl": ("general", "Default Record TTL", "Default TTL (seconds) for new DNS records"),
    "defaultResponsiblePerson": ("general", "Default SOA Email", "Default responsible person email for SOA records"),
    "useSoaSerialDateScheme": ("general", "SOA Date Serial Scheme", "Use YYYYMMDDnn format for SOA serial numbers"),
    "minSoaRefresh": ("general", "Min SOA Refresh", "Minimum SOA refresh interval (seconds)"),
    "minSoaRetry": ("general", "Min SOA Retry", "Minimum SOA retry interval (seconds)"),
    "preferIPv6": ("general", "Prefer IPv6", "Prefer IPv6 when querying upstream name servers"),
    "udpPayloadSize": ("general", "EDNS UDP Payload Size", "Maximum UDP packet size in bytes (default 1232)"),
    "dnssecValidation": ("general", "DNSSEC Validation", "Validate cryptographic DNSSEC signatures on responses"),
    "eDnsClientSubnet": ("general", "EDNS Client Subnet", "Send truncated client subnet to upstream for CDN routing"),
    "eDnsClientSubnetIPv4PrefixLength": ("general", "ECS IPv4 Prefix Length", "IPv4 prefix length sent in EDNS Client Subnet (e.g. 24)"),
    "eDnsClientSubnetIPv6PrefixLength": ("general", "ECS IPv6 Prefix Length", "IPv6 prefix length sent in EDNS Client Subnet (e.g. 56)"),
    "eDnsClientSubnetIpv4Override": ("general", "ECS IPv4 Override", "Override public IPv4 network sent for ECS"),
    "eDnsClientSubnetIpv6Override": ("general", "ECS IPv6 Override", "Override public IPv6 network sent for ECS"),
    "qpmLimitRequests": ("general", "QPM Rate Limit", "Max queries per minute per client subnet (0 = unlimited)"),
    "qpmLimitErrors": ("general", "QPM Error Limit", "Max error queries per minute per client (0 = unlimited)"),
    "qpmLimitSampleMinutes": ("general", "QPM Sample Window", "Sampling window in minutes for rate limiting"),
    "qpmLimitIPv4PrefixLength": ("general", "QPM IPv4 Prefix", "IPv4 subnet prefix grouped for rate limiting"),
    "qpmLimitIPv6PrefixLength": ("general", "QPM IPv6 Prefix", "IPv6 subnet prefix grouped for rate limiting"),
    "qpmLimitBypassList": ("general", "QPM Bypass List", "IPs/subnets exempt from query rate limiting"),
    "clientTimeout": ("general", "Client Timeout (ms)", "Timeout for incoming client requests in milliseconds"),
    "tcpSendTimeout": ("general", "TCP Send Timeout (ms)", "Timeout for sending TCP responses in milliseconds"),
    "tcpReceiveTimeout": ("general", "TCP Receive Timeout (ms)", "Timeout for receiving TCP requests in milliseconds"),
    "quicIdleTimeout": ("general", "QUIC Idle Timeout (ms)", "Idle timeout for DNS-over-QUIC connections"),
    "quicMaxInboundStreams": ("general", "QUIC Max Streams", "Max concurrent inbound streams per QUIC connection"),
    "listenBacklog": ("general", "TCP Listen Backlog", "Max pending TCP connections in listen queue"),
    "maxConcurrentResolutionsPerCore": ("general", "Max Resolutions / Core", "Max simultaneous DNS resolutions per CPU core"),
    "dnsAppsEnableAutomaticUpdate": ("general", "Auto-Update DNS Apps", "Automatically update installed DNS Apps"),
    "dnsServerEnableCheckForUpdate": ("general", "Check For Updates", "Periodically check for new Technitium DNS releases"),

    # Blocking
    "enableBlocking": ("blocking", "Enable Blocking", "Master switch for ad/tracker domain blocking"),
    "allowTxtBlockingReport": ("blocking", "TXT Blocking Report", "Include blocking reason in TXT record for blocked queries"),
    "blockingBypassList": ("blocking", "Blocking Bypass List", "Client IPs/subnets that bypass all block lists"),
    "blockingType": ("blocking", "Blocking Response Type", "Reply type for blocked domains (AnyAddress, NxDomain, CustomAddress)"),
    "blockingAnswerTtl": ("blocking", "Blocked Answer TTL", "TTL (seconds) returned for blocked domain answers"),
    "customBlockingAddresses": ("blocking", "Custom Blocking IPs", "Custom IP(s) returned when Blocking Type is CustomAddress"),
    "blockListUrls": ("blocking", "Block List URLs", "URLs of block/allow lists downloaded & enforced"),
    "blockListUpdateIntervalHours": ("blocking", "Block List Update (hrs)", "How often to auto-refresh block lists (hours)"),

    # Forwarders & Proxy
    "forwarders": ("forwarders", "Forwarders", "Upstream DNS servers to forward unresolved queries to"),
    "forwarderProtocol": ("forwarders", "Forwarder Protocol", "Transport protocol for forwarders (Udp, Tcp, Tls, Https, Quic)"),
    "concurrentForwarding": ("forwarders", "Concurrent Forwarding", "Query multiple forwarders simultaneously for fastest reply"),
    "forwarderRetries": ("forwarders", "Forwarder Retries", "Retry count when a forwarder times out"),
    "forwarderTimeout": ("forwarders", "Forwarder Timeout (ms)", "Timeout per forwarder request in milliseconds"),
    "forwarderConcurrency": ("forwarders", "Forwarder Concurrency", "Max concurrent forwarders queried per request"),
    "proxy": ("forwarders", "Proxy Settings", "HTTP/SOCKS5 proxy used for outbound DNS & blocklist fetches"),

    # Cache
    "saveCache": ("cache", "Save Cache to Disk", "Persist DNS cache across server restarts"),
    "serveStale": ("cache", "Serve Stale Records", "Serve expired cache entries if upstream is unreachable"),
    "serveStaleTtl": ("cache", "Serve Stale TTL", "Max age (seconds) to serve stale cached records"),
    "serveStaleAnswerTtl": ("cache", "Stale Answer TTL", "TTL (seconds) given to clients for stale answers"),
    "serveStaleResetTtl": ("cache", "Stale Reset TTL", "Delay before retrying upstream for a stale record"),
    "serveStaleMaxWaitTime": ("cache", "Stale Max Wait (ms)", "Max time to wait for upstream before serving stale"),
    "cacheMaximumEntries": ("cache", "Max Cache Entries", "Maximum number of cached domains kept in memory"),
    "cacheMinimumRecordTtl": ("cache", "Min Record TTL", "Minimum TTL (seconds) enforced on cached records"),
    "cacheMaximumRecordTtl": ("cache", "Max Record TTL", "Maximum TTL (seconds) enforced on cached records"),
    "cacheNegativeRecordTtl": ("cache", "Negative Cache TTL", "Max TTL (seconds) for NXDOMAIN / negative responses"),
    "cacheFailureRecordTtl": ("cache", "Failure Cache TTL", "TTL (seconds) for SERVFAIL / failed lookups"),
    "cachePrefetchEligibility": ("cache", "Prefetch Eligibility", "Min original TTL (sec) for a record to qualify for auto-prefetch"),
    "cachePrefetchTrigger": ("cache", "Prefetch Trigger", "Remaining TTL (sec) at which popular records auto-refresh"),
    "cachePrefetchSampleIntervalInMinutes": ("cache", "Prefetch Sample (min)", "Interval (minutes) to sample top queried domains"),
    "cachePrefetchSampleEligibilityHitsPerHour": ("cache", "Prefetch Min Hits/hr", "Minimum hits/hour for a domain to be auto-prefetched"),

    # Recursion
    "recursion": ("recursion", "Recursion Policy", "Who can resolve external domains (Deny, Allow, AllowOnlyForPrivateNetworks)"),
    "recursionNetworkACL": ("recursion", "Recursion Network ACL", "Allowed/denied subnets when using custom recursion ACL"),
    "randomizeName": ("recursion", "0x20 Case Randomization", "Randomize query letter casing to harden against spoofing"),
    "qnameMinimization": ("recursion", "QNAME Minimization", "Send minimal domain labels to root/TLD servers for privacy"),
    "nsRevalidation": ("recursion", "NS Revalidation", "Revalidate authoritative NS records on expiry"),
    "resolverRetries": ("recursion", "Resolver Retries", "Retry count for recursive upstream queries"),
    "resolverTimeout": ("recursion", "Resolver Timeout (ms)", "Timeout for recursive upstream queries"),
    "resolverConcurrency": ("recursion", "Resolver Concurrency", "Parallel name servers queried during recursion"),
    "resolverMaxStackCount": ("recursion", "Max Recursion Depth", "Maximum recursive resolution stack depth"),

    # Optional Protocols
    "enableDnsOverUdpProxy": ("protocols", "DNS-over-UDP Proxy", "Enable HAProxy PROXY protocol for UDP DNS"),
    "enableDnsOverTcpProxy": ("protocols", "DNS-over-TCP Proxy", "Enable HAProxy PROXY protocol for TCP DNS"),
    "enableDnsOverHttp": ("protocols", "DNS-over-HTTP (DoH)", "Enable plain HTTP DoH (for behind a reverse proxy)"),
    "enableDnsOverTls": ("protocols", "DNS-over-TLS (DoT)", "Enable encrypted DNS-over-TLS (port 853)"),
    "enableDnsOverHttps": ("protocols", "DNS-over-HTTPS (DoH)", "Enable encrypted DNS-over-HTTPS (port 443)"),
    "enableDnsOverHttp3": ("protocols", "DNS-over-HTTP/3", "Enable HTTP/3 for DNS-over-HTTPS"),
    "enableDnsOverQuic": ("protocols", "DNS-over-QUIC (DoQ)", "Enable encrypted DNS-over-QUIC (port 853)"),
    "dnsOverUdpProxyPort": ("protocols", "UDP Proxy Port", "Port for DNS-over-UDP Proxy"),
    "dnsOverTcpProxyPort": ("protocols", "TCP Proxy Port", "Port for DNS-over-TCP Proxy"),
    "dnsOverHttpPort": ("protocols", "DoH HTTP Port", "Port for plain HTTP DoH (default 80)"),
    "dnsOverTlsPort": ("protocols", "DoT Port", "Port for DNS-over-TLS (default 853)"),
    "dnsOverHttpsPort": ("protocols", "DoH HTTPS Port", "Port for DNS-over-HTTPS (default 443)"),
    "dnsOverQuicPort": ("protocols", "DoQ Port", "Port for DNS-over-QUIC (default 853)"),
    "dnsOverHttpRealIpHeader": ("protocols", "DoH Real-IP Header", "HTTP header carrying client IP behind reverse proxy"),
    "dnsTlsCertificatePath": ("protocols", "TLS Certificate Path", "Path to PKCS#12 (.pfx) TLS certificate for DoT/DoH/DoQ"),
    "dnsTlsCertificatePassword": ("protocols", "TLS Cert Password", "Password for the TLS certificate file"),
    "reverseProxyNetworkACL": ("protocols", "Reverse Proxy ACL", "Trusted reverse proxy IPs/subnets"),

    # Web Service
    "webServiceLocalAddresses": ("web", "Web UI Listen IPs", "IP addresses the Web UI listens on"),
    "webServiceHttpPort": ("web", "Web UI HTTP Port", "HTTP port for Technitium Web UI & API (default 5380)"),
    "webServiceEnableTls": ("web", "Web UI Enable HTTPS", "Enable HTTPS for the Web UI"),
    "webServiceEnableHttp3": ("web", "Web UI Enable HTTP/3", "Enable HTTP/3 on the HTTPS Web UI"),
    "webServiceHttpToTlsRedirect": ("web", "Redirect HTTP → HTTPS", "Automatically redirect Web UI HTTP to HTTPS"),
    "webServiceUseSelfSignedTlsCertificate": ("web", "Self-Signed TLS Cert", "Auto-generate a self-signed cert for Web UI HTTPS"),
    "webServiceTlsPort": ("web", "Web UI HTTPS Port", "HTTPS port for Web UI (default 53443)"),
    "webServiceTlsCertificatePath": ("web", "Web UI TLS Cert Path", "Path to custom TLS certificate for Web UI"),
    "webServiceTlsCertificatePassword": ("web", "Web UI TLS Password", "Password for custom Web UI TLS certificate"),
    "webServiceRealIpHeader": ("web", "Web UI Real-IP Header", "Header carrying client IP when Web UI is reverse-proxied"),

    # Logging
    "enableLogging": ("logging", "Enable Server Logging", "Write DNS server events to log files"),
    "ignoreResolverLogs": ("logging", "Ignore Resolver Logs", "Reduce log noise by omitting recursive resolver errors"),
    "logQueries": ("logging", "Log All DNS Queries", "Write every DNS query into the server log file"),
    "useLocalTime": ("logging", "Use Local Time", "Use server local timezone instead of UTC in logs"),
    "logFolder": ("logging", "Log Folder Path", "Directory where log files are stored"),
    "maxLogFileDays": ("logging", "Log Retention (days)", "Delete log files older than N days (0 = keep forever)"),
    "enableInMemoryStats": ("logging", "In-Memory Stats Only", "Keep dashboard stats in RAM only (don't write to disk)"),
    "maxStatFileDays": ("logging", "Stats Retention (days)", "Delete dashboard stat files older than N days"),
}

# Read-only informational keys hidden from the editable settings table
HIDDEN_SETTINGS = {
    "version",
    "uptimestamp",
    "blockListNextUpdatedOn",
    "temporaryDisableBlockingTill",
    "clusterInitialized",
    "clusterDomain",
    "tsigKeys",
    "defaultNsRecordTtl",
    "defaultSoaRecordTtl",
}


def humanize_key(key: str) -> str:
    """Convert camelCase API key into clean Title Case as fallback."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", key)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return s[:1].upper() + s[1:]


def get_setting_meta(key: str) -> tuple[str, str, str]:
    """Return (section, human_label, description) for any Technitium setting key."""
    if key in SETTINGS_INFO:
        return SETTINGS_INFO[key]
    kl = key.lower()
    if "block" in kl:
        sec = "blocking"
    elif "forward" in kl or "proxy" in kl:
        sec = "forwarders"
    elif "cache" in kl or "stale" in kl:
        sec = "cache"
    elif "recurs" in kl or "resolver" in kl:
        sec = "recursion"
    elif "webservice" in kl:
        sec = "web"
    elif "log" in kl or "stat" in kl:
        sec = "logging"
    elif "dnsover" in kl or "tls" in kl or "quic" in kl:
        sec = "protocols"
    else:
        sec = "general"
    return (sec, humanize_key(key), "")
