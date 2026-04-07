from urllib.parse import quote, urlencode, urlsplit, urlunsplit


def build_vless_url(
    *,
    uuid: str,
    host: str,
    port: int,
    tag: str,
    public_key: str,
    short_id: str,
    sni: str,
    fingerprint: str = "chrome",
    flow: str = "",
) -> str:
    params = {
        "encryption": "none",
        "type": "tcp",
        "security": "reality",
        "pbk": public_key,
        "fp": fingerprint,
        "sni": sni,
        "sid": short_id,
        "spx": "/",
    }
    if flow:
        params["flow"] = flow
    query = urlencode(params, safe="")
    return f"vless://{uuid}@{host}:{port}?{query}#{quote(tag)}"


def normalize_vless_public_endpoint(
    vless_url: str,
    *,
    host: str,
    port: int,
    tag: str | None = None,
) -> str:
    raw = str(vless_url or "").strip()
    if not raw.lower().startswith("vless://"):
        return raw

    try:
        parts = urlsplit(raw)
    except Exception:
        return raw

    username = parts.username or ""
    if not username:
        return raw

    fragment = parts.fragment
    if tag:
        fragment = quote(tag)

    netloc = f"{username}@{host}:{int(port)}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, fragment))
