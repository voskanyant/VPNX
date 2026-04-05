import unittest
from datetime import datetime, timedelta, timezone

from src.db import DB
from src.db import _site_placeholder_telegram_id_for_auth_user


class _AsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.tokens = {
            "LINKME": {
                "id": 11,
                "user_id": 77,
                "expires_at": now + timedelta(minutes=10),
                "consumed_at": None,
                "consumed_telegram_id": None,
            }
        }
        placeholder_telegram_id = _site_placeholder_telegram_id_for_auth_user(77)
        self.users = {
            5: {
                "id": 5,
                "telegram_id": placeholder_telegram_id,
                "username": "site-user",
                "first_name": "Site",
            },
            7: {
                "id": 7,
                "telegram_id": 555001,
                "username": "tg-user",
                "first_name": "Telegram",
            },
        }
        self.orders = [{"id": 1, "user_id": 7}]
        self.subscriptions = [{"id": 2, "user_id": 7}]
        self.support_tickets = [{"id": 3, "user_id": 7}]
        self.support_messages = [{"id": 4, "sender_user_id": 7}]
        self.linked_accounts = {}

    def transaction(self):
        return _AsyncContext()

    async def fetchrow(self, query: str, *args):
        if "FROM cabinet_telegramlinktoken" in query and "consumed_at IS NULL" in query:
            code = args[0]
            token = self.tokens.get(code)
            if not token:
                return None
            if token["consumed_at"] is not None or token["expires_at"] <= datetime.now(timezone.utc):
                return None
            return {"id": token["id"], "user_id": token["user_id"]}

        if "SELECT consumed_at, expires_at FROM cabinet_telegramlinktoken" in query:
            code = args[0]
            token = self.tokens.get(code)
            if not token:
                return None
            return {
                "consumed_at": token["consumed_at"],
                "expires_at": token["expires_at"],
            }

        if "SELECT id, username, first_name" in query and "FROM users" in query:
            telegram_id = args[0]
            for user in self.users.values():
                if int(user["telegram_id"]) == int(telegram_id):
                    return {
                        "id": user["id"],
                        "username": user["username"],
                        "first_name": user["first_name"],
                    }
            return None

        if "SELECT id" in query and "FROM users" in query:
            telegram_id = args[0]
            for user in self.users.values():
                if int(user["telegram_id"]) == int(telegram_id):
                    return {"id": user["id"]}
            return None

        raise AssertionError(f"Unexpected fetchrow query: {query}")

    async def execute(self, query: str, *args):
        if query.startswith("UPDATE orders SET user_id = $1 WHERE user_id = $2"):
            target_user_id, source_user_id = args
            for item in self.orders:
                if item["user_id"] == source_user_id:
                    item["user_id"] = target_user_id
            return "UPDATE"

        if query.startswith("UPDATE subscriptions SET user_id = $1 WHERE user_id = $2"):
            target_user_id, source_user_id = args
            for item in self.subscriptions:
                if item["user_id"] == source_user_id:
                    item["user_id"] = target_user_id
            return "UPDATE"

        if query.startswith("UPDATE support_tickets SET user_id = $1 WHERE user_id = $2"):
            target_user_id, source_user_id = args
            for item in self.support_tickets:
                if item["user_id"] == source_user_id:
                    item["user_id"] = target_user_id
            return "UPDATE"

        if query.startswith("UPDATE support_messages SET sender_user_id = $1 WHERE sender_user_id = $2"):
            target_user_id, source_user_id = args
            for item in self.support_messages:
                if item["sender_user_id"] == source_user_id:
                    item["sender_user_id"] = target_user_id
            return "UPDATE"

        if "UPDATE users" in query and "username = COALESCE($2, username)" in query:
            telegram_id, username, first_name, user_id = args
            user = self.users[int(user_id)]
            user["telegram_id"] = int(telegram_id)
            if username is not None:
                user["username"] = username
            if first_name is not None:
                user["first_name"] = first_name
            return "UPDATE"

        if query.startswith("UPDATE users") and "SET telegram_id = $1" in query:
            telegram_id, user_id = args
            self.users[int(user_id)]["telegram_id"] = int(telegram_id)
            return "UPDATE"

        if query.startswith("DELETE FROM users WHERE id = $1"):
            user_id = int(args[0])
            self.users.pop(user_id, None)
            return "DELETE"

        if query.startswith("DELETE FROM cabinet_linkedaccount"):
            telegram_id, keep_user_id = args
            for user_id, linked_telegram_id in list(self.linked_accounts.items()):
                if int(linked_telegram_id) == int(telegram_id) and int(user_id) != int(keep_user_id):
                    self.linked_accounts.pop(user_id, None)
            return "DELETE"

        if "INSERT INTO cabinet_linkedaccount" in query:
            user_id, telegram_id = args
            self.linked_accounts[int(user_id)] = int(telegram_id)
            return "INSERT"

        if "UPDATE cabinet_telegramlinktoken" in query:
            token_id, telegram_id = args
            for token in self.tokens.values():
                if int(token["id"]) == int(token_id):
                    token["consumed_at"] = datetime.now(timezone.utc)
                    token["consumed_telegram_id"] = int(telegram_id)
                    return "UPDATE"
            raise AssertionError("Token not found")

        raise AssertionError(f"Unexpected execute query: {query}")


class _Acquire:
    def __init__(self, conn: FakeConn) -> None:
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn: FakeConn) -> None:
        self.conn = conn

    def acquire(self):
        return _Acquire(self.conn)


class TelegramLinkMergeUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_consume_link_code_merges_placeholder_user_into_real_telegram_identity(self):
        conn = FakeConn()
        db = DB("postgresql://unused")
        db.pool = FakePool(conn)

        status = await db.consume_telegram_link_code("linkme", 555001)

        self.assertEqual(status, "ok")
        self.assertEqual(conn.linked_accounts[77], 555001)
        self.assertEqual(conn.tokens["LINKME"]["consumed_telegram_id"], 555001)
        self.assertIsNotNone(conn.tokens["LINKME"]["consumed_at"])
        self.assertNotIn(7, conn.users)
        self.assertEqual(conn.users[5]["telegram_id"], 555001)
        self.assertEqual(conn.users[5]["username"], "tg-user")
        self.assertEqual(conn.users[5]["first_name"], "Telegram")
        self.assertEqual(conn.orders[0]["user_id"], 5)
        self.assertEqual(conn.subscriptions[0]["user_id"], 5)
        self.assertEqual(conn.support_tickets[0]["user_id"], 5)
        self.assertEqual(conn.support_messages[0]["sender_user_id"], 5)


if __name__ == "__main__":
    unittest.main()
