import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.xui_client import (
    NO_EXPIRY_SENTINEL,
    RESERVED_PLACEHOLDER_COMMENT,
    RESERVED_PLACEHOLDER_EMAIL,
    XUIClient,
)


class XUIClientDeleteUnitTests(unittest.TestCase):
    def test_last_client_delete_becomes_reserved_placeholder(self):
        client = XUIClient("https://panel.local", "user", "pass")
        client._post = AsyncMock(side_effect=RuntimeError("Something went wrong (no client remained in Inbound)"))
        client.update_client = AsyncMock()
        client.set_client_enabled = AsyncMock()

        result = asyncio.run(
            client.del_client(
                1,
                "11111111-1111-1111-1111-111111111111",
                email="user@example.com",
                expiry=datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                limit_ip=1,
                flow="xtls-rprx-vision",
                sub_id="abc123",
            )
        )

        self.assertEqual(result, "placeholder")
        client.update_client.assert_awaited_once_with(
            1,
            "11111111-1111-1111-1111-111111111111",
            RESERVED_PLACEHOLDER_EMAIL,
            NO_EXPIRY_SENTINEL,
            limit_ip=0,
            flow="",
            comment=RESERVED_PLACEHOLDER_COMMENT,
            sub_id=None,
            enable=False,
        )
        client.set_client_enabled.assert_not_awaited()

    def test_non_last_client_delete_falls_back_to_disable(self):
        client = XUIClient("https://panel.local", "user", "pass")
        client._post = AsyncMock(side_effect=RuntimeError("random delete failure"))
        client.update_client = AsyncMock()
        client.set_client_enabled = AsyncMock()
        expiry = datetime(2026, 1, 1, tzinfo=timezone.utc)

        result = asyncio.run(
            client.del_client(
                1,
                "11111111-1111-1111-1111-111111111111",
                email="user@example.com",
                expiry=expiry,
                limit_ip=1,
                flow="xtls-rprx-vision",
                sub_id="abc123",
            )
        )

        self.assertEqual(result, "disabled")
        client.update_client.assert_not_awaited()
        client.set_client_enabled.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
