import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from src.cluster.provisioner import ensure_client_on_all_active_nodes


class FakeXUIClient:
    instances: list["FakeXUIClient"] = []
    delete_mode: str = "deleted"
    duplicate_add_failures_remaining: int = 0

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password
        self.calls: list[tuple[str, tuple, dict]] = []
        self.__class__.instances.append(self)

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def add_client(self, *args, **kwargs) -> None:
        self.calls.append(("add_client", args, kwargs))
        if self.__class__.duplicate_add_failures_remaining > 0:
            self.__class__.duplicate_add_failures_remaining -= 1
            raise RuntimeError("already exists")

    async def update_client(self, *args, **kwargs) -> None:
        self.calls.append(("update_client", args, kwargs))

    async def del_client(self, *args, **kwargs) -> str:
        self.calls.append(("del_client", args, kwargs))
        if self.__class__.delete_mode == "error":
            raise RuntimeError("delete failed")
        return self.__class__.delete_mode

    async def delete_client(self, *args, **kwargs) -> str:
        self.calls.append(("delete_client", args, kwargs))
        return await self.del_client(*args, **kwargs)

    async def set_client_enabled(self, *args, **kwargs) -> None:
        self.calls.append(("set_client_enabled", args, kwargs))

    async def get_client_sub_id(self, *args, **kwargs) -> str:
        self.calls.append(("get_client_sub_id", args, kwargs))
        return "node-sub-id"


class ClusterProvisionerUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_ensure_client_syncs_all_nodes_and_persists_ok_state(self):
        FakeXUIClient.instances.clear()
        FakeXUIClient.delete_mode = "deleted"
        FakeXUIClient.duplicate_add_failures_remaining = 0
        db = AsyncMock()
        db.get_active_vpn_nodes.return_value = [
            {
                "id": 1,
                "xui_base_url": "https://node-1.local",
                "xui_username": "u1",
                "xui_password": "p1",
                "xui_inbound_id": 101,
                "lb_enabled": True,
                "is_active": True,
            },
            {
                "id": 2,
                "xui_base_url": "https://node-2.local",
                "xui_username": "u2",
                "xui_password": "p2",
                "xui_inbound_id": 102,
                "lb_enabled": True,
                "is_active": True,
            },
        ]
        subscription_row = {
            "id": 777,
            "client_uuid": "11111111-2222-3333-4444-555555555555",
            "client_email": "tg_77_seed",
            "xui_sub_id": "seed-sub-id",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=5),
            "is_active": True,
            "revoked_at": None,
        }
        settings = type("SettingsStub", (), {"max_devices_per_sub": 1})()

        result = await ensure_client_on_all_active_nodes(
            db,
            subscription_row,
            settings,
            xui_client_factory=FakeXUIClient,
        )

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["ok"], 2)
        self.assertEqual(result["failed"], 0)
        db.get_active_vpn_nodes.assert_awaited_once_with(lb_only=True)
        self.assertEqual(db.upsert_vpn_node_client_state.await_count, 2)

        self.assertEqual(len(FakeXUIClient.instances), 2)
        for client in FakeXUIClient.instances:
            call_names = [name for name, _, _ in client.calls]
            self.assertIn("add_client", call_names)
            add_call = next(item for item in client.calls if item[0] == "add_client")
            self.assertEqual(add_call[2].get("sub_id"), "seed-sub-id")

    async def test_ensure_client_duplicate_on_one_node_falls_back_to_update(self):
        FakeXUIClient.instances.clear()
        FakeXUIClient.delete_mode = "deleted"
        FakeXUIClient.duplicate_add_failures_remaining = 1
        db = AsyncMock()
        db.get_active_vpn_nodes.return_value = [
            {
                "id": 1,
                "xui_base_url": "https://node-1.local",
                "xui_username": "u1",
                "xui_password": "p1",
                "xui_inbound_id": 101,
                "lb_enabled": True,
                "is_active": True,
            },
            {
                "id": 2,
                "xui_base_url": "https://node-2.local",
                "xui_username": "u2",
                "xui_password": "p2",
                "xui_inbound_id": 102,
                "lb_enabled": True,
                "is_active": True,
            },
        ]
        subscription_row = {
            "id": 778,
            "client_uuid": "11111111-2222-3333-4444-555555555556",
            "client_email": "tg_78_seed",
            "xui_sub_id": "seed-sub-id-2",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=5),
            "is_active": True,
            "revoked_at": None,
        }
        settings = type("SettingsStub", (), {"max_devices_per_sub": 1})()

        result = await ensure_client_on_all_active_nodes(
            db,
            subscription_row,
            settings,
            xui_client_factory=FakeXUIClient,
        )

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["ok"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(db.upsert_vpn_node_client_state.await_count, 2)

        all_calls = [[name for name, _, _ in client.calls] for client in FakeXUIClient.instances]
        self.assertTrue(all(("add_client" in calls) or ("update_client" in calls) for calls in all_calls))
        self.assertTrue(any("update_client" in calls for calls in all_calls))

    async def test_ensure_client_revoked_calls_del_client(self):
        FakeXUIClient.instances.clear()
        FakeXUIClient.delete_mode = "disabled"
        FakeXUIClient.duplicate_add_failures_remaining = 0
        db = AsyncMock()
        db.get_active_vpn_nodes.return_value = [
            {
                "id": 3,
                "xui_base_url": "https://node-3.local",
                "xui_username": "u3",
                "xui_password": "p3",
                "xui_inbound_id": 103,
                "lb_enabled": True,
                "is_active": True,
            }
        ]
        subscription_row = {
            "id": 888,
            "client_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "client_email": "tg_88_seed",
            "xui_sub_id": "sub-888",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=2),
            "is_active": False,
            "revoked_at": datetime.now(timezone.utc),
        }
        settings = type("SettingsStub", (), {"max_devices_per_sub": 1})()

        result = await ensure_client_on_all_active_nodes(
            db,
            subscription_row,
            settings,
            xui_client_factory=FakeXUIClient,
        )

        self.assertEqual(result["ok"], 1)
        call_names = [name for name, _, _ in FakeXUIClient.instances[0].calls]
        self.assertIn("del_client", call_names)
        self.assertNotIn("add_client", call_names)
        kwargs = db.upsert_vpn_node_client_state.await_args.kwargs
        self.assertFalse(kwargs["desired_enabled"])
        self.assertFalse(kwargs["observed_enabled"])
        self.assertEqual(kwargs["sync_state"], "ok")


if __name__ == "__main__":
    unittest.main()
