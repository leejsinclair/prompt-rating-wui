import json
import tempfile
import unittest
from pathlib import Path

from src.favorites import FavoritePromptsStore, InvalidFavoritesStoreError
from src.ratings import InvalidStoreError, RatingsStore


class StoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "nested" / "ratings.json"
        self.store = RatingsStore(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_is_empty_store(self):
        self.assertEqual(self.store.load(), {})

    def test_set_creates_directory_and_round_trips(self):
        record = self.store.set("p1", "s1", 3, 8)
        self.assertTrue(self.path.exists())
        self.assertEqual(record["value"], 8)
        loaded = RatingsStore(self.path).load()
        self.assertEqual(loaded["p1"]["value"], 8)
        self.assertEqual((loaded["p1"]["session_id"], loaded["p1"]["position"]), ("s1", 3))

    def test_rerating_overwrites_and_updates_rated_at(self):
        first = self.store.set("p1", "s1", 0, 4)
        second = self.store.set("p1", "s1", 0, 9)
        data = self.store.load()
        self.assertEqual(len(data), 1)
        self.assertEqual(data["p1"]["value"], 9)
        self.assertGreater(second["rated_at"], first["rated_at"])

    def test_out_of_range_value_rejected_on_set(self):
        for bad in (0, 11, -1, 5.5, "7", True, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.store.set("p1", "s1", 0, bad)
        self.assertEqual(self.store.load(), {})

    def _write_raw(self, text):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text)

    def test_invalid_json_is_invalid_state(self):
        self._write_raw("not json")
        with self.assertRaises(InvalidStoreError):
            self.store.load()

    def test_wrong_shape_is_invalid_state(self):
        for payload in ([], {"p": 5}, {"p": {"value": 5}}, {"p": {"value": 5, "session_id": "s", "position": -1, "rated_at": "t"}}):
            with self.subTest(payload=payload):
                self._write_raw(json.dumps(payload))
                with self.assertRaises(InvalidStoreError):
                    self.store.load()

    def test_out_of_range_stored_value_is_invalid_state(self):
        for value in (0, 11, "8", True):
            with self.subTest(value=value):
                self._write_raw(json.dumps({"p": {"value": value, "session_id": "s", "position": 0, "rated_at": "t"}}))
                with self.assertRaises(InvalidStoreError):
                    self.store.load()

    def test_set_refuses_to_overwrite_invalid_store(self):
        self._write_raw("garbage")
        with self.assertRaises(InvalidStoreError):
            self.store.set("p1", "s1", 0, 5)
        self.assertEqual(self.path.read_text(), "garbage")

    def test_reset_deletes_file_and_recovers(self):
        self._write_raw("garbage")
        self.store.reset()
        self.assertFalse(self.path.exists())
        self.assertEqual(self.store.load(), {})
        self.store.set("p1", "s1", 0, 5)
        self.assertEqual(self.store.load()["p1"]["value"], 5)

    def test_reset_when_file_absent_succeeds(self):
        self.store.reset()


class FavoriteStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "nested" / "favorites.json"
        self.store = FavoritePromptsStore(self.path)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_is_empty_store(self):
        self.assertEqual(self.store.load(), {})

    def test_create_creates_directory_and_round_trips(self):
        record = self.store.create("Prompt text")
        self.assertTrue(self.path.exists())
        self.assertEqual(record["text"], "Prompt text")
        loaded = FavoritePromptsStore(self.path).load()
        self.assertEqual(loaded[record["favorite_prompt_id"]]["text"], "Prompt text")

    def test_update_overwrites_text_and_updates_timestamp(self):
        first = self.store.create("Prompt text")
        second = self.store.update(first["favorite_prompt_id"], "Updated prompt")
        data = self.store.load()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[first["favorite_prompt_id"]]["text"], "Updated prompt")
        self.assertEqual(second["created_at"], first["created_at"])
        self.assertGreater(second["updated_at"], first["updated_at"])

    def test_blank_text_rejected(self):
        for bad in ("", "   ", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.store.create(bad)
        created = self.store.create("Prompt text")
        with self.assertRaises(ValueError):
            self.store.update(created["favorite_prompt_id"], " ")

    def _write_raw(self, text):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(text)

    def test_invalid_json_is_invalid_state(self):
        self._write_raw("not json")
        with self.assertRaises(InvalidFavoritesStoreError):
            self.store.load()

    def test_wrong_shape_is_invalid_state(self):
        for payload in ([], {"p": 5}, {"p": {"text": "ok"}}, {"p": {"text": "", "created_at": "t", "updated_at": "t"}}):
            with self.subTest(payload=payload):
                self._write_raw(json.dumps(payload))
                with self.assertRaises(InvalidFavoritesStoreError):
                    self.store.load()


if __name__ == "__main__":
    unittest.main()
