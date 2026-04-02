from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable

from src.xui_client import XUIClient


XUIClientFactory = Callable[[str, str, str], XUIClient]


def _coerce_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    raise ValueError(f"Unsupported datetime value: {value!r}")


def _node_inbound_id(node: dict[str, Any]) -> int:
    raw = node.get("xui_inbound_id")
    if raw is None:
        raise RuntimeError(f"Node {node.get('id')} has no xui_inbound_id")
    return int(raw)


def _is_duplicate_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "exists" in text or "exist" in text or "duplicate" in text or "already" in text


async def _with_xui_node_client(
    node: dict[str, Any],
    fn: Callable[[XUIClient, int], "asyncio.Future[Any]"] | Callable[[XUIClient, int], Any],
    *,
    xui_client_factory: XUIClientFactory | None = None,
) -> Any:
    factory = xui_client_factory or XUIClient
    xui = factory(
        str(node["xui_base_url"]).rstrip("/"),
        str(node["xui_username"]),
        str(node["xui_password"]),
    )
    inbound_id = _node_inbound_id(node)
    await xui.start()
    try:
        return await fn(xui, inbound_id)
    finally:
        await xui.close()


async def create_client_on_node(
    node: dict[str, Any],
    client_uuid: str,
    client_email: str,
    sub_id: str | None,
    expires_at: datetime,
    limit_ip: int,
    *,
    xui_client_factory: XUIClientFactory | None = None,
) -> dict[str, Any]:
    expires = _coerce_utc(expires_at)

    async def _run(xui: XUIClient, inbound_id: int) -> dict[str, Any]:
        await xui.add_client(
            inbound_id,
            client_uuid,
            client_email,
            expires,
            limit_ip=limit_ip,
            sub_id=sub_id,
        )
        node_sub_id = sub_id or await xui.get_client_sub_id(inbound_id, client_uuid)
        return {"xui_sub_id": node_sub_id}

    return await _with_xui_node_client(node, _run, xui_client_factory=xui_client_factory)


async def update_client_on_node(
    node: dict[str, Any],
    client_uuid: str,
    client_email: str,
    sub_id: str | None,
    expires_at: datetime,
    limit_ip: int,
    *,
    xui_client_factory: XUIClientFactory | None = None,
) -> dict[str, Any]:
    expires = _coerce_utc(expires_at)

    async def _run(xui: XUIClient, inbound_id: int) -> dict[str, Any]:
        await xui.update_client(
            inbound_id,
            client_uuid,
            client_email,
            expires,
            limit_ip=limit_ip,
            sub_id=sub_id,
        )
        node_sub_id = sub_id or await xui.get_client_sub_id(inbound_id, client_uuid)
        return {"xui_sub_id": node_sub_id}

    return await _with_xui_node_client(node, _run, xui_client_factory=xui_client_factory)


async def delete_or_disable_client_on_node(
    node: dict[str, Any],
    client_uuid: str,
    client_email: str,
    sub_id: str | None,
    expires_at: datetime,
    limit_ip: int,
    *,
    xui_client_factory: XUIClientFactory | None = None,
) -> dict[str, Any]:
    expires = _coerce_utc(expires_at)

    async def _run(xui: XUIClient, inbound_id: int) -> dict[str, Any]:
        action = await xui.del_client(
            inbound_id,
            client_uuid,
            email=client_email,
            expiry=expires,
            limit_ip=limit_ip,
            sub_id=sub_id,
        )
        return {"action": action, "xui_sub_id": sub_id}

    return await _with_xui_node_client(node, _run, xui_client_factory=xui_client_factory)


async def ensure_client_on_all_active_nodes(
    db: Any,
    subscription_row: dict[str, Any],
    settings: Any,
    *,
    semaphore_limit: int = 5,
    xui_client_factory: XUIClientFactory | None = None,
) -> dict[str, Any]:
    nodes = await db.get_active_vpn_nodes(lb_only=True)
    if not nodes:
        return {"total": 0, "ok": 0, "failed": 0, "results": []}

    subscription_id = int(subscription_row["id"])
    client_uuid = str(subscription_row["client_uuid"])
    client_email = str(subscription_row["client_email"])
    expires_at = _coerce_utc(subscription_row["expires_at"])
    sub_id = str(subscription_row["xui_sub_id"]) if subscription_row.get("xui_sub_id") else None
    is_active = bool(subscription_row.get("is_active", False))
    revoked_at = subscription_row.get("revoked_at")
    desired_enabled = is_active and expires_at > datetime.now(timezone.utc) and revoked_at is None
    limit_ip = int(getattr(settings, "max_devices_per_sub", 1))

    semaphore = asyncio.Semaphore(max(1, int(semaphore_limit)))

    async def _sync_node(node: dict[str, Any]) -> dict[str, Any]:
        node_id = int(node["id"])
        async with semaphore:
            try:
                if desired_enabled:
                    try:
                        node_result = await create_client_on_node(
                            node,
                            client_uuid,
                            client_email,
                            sub_id,
                            expires_at,
                            limit_ip,
                            xui_client_factory=xui_client_factory,
                        )
                    except Exception as exc:
                        if not _is_duplicate_error(exc):
                            raise
                        node_result = await update_client_on_node(
                            node,
                            client_uuid,
                            client_email,
                            sub_id,
                            expires_at,
                            limit_ip,
                            xui_client_factory=xui_client_factory,
                        )
                    observed_enabled = True
                    observed_expires_at = expires_at
                    sync_state = "ok"
                    last_error = None
                else:
                    node_result = await delete_or_disable_client_on_node(
                        node,
                        client_uuid,
                        client_email,
                        sub_id,
                        expires_at,
                        limit_ip,
                        xui_client_factory=xui_client_factory,
                    )
                    observed_enabled = False
                    observed_expires_at = expires_at
                    sync_state = "ok"
                    last_error = None

                await db.upsert_vpn_node_client_state(
                    node_id=node_id,
                    subscription_id=subscription_id,
                    client_uuid=client_uuid,
                    client_email=client_email,
                    desired_enabled=desired_enabled,
                    desired_expires_at=expires_at,
                    observed_enabled=observed_enabled,
                    observed_expires_at=observed_expires_at,
                    sync_state=sync_state,
                    last_error=last_error,
                    xui_sub_id=node_result.get("xui_sub_id"),
                )
                return {"node_id": node_id, "ok": True}
            except Exception as exc:
                await db.upsert_vpn_node_client_state(
                    node_id=node_id,
                    subscription_id=subscription_id,
                    client_uuid=client_uuid,
                    client_email=client_email,
                    desired_enabled=desired_enabled,
                    desired_expires_at=expires_at,
                    observed_enabled=None,
                    observed_expires_at=None,
                    sync_state="error",
                    last_error=str(exc),
                    xui_sub_id=sub_id,
                )
                return {"node_id": node_id, "ok": False, "error": str(exc)}

    results = await asyncio.gather(*[_sync_node(node) for node in nodes])
    ok_count = sum(1 for item in results if item["ok"])
    return {
        "total": len(results),
        "ok": ok_count,
        "failed": len(results) - ok_count,
        "results": results,
    }
