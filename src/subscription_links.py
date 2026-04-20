from __future__ import annotations

import base64
from urllib.parse import quote

from src.config import Settings
from src.vless import build_vless_url
from src.xui_client import InboundRealityInfo


def subscription_endpoint_for_node(
    *,
    settings: Settings,
    node: dict[str, object] | None,
) -> tuple[str, int]:
    host = str((node or {}).get("backend_host") or settings.vpn_public_host).strip()
    port_raw = (node or {}).get("backend_port")
    try:
        port = int(port_raw) if port_raw not in (None, "") else int(settings.vpn_public_port)
    except (TypeError, ValueError):
        port = int(settings.vpn_public_port)
    return host, port


def build_subscription_vless_url(
    *,
    settings: Settings,
    node: dict[str, object] | None,
    client_uuid: str,
    reality: InboundRealityInfo,
) -> str:
    host, port = subscription_endpoint_for_node(settings=settings, node=node)
    return build_vless_url(
        uuid=client_uuid,
        host=host,
        port=port,
        tag=settings.vpn_tag,
        public_key=reality.public_key,
        short_id=reality.short_id,
        sni=reality.sni,
        fingerprint=reality.fingerprint,
        flow=settings.vpn_flow,
    )


def build_bot_feed_url(*, site_url: str, feed_token: str) -> str:
    base = str(site_url or "").strip().rstrip("/")
    token = quote(str(feed_token).strip(), safe="")
    return f"{base}/account/feed/{token}/"


def encode_subscription_payload(links: list[str]) -> bytes:
    body = "\n".join(str(item).strip() for item in links if str(item).strip())
    return base64.b64encode(body.encode("utf-8"))
