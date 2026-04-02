from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.cluster.provisioner import create_client_on_node, delete_or_disable_client_on_node, update_client_on_node
from src.db import DB
from src.xui_client import XUIClient


LOGGER = logging.getLogger(__name__)


def _is_duplicate_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "exists" in text or "exist" in text or "duplicate" in text or "already" in text


def _to_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    raise ValueError(f"Unsupported datetime value for sync: {value!r}")


def _node_client(node: dict[str, Any]) -> XUIClient:
    return XUIClient(
        str(node["xui_base_url"]).rstrip("/"),
        str(node["xui_username"]),
        str(node["xui_password"]),
    )


def _node_inbound_id(node: dict[str, Any], fallback: int = 1) -> int:
    raw = node.get("xui_inbound_id")
    if raw is None:
        return int(fallback)
    return int(raw)


async def healthcheck_tick(db: DB) -> dict[str, int]:
    nodes = await db.get_active_vpn_nodes(lb_only=False)
    if not nodes:
        return {"checked": 0, "ok": 0, "failed": 0}

    checked = 0
    ok_count = 0
    failed_count = 0

    for node in nodes:
        checked += 1
        node_id = int(node["id"])
        inbound_id = _node_inbound_id(node)
        xui = _node_client(node)
        try:
            await xui.start()
            inbound = await xui.get_inbound(inbound_id)
            reality = xui.parse_reality(inbound)
            await db.mark_node_health(
                node_id=node_id,
                ok=True,
                error=None,
                reality_public_key=reality.public_key,
                reality_short_id=reality.short_id,
                reality_sni=reality.sni,
                reality_fingerprint=reality.fingerprint,
            )
            ok_count += 1
        except Exception as exc:
            failed_count += 1
            await db.mark_node_health(node_id=node_id, ok=False, error=str(exc))
            LOGGER.exception("Cluster healthcheck failed for node_id=%s", node_id)
        finally:
            await xui.close()

    return {"checked": checked, "ok": ok_count, "failed": failed_count}


async def sync_tick(db: DB, settings: Any) -> dict[str, int]:
    nodes = await db.get_active_vpn_nodes(lb_only=True)
    if not nodes:
        return {"nodes": 0, "processed": 0, "ok": 0, "failed": 0}

    batch_size = max(1, int(getattr(settings, "vpn_cluster_sync_batch_size", 200)))
    limit_ip = int(getattr(settings, "max_devices_per_sub", 1))

    processed = 0
    ok_count = 0
    failed_count = 0

    for node in nodes:
        node_id = int(node["id"])
        rows = await db.list_subscriptions_needing_sync(node_id, limit=batch_size)
        node_had_failures = False
        for row in rows:
            processed += 1
            subscription_id = int(row["subscription_id"])
            client_uuid = str(row["client_uuid"])
            client_email = str(row["client_email"])
            desired_enabled = bool(row.get("desired_enabled"))
            desired_expires_at = _to_utc(row.get("desired_expires_at") or row.get("expires_at"))
            sub_id_raw = row.get("xui_sub_id")
            sub_id = str(sub_id_raw).strip() if sub_id_raw else None

            try:
                if desired_enabled:
                    try:
                        node_result = await create_client_on_node(
                            node,
                            client_uuid,
                            client_email,
                            sub_id,
                            desired_expires_at,
                            limit_ip=limit_ip,
                        )
                    except Exception as exc:
                        if not _is_duplicate_error(exc):
                            raise
                        node_result = await update_client_on_node(
                            node,
                            client_uuid,
                            client_email,
                            sub_id,
                            desired_expires_at,
                            limit_ip=limit_ip,
                        )
                    observed_enabled = True
                    observed_expires_at = desired_expires_at
                else:
                    node_result = await delete_or_disable_client_on_node(
                        node,
                        client_uuid,
                        client_email,
                        sub_id,
                        desired_expires_at,
                        limit_ip=limit_ip,
                    )
                    observed_enabled = False
                    observed_expires_at = desired_expires_at

                await db.upsert_vpn_node_client_state(
                    node_id=node_id,
                    subscription_id=subscription_id,
                    client_uuid=client_uuid,
                    client_email=client_email,
                    desired_enabled=desired_enabled,
                    desired_expires_at=desired_expires_at,
                    observed_enabled=observed_enabled,
                    observed_expires_at=observed_expires_at,
                    sync_state="ok",
                    last_error=None,
                    xui_sub_id=node_result.get("xui_sub_id") or sub_id,
                )
                ok_count += 1
            except Exception as exc:
                failed_count += 1
                node_had_failures = True
                await db.upsert_vpn_node_client_state(
                    node_id=node_id,
                    subscription_id=subscription_id,
                    client_uuid=client_uuid,
                    client_email=client_email,
                    desired_enabled=desired_enabled,
                    desired_expires_at=desired_expires_at,
                    observed_enabled=None,
                    observed_expires_at=None,
                    sync_state="error",
                    last_error=str(exc),
                    xui_sub_id=sub_id,
                )
                LOGGER.exception(
                    "Cluster sync failed for node_id=%s subscription_id=%s",
                    node_id,
                    subscription_id,
                )

        if bool(node.get("needs_backfill")):
            if node_had_failures:
                await db.mark_node_backfill_error(node_id, "sync errors occurred during backfill")
            else:
                remaining = await db.list_subscriptions_needing_sync(node_id, limit=1)
                if not remaining:
                    await db.mark_node_backfill_completed(node_id)

    return {"nodes": len(nodes), "processed": processed, "ok": ok_count, "failed": failed_count}
