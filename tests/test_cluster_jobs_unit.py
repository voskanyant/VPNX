import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.cluster.jobs import healthcheck_tick, sync_tick


class _FakeHealthXUI:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password

    async def start(self) -> None:
        if "down" in self.base_url:
            raise RuntimeError("node unavailable")

    async def close(self) -> None:
        return None

    async def get_inbound(self, inbound_id: int):  # noqa: ANN001
        return {"port": 29940, "id": inbound_id}

    def parse_reality(self, inbound):  # noqa: ANN001
        return SimpleNamespace(
            public_key="pubkey",
            short_id="ec40",
            sni="www.cloudflare.com",
            fingerprint="chrome",
        )


class ClusterJobsUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_healthcheck_tick_marks_ok_and_failed_nodes(self):
        db = AsyncMock()
        db.get_active_vpn_nodes.return_value = [
            {
                "id": 1,
                "xui_base_url": "https://node-ok.local",
                "xui_username": "u1",
                "xui_password": "p1",
                "xui_inbound_id": 1,
                "is_active": True,
            },
            {
                "id": 2,
                "xui_base_url": "https://node-down.local",
                "xui_username": "u2",
                "xui_password": "p2",
                "xui_inbound_id": 1,
                "is_active": True,
            },
        ]

        with patch("src.cluster.jobs.XUIClient", new=_FakeHealthXUI):
            result = await healthcheck_tick(db)

        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["ok"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(db.mark_node_health.await_count, 2)

    async def test_sync_tick_retries_duplicate_with_update(self):
        db = AsyncMock()
        db.get_active_vpn_nodes.return_value = [
            {
                "id": 10,
                "xui_base_url": "https://node.local",
                "xui_username": "u",
                "xui_password": "p",
                "xui_inbound_id": 1,
                "is_active": True,
                "lb_enabled": True,
            }
        ]
        db.list_subscriptions_needing_sync.return_value = [
            {
                "subscription_id": 101,
                "client_uuid": "00000000-0000-0000-0000-000000000101",
                "client_email": "tg_1_101",
                "xui_sub_id": "sid-101",
                "desired_enabled": True,
                "desired_expires_at": datetime.now(timezone.utc) + timedelta(days=10),
                "sync_state": "pending",
            }
        ]
        settings = SimpleNamespace(vpn_cluster_sync_batch_size=100, max_devices_per_sub=1)

        with (
            patch(
                "src.cluster.jobs.create_client_on_node",
                new=AsyncMock(side_effect=RuntimeError("already exists")),
            ) as create_mock,
            patch(
                "src.cluster.jobs.update_client_on_node",
                new=AsyncMock(return_value={"xui_sub_id": "sid-101"}),
            ) as update_mock,
            patch(
                "src.cluster.jobs.delete_or_disable_client_on_node",
                new=AsyncMock(return_value={"xui_sub_id": "sid-101"}),
            ) as delete_mock,
        ):
            result = await sync_tick(db, settings)

        self.assertEqual(result["nodes"], 1)
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["ok"], 1)
        self.assertEqual(result["failed"], 0)
        create_mock.assert_awaited_once()
        update_mock.assert_awaited_once()
        delete_mock.assert_not_awaited()

        upsert_kwargs = db.upsert_vpn_node_client_state.await_args.kwargs
        self.assertEqual(upsert_kwargs["sync_state"], "ok")
        self.assertTrue(upsert_kwargs["desired_enabled"])


if __name__ == "__main__":
    unittest.main()
