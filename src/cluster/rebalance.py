from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from src.config import Settings
from src.db import DB
from src.subscription_links import build_subscription_vless_url
from src.xui_client import InboundRealityInfo


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class NodeScore:
    node: dict[str, Any]
    score: float
    reasons: dict[str, float]


def _node_reality_from_health(node: dict[str, Any]) -> InboundRealityInfo | None:
    public_key = str(node.get("last_reality_public_key") or "").strip()
    short_id = str(node.get("last_reality_short_id") or "").strip()
    sni = str(node.get("last_reality_sni") or "").strip()
    fingerprint = str(node.get("last_reality_fingerprint") or "chrome").strip() or "chrome"
    if not (public_key and short_id and sni):
        return None
    return InboundRealityInfo(
        public_key=public_key,
        short_id=short_id,
        sni=sni,
        fingerprint=fingerprint,
    )


def score_node(node: dict[str, Any]) -> NodeScore | None:
    if not bool(node.get("is_active")):
        return None
    if not bool(node.get("lb_enabled")):
        return None
    if bool(node.get("needs_backfill")):
        return None
    if node.get("last_health_ok") is not True:
        return None
    if _node_reality_from_health(node) is None:
        return None

    active_assigned = float(node.get("active_assigned_subscriptions") or 0)
    observed_enabled = float(node.get("observed_enabled_clients") or 0)
    total_traffic = float(node.get("total_traffic_bytes") or 0)
    peak_concurrency = float(node.get("peak_concurrency") or 0)
    moves_in_week = float(node.get("moves_in_week") or 0)
    weight = float(node.get("backend_weight") or 100)
    if weight <= 0:
        weight = 100.0

    reasons = {
        "active_assigned": active_assigned * 4.0,
        "observed_enabled": observed_enabled * 3.0,
        "traffic": total_traffic / float(10 * 1024 * 1024 * 1024),
        "peak_concurrency": peak_concurrency * 2.0,
        "recent_moves": moves_in_week * 1.5,
    }
    raw_score = sum(reasons.values())
    normalized = raw_score / max(weight / 100.0, 0.25)
    return NodeScore(node=node, score=normalized, reasons=reasons)


async def pick_best_node(db: DB) -> NodeScore | None:
    metrics = await db.list_node_assignment_metrics()
    scored = [item for item in (score_node(node) for node in metrics) if item is not None]
    if not scored:
        return None
    scored.sort(key=lambda item: (item.score, int(item.node.get("id", 0) or 0)))
    return scored[0]


async def backfill_unassigned_subscriptions(db: DB, settings: Settings, *, limit: int = 200) -> dict[str, int]:
    pending = await db.list_unassigned_active_subscriptions(limit=limit)
    if not pending:
        return {"processed": 0, "assigned": 0, "skipped": 0}

    assigned = 0
    skipped = 0
    for sub in pending:
        best = await pick_best_node(db)
        if best is None:
            skipped += 1
            continue
        reality = _node_reality_from_health(best.node)
        if reality is None:
            skipped += 1
            continue
        vless_url = build_subscription_vless_url(
            settings=settings,
            node=best.node,
            client_uuid=str(sub["client_uuid"]),
            reality=reality,
        )
        await db.update_subscription_assignment(
            int(sub["id"]),
            assigned_node_id=int(best.node["id"]),
            vless_url=vless_url,
            assignment_source="migration_backfill",
            migration_state="ready",
            mark_rebalanced=False,
        )
        await db.record_rebalance_decision(
            subscription_id=int(sub["id"]),
            from_node_id=None,
            to_node_id=int(best.node["id"]),
            decision_kind="migration_backfill",
            score_before=None,
            score_after=best.score,
            reason="subscription had no assigned node",
            details={"reasons": best.reasons},
        )
        assigned += 1

    return {"processed": len(pending), "assigned": assigned, "skipped": skipped}


async def rebalance_tick(db: DB, settings: Settings) -> dict[str, int]:
    metrics = await db.list_node_assignment_metrics()
    scored = [item for item in (score_node(node) for node in metrics) if item is not None]
    if len(scored) < 2:
        return {"moved": 0, "considered": 0, "from_nodes": 0, "to_nodes": 0}

    scored.sort(key=lambda item: item.score)
    underloaded = scored[0]
    overloaded = scored[-1]
    if (overloaded.score - underloaded.score) < float(settings.vpn_rebalance_min_score_gap):
        return {"moved": 0, "considered": 0, "from_nodes": 1, "to_nodes": 1}

    max_moves = max(1, int(settings.vpn_rebalance_max_moves_per_node))
    overload_count = int(overloaded.node.get("active_assigned_subscriptions") or 0)
    move_cap = max(1, min(max_moves, int(overload_count * float(settings.vpn_rebalance_move_fraction or 0.2))))
    candidates = await db.list_rebalance_candidates(
        int(overloaded.node["id"]),
        cooldown_hours=int(settings.vpn_rebalance_cooldown_hours),
        limit=move_cap,
    )
    moved = 0
    for sub in candidates:
        reality = _node_reality_from_health(underloaded.node)
        if reality is None:
            break
        vless_url = build_subscription_vless_url(
            settings=settings,
            node=underloaded.node,
            client_uuid=str(sub["client_uuid"]),
            reality=reality,
        )
        await db.update_subscription_assignment(
            int(sub["id"]),
            assigned_node_id=int(underloaded.node["id"]),
            vless_url=vless_url,
            assignment_source="weekly_rebalance",
            migration_state="ready",
            mark_rebalanced=True,
        )
        await db.record_rebalance_decision(
            subscription_id=int(sub["id"]),
            from_node_id=int(overloaded.node["id"]),
            to_node_id=int(underloaded.node["id"]),
            decision_kind="weekly_rebalance",
            score_before=overloaded.score,
            score_after=underloaded.score,
            reason="score gap exceeded threshold",
            details={
                "from_reasons": overloaded.reasons,
                "to_reasons": underloaded.reasons,
            },
        )
        moved += 1

    return {"moved": moved, "considered": len(candidates), "from_nodes": 1, "to_nodes": 1}
