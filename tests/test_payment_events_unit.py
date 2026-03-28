import json
import unittest

from src.db import DB


class FakePool:
    def __init__(self) -> None:
        self.events: dict[tuple[str, str], dict[str, object]] = {}

    async def fetchrow(self, query: str, *args):
        if "INSERT INTO payment_events" in query:
            provider, event_id, body_json = args
            key = (provider, event_id)
            if key in self.events:
                return None
            body = json.loads(body_json)
            event = {
                "id": len(self.events) + 1,
                "provider": provider,
                "event_id": event_id,
                "body": body,
                "processed": False,
            }
            self.events[key] = event
            return {"id": event["id"]}

        if "UPDATE payment_events" in query and "processed_at" in query:
            provider, event_id = args
            event = self.events.get((provider, event_id))
            if not event:
                return None
            event["processed"] = True
            return {"id": event["id"]}

        raise AssertionError(f"Unexpected query: {query}")


class PaymentEventsDedupUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_insert_payment_event_if_new_deduplicates_by_provider_and_event_id(self):
        db = DB("postgresql://unused")
        db.pool = FakePool()

        first = await db.insert_payment_event_if_new("reference", "evt-1", {"a": 1})
        second = await db.insert_payment_event_if_new("reference", "evt-1", {"a": 2})
        other_provider = await db.insert_payment_event_if_new("other", "evt-1", {"a": 3})

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(other_provider)

    async def test_mark_payment_event_processed_returns_false_for_unknown_event(self):
        db = DB("postgresql://unused")
        db.pool = FakePool()

        ok = await db.insert_payment_event_if_new("reference", "evt-2", {"raw": True})
        marked_existing = await db.mark_payment_event_processed("reference", "evt-2")
        marked_missing = await db.mark_payment_event_processed("reference", "evt-missing")

        self.assertTrue(ok)
        self.assertTrue(marked_existing)
        self.assertFalse(marked_missing)


if __name__ == "__main__":
    unittest.main()
