import ipaddress
import re
from urllib.parse import urlparse

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_domain(value: str) -> str:
    """Normalize a company URL to a DNS hostname, rejecting credentials and malformed hosts."""
    raw = value.strip()
    if not raw:
        raise ValueError("A valid company domain is required")
    candidate = raw if "://" in raw else "https://" + raw
    try:
        parsed = urlparse(candidate)
        # Accessing .port validates malformed/out-of-range ports.
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid company domain or port") from exc
    if parsed.scheme.lower() not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("Only HTTP(S) company URLs without embedded credentials are accepted")
    host = (parsed.hostname or "").strip(".").lower()
    if not host:
        raise ValueError("A valid company domain is required")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Invalid internationalized company domain") from exc
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("A company DNS domain is required, not an IP address")
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) < 2 or len(host) > 253 or any(not _LABEL.fullmatch(label) for label in labels):
        raise ValueError("A valid company DNS domain is required")
    return host
