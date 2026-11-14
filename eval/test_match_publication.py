"""Offline tests: no credentials or database connections required."""
import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.common import db


def row(company, opportunity, rank=1):
    return {
        "company_id": company,
        "opportunity_id": opportunity,
        "rank": rank,
        "score": 0.5,
        "reason": "Supported company-specific reason",
    }


class FakeDatabase:
    def __init__(self, fail=None):
        self.rows = {
            ("oht", "old"): row("oht", "old"),
            ("other", "keep"): row("other", "keep"),
        }
        self.fail = fail
        self.operations = []
        self.snapshots = []

    def table(self, name):
        assert name == "matches"
        return self

    def upsert(self, rows, on_conflict):
        assert on_conflict == "company_id,opportunity_id"

        def execute():
            self.operations.append("upsert")
            if self.fail == "upsert":
                raise RuntimeError("simulated upsert failure")
            for item in rows:
                self.rows[(item["company_id"], item["opportunity_id"])] = dict(item)
            self.snapshots.append(copy.deepcopy(self.rows))
            return SimpleNamespace(data=rows)

        return SimpleNamespace(execute=execute)

    def delete(self):
        return self

    def eq(self, column, value):
        assert column == "company_id"
        self.company = value
        return self

    @property
    def not_(self):
        return self

    def in_(self, column, values):
        assert column == "opportunity_id"
        self.keep = set(values)
        return self

    def execute(self):
        self.operations.append("cleanup")
        if self.fail == "cleanup":
            raise RuntimeError("simulated cleanup failure")
        self.rows = {
            key: value for key, value in self.rows.items()
            if key[0] != self.company or key[1] in self.keep
        }
        self.snapshots.append(copy.deepcopy(self.rows))
        return SimpleNamespace(data=[])


class PublicationTests(unittest.TestCase):
    def test_new_rows_written_before_cleanup_and_other_company_preserved(self):
        fake = FakeDatabase()
        with patch.object(db, "client", return_value=fake):
            count = db.replace_matches(
                "oht", [row("oht", "new-a", 1), row("oht", "new-b", 2)]
            )
        self.assertEqual(count, 2)
        self.assertEqual(fake.operations, ["upsert", "cleanup"])
        self.assertEqual(
            set(fake.rows),
            {("oht", "new-a"), ("oht", "new-b"), ("other", "keep")},
        )
        for snapshot in fake.snapshots:
            self.assertTrue(any(company == "oht" for company, _ in snapshot))

    def test_upsert_failure_preserves_existing_feed(self):
        fake = FakeDatabase(fail="upsert")
        before = copy.deepcopy(fake.rows)
        with patch.object(db, "client", return_value=fake):
            with self.assertRaises(RuntimeError):
                db.replace_matches("oht", [row("oht", "new")])
        self.assertEqual(fake.rows, before)
        self.assertEqual(fake.operations, ["upsert"])

    def test_cleanup_failure_keeps_new_and_old_rows(self):
        fake = FakeDatabase(fail="cleanup")
        with patch.object(db, "client", return_value=fake):
            with self.assertRaises(RuntimeError):
                db.replace_matches("oht", [row("oht", "new")])
        self.assertIn(("oht", "old"), fake.rows)
        self.assertIn(("oht", "new"), fake.rows)
        self.assertIn(("other", "keep"), fake.rows)

    def test_invalid_batches_never_access_database(self):
        invalid = [
            [],
            [row("other", "x")],
            [row("oht", "x", 1), row("oht", "x", 2)],
            [row("oht", "x", 2)],
            [{**row("oht", "x"), "score": float("nan")}],
            [{**row("oht", "x"), "reason": ""}],
        ]
        for batch in invalid:
            with self.subTest(batch=batch):
                with patch.object(db, "client") as client:
                    with self.assertRaises(ValueError):
                        db.replace_matches("oht", batch)
                    client.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
