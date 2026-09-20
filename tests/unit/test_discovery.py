import os
import tempfile
import unittest
from pathlib import Path

from src.discovery import discover_session_files


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, rel, mtime=None):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
        if mtime is not None:
            os.utime(path, (mtime, mtime))
        return path

    def test_missing_root_returns_empty(self):
        self.assertEqual(discover_session_files(self.root / "nope"), [])

    def test_empty_root_returns_empty(self):
        self.assertEqual(discover_session_files(self.root), [])

    def test_single_project(self):
        a = self._touch("-home-a/one.jsonl")
        self.assertEqual(discover_session_files(self.root), [a])

    def test_multiple_projects_newest_first(self):
        old = self._touch("-home-a/old.jsonl", mtime=1000)
        new = self._touch("-home-b/new.jsonl", mtime=2000)
        self.assertEqual(discover_session_files(self.root), [new, old])

    def test_ignores_non_jsonl_and_nested_files(self):
        self._touch("-home-a/notes.txt")
        self._touch("-home-a/sub/deep.jsonl")
        self._touch("stray.jsonl")
        self.assertEqual(discover_session_files(self.root), [])


if __name__ == "__main__":
    unittest.main()
