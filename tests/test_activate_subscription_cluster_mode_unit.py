import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Settings
from src.domain.subscriptions import activate_subscription


def _settings(*, cluster_enabled: bool) -> Settings:
    return Settings(
        telegram_bot_token="token",
        telegram_admin_id=1,
        database_url="postgresql://unused",
        xui_base_url="https://xui.local",
        xui_username="u",
        xui_password="p",
        xui_inbound_id=1,
        xui_sub_port=2096,
        vpn_public_host="lb.vxcloud.ru",
        vpn_public_port=41068,
        vpn_cluster_enabled=cluster_enabled,
        vpn_cluster_healthcheck_interval_seconds=30,
        vpn_cluster_sync_interval_seconds=60,
        vpn_cluster_sync_batch_size=200,
        vpn_tag="VXcloud",
        plan_days=30,
        plan_price_stars=250,
        max_devices_per_sub=1,
        price_text="Monthly plan",
        timezone="UTC",
        cms_base_url=None,
        cms_token=None,
        cms_content_collection="bot_content",
        cms_button_collection="bot_buttons",
        cms_cache_ttl_seconds=60,
        magic_link_shared_secret=None,
        magic_link_api_timeout_seconds=5,
        enforce_single_ip=False,
        single_ip_check_interval_seconds=20,
        single_ip_window_seconds=90,
        single_ip_block_seconds=120,
        xray_access_log_path="/var/log/xray/access.log",
    )


def _xui_mock() -> MagicMock:
    xui = MagicMock()
    xui.parse_reality.return_value = SimpleNamespace(
        public_key="pubkey",
        short_id="abcd",
        sni="www.cloudflare.com",
        fingerprint="chrome",
    )
    xui.get_inbound = AsyncMock(return_value={"port": 443})
    xui.add_client = AsyncMock(return_value=None)
    xui.update_client = AsyncMock(return_value=None)
    xui.get_client_sub_id = AsyncMock(return_value="single-node-sub-id")
    return xui


class _FakeNodeXUI:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get_inbound(self, inbound_id: int) -> dict[str, object]:
        return {"port": 29940, "id": inbound_id}

    def parse_reality(self, inbound_obj):  # noqa: ANN001
        return SimpleNamespace(
            public_key="cluster-pubkey",
            short_id="ec40",
            sni="www.cloudflare.com",
            fingerprint="chrome",
        )


class ActivateSubscriptionClusterModeUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_single_node_mode_does_not_use_cluster_ensure(self):
        now = datetime.now(timezone.utc)
        db = AsyncMock()
        db.claim_order_for_activation.return_value = {
            "id": 501,
            "user_id": 7,
            "status": "paid",
            "payload": "renew:7:777:1711:abc",
        }
        db.get_user_client_code.return_value = "VX-000007"
        db.get_subscription.return_value = {
            "id": 777,
            "user_id": 7,
            "client_uuid": "00000000-0000-0000-0000-000000000001",
            "client_email": "tg_7_seed",
            "expires_at": now + timedelta(days=10),
            "vless_url": "vless://existing",
            "xui_sub_id": "sub-old",
        }
        db.get_active_subscription.return_value = None

        with patch("src.domain.subscriptions.ensure_client_on_all_active_nodes", new=AsyncMock()) as ensure_mock:
            result = await activate_subscription(
                501,
                db=db,
                xui=_xui_mock(),
                settings=_settings(cluster_enabled=False),
            )

        ensure_mock.assert_not_awaited()
        self.assertEqual(result.subscription_id, 777)
        self.assertFalse(result.created)
        self.assertFalse(result.idempotent)
        db.extend_subscription.assert_awaited_once()

    async def test_cluster_mode_uses_cluster_ensure_and_public_host_port_link(self):
        db = AsyncMock()
        db.claim_order_for_activation.return_value = {
            "id": 601,
            "user_id": 9,
            "status": "paid",
            "payload": "buynew:9:1711:abc",
        }
        db.get_user_client_code.return_value = "VX-000009"
        db.get_active_subscription.return_value = None
        db.create_subscription.return_value = 9001
        db.get_active_vpn_nodes.return_value = [
            {
                "id": 2,
                "xui_base_url": "https://node-2.local",
                "xui_username": "u2",
                "xui_password": "p2",
                "xui_inbound_id": 1,
                "is_active": True,
                "lb_enabled": True,
                "last_health_ok": False,
            },
            {
                "id": 1,
                "xui_base_url": "https://node-1.local",
                "xui_username": "u1",
                "xui_password": "p1",
                "xui_inbound_id": 1,
                "is_active": True,
                "lb_enabled": True,
                "last_health_ok": True,
            },
        ]

        with (
            patch("src.domain.subscriptions.XUIClient", new=_FakeNodeXUI),
            patch(
                "src.domain.subscriptions.ensure_client_on_all_active_nodes",
                new=AsyncMock(return_value={"total": 2, "ok": 2, "failed": 0, "results": []}),
            ) as ensure_mock,
        ):
            result = await activate_subscription(
                601,
                db=db,
                xui=_xui_mock(),
                settings=_settings(cluster_enabled=True),
            )

        ensure_mock.assert_awaited_once()
        create_kwargs = db.create_subscription.await_args.kwargs
        created_vless = str(create_kwargs["vless_url"])
        self.assertIn("@lb.vxcloud.ru:41068", created_vless)
        self.assertEqual(result.vless_url, created_vless)
        self.assertTrue(result.created)
        self.assertFalse(result.idempotent)


if __name__ == "__main__":
    unittest.main()
