import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.favorites import FavoritePromptsStore
from src.ratings import RatingsStore
from src.server.common import Context
from src.server.server import create_server


def line(kind, **kw):
    return json.dumps(dict(type=kind, **kw))


def session_lines(prompts):
    out = []
    for i, (pid, text, resp) in enumerate(prompts):
        out.append(line("user", promptId=pid, timestamp=f"2026-01-01T00:0{i}:00Z", cwd="/w",
                        message={"role": "user", "content": text}))
        out.append(line("assistant", timestamp=f"2026-01-01T00:0{i}:30Z",
                        message={"role": "assistant", "content": [{"type": "text", "text": resp}]}))
    return "\n".join(out) + "\n"


class QuickstartTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.now = datetime(2026, 1, 10, tzinfo=timezone.utc)
        self.root = tmp / "projects"
        self.proj = self.root / "-w"
        self.proj.mkdir(parents=True)
        self.store_path = tmp / "cfg" / "ratings.json"
        self.favorites_path = tmp / "cfg" / "favorites.json"
        self.server = create_server(
            Context(
                store=RatingsStore(self.store_path),
                favorites_store=FavoritePromptsStore(self.favorites_path),
                projects_root=self.root,
                now=self.now,
            ),
            port=0,
        )
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._tmp.cleanup()

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, method=method, data=data)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def add_session(self, name, prompts):
        (self.proj / f"{name}.jsonl").write_text(session_lines(prompts))

    def test_empty_states(self):
        self.assertEqual(self.call("GET", "/api/sessions")[1], {"page": 1, "has_more": False, "sessions": []})
        self.assertEqual(self.call("GET", "/api/top-rated")[1], {"page": 1, "has_more": False, "prompts": []})
        self.assertEqual(self.call("GET", "/api/favorites")[1], {"prompts": []})

    def test_bind_address_is_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_browse_rate_rerate_and_top_rated_order(self):
        self.add_session("s1", [("a", "first", "r1"), ("b", "second", "r2")])
        self.add_session("s2", [("c", "third", "r3")])
        for pid, sid, pos, v in [("a", "s1", 0, 5), ("b", "s1", 1, 9), ("c", "s2", 0, 9)]:
            self.assertEqual(self.call("PUT", f"/api/ratings/{pid}", {"value": v, "session_id": sid, "position": pos})[0], 200)
        order = [p["prompt_id"] for p in self.call("GET", "/api/top-rated")[1]["prompts"]]
        self.assertEqual(order, ["c", "b", "a"])  # ties on 9 broken by most recently rated
        self.call("PUT", "/api/ratings/a", {"value": 10, "session_id": "s1", "position": 0})
        order = [p["prompt_id"] for p in self.call("GET", "/api/top-rated")[1]["prompts"]]
        self.assertEqual(order[0], "a")
        detail = self.call("GET", "/api/sessions/s1")[1]
        self.assertEqual([p["rating"] for p in detail["prompts"]], [10, 9])
        self.assertEqual(self.call("GET", "/api/sessions/s1/prompts/a")[1]["response_text"], "r1")

    def test_prompt_timestamp_response_flag_and_duration(self):
        self.add_session("s1", [("a", "first", "r1"), ("b", "", "")])
        prompts = self.call("GET", "/api/sessions/s1")[1]["prompts"]
        self.assertEqual(prompts[0]["timestamp"], "2026-01-01T00:00:00Z")
        self.assertEqual([p["has_response"] for p in prompts], [True, False])
        self.assertEqual(prompts[0]["duration_seconds"], 30)
        self.assertIn("activity_summary", prompts[0])
        self.assertEqual(self.call("GET", "/api/sessions/s1/prompts/a")[1]["duration_seconds"], 30)

    def test_pagination(self):
        for i in range(25):
            self.add_session(f"s{i:02d}", [(f"p{i}", "t", "r")])
        first = self.call("GET", "/api/sessions")[1]
        second = self.call("GET", "/api/sessions?page=2")[1]
        self.assertEqual((len(first["sessions"]), first["has_more"]), (20, True))
        self.assertEqual((len(second["sessions"]), second["has_more"]), (5, False))

    def test_sessions_without_prompts_are_hidden(self):
        self.add_session("shown", [("a", "hello", "r")])
        (self.proj / "hidden.jsonl").write_text(json.dumps({"type": "mode", "mode": "normal"}) + "\n")
        sessions = self.call("GET", "/api/sessions")[1]["sessions"]
        self.assertEqual([session["session_id"] for session in sessions], ["shown"])

    def test_prompt_search_only_returns_recent_matches(self):
        recent = self.now - timedelta(days=2)
        old = self.now - timedelta(days=8)
        (self.proj / "recent.jsonl").write_text(
            "\n".join(
                [
                    line(
                        "user",
                        promptId="recent-prompt",
                        timestamp=recent.isoformat().replace("+00:00", "Z"),
                        cwd="/w",
                        message={"role": "user", "content": "Search Needle"},
                    ),
                    line(
                        "assistant",
                        timestamp=(recent + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
                        message={"role": "assistant", "content": [{"type": "text", "text": "r"}]},
                    ),
                ]
            )
            + "\n"
        )
        (self.proj / "old.jsonl").write_text(
            "\n".join(
                [
                    line(
                        "user",
                        promptId="old-prompt",
                        timestamp=old.isoformat().replace("+00:00", "Z"),
                        cwd="/w",
                        message={"role": "user", "content": "Search Needle"},
                    ),
                    line(
                        "assistant",
                        timestamp=(old + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
                        message={"role": "assistant", "content": [{"type": "text", "text": "r"}]},
                    ),
                ]
            )
            + "\n"
        )
        status, data = self.call("GET", "/api/prompts/search?q=needle")
        self.assertEqual(status, 200)
        self.assertEqual([prompt["prompt_id"] for prompt in data["prompts"]], ["recent-prompt"])

    def test_prompt_search_accepts_recent_naive_timestamps(self):
        recent_naive = (self.now - timedelta(days=1)).replace(tzinfo=None)
        (self.proj / "recent-naive.jsonl").write_text(
            "\n".join(
                [
                    line(
                        "user",
                        promptId="recent-naive",
                        timestamp=recent_naive.isoformat(),
                        cwd="/w",
                        message={"role": "user", "content": "Needle"},
                    ),
                    line(
                        "assistant",
                        timestamp=(recent_naive + timedelta(seconds=30)).isoformat(),
                        message={"role": "assistant", "content": [{"type": "text", "text": "r"}]},
                    ),
                ]
            )
            + "\n"
        )

        status, data = self.call("GET", "/api/prompts/search?q=needle")
        self.assertEqual(status, 200)
        self.assertEqual([prompt["prompt_id"] for prompt in data["prompts"]], ["recent-naive"])

    def test_prompt_search_includes_session_context(self):
        recent = self.now - timedelta(days=1)
        (self.proj / "context.jsonl").write_text(
            "\n".join(
                [
                    line(
                        "user",
                        promptId="intro",
                        timestamp=recent.isoformat().replace("+00:00", "Z"),
                        cwd="/w",
                        message={"role": "user", "content": "Session title prompt"},
                    ),
                    line(
                        "assistant",
                        timestamp=(recent + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
                        message={"role": "assistant", "content": [{"type": "text", "text": "r"}]},
                    ),
                    line(
                        "user",
                        promptId="match",
                        timestamp=(recent + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                        cwd="/w",
                        message={"role": "user", "content": "Needle prompt body"},
                    ),
                    line(
                        "assistant",
                        timestamp=(recent + timedelta(minutes=1, seconds=30)).isoformat().replace("+00:00", "Z"),
                        message={"role": "assistant", "content": [{"type": "text", "text": "r"}]},
                    ),
                ]
            )
            + "\n"
        )

        status, data = self.call("GET", "/api/prompts/search?q=needle")
        self.assertEqual(status, 200)
        self.assertEqual(
            data["prompts"],
            [
                {
                    "prompt_id": "match",
                    "session_id": "context",
                    "position": 1,
                    "timestamp": (recent + timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
                    "project_path": "/w",
                    "session_title": "Session title prompt",
                    "text": "Needle prompt body",
                    "is_truncated": False,
                }
            ],
        )

    def test_prompt_search_ignores_presentation_markup(self):
        recent = self.now - timedelta(days=1)
        (self.proj / "markup.jsonl").write_text(
            "\n".join(
                [
                    line(
                        "user",
                        promptId="markup-prompt",
                        timestamp=recent.isoformat().replace("+00:00", "Z"),
                        cwd="/w",
                        message={
                            "role": "user",
                            "content": "<strong>&lt;command-name&gt;/clear&lt;/command-name&gt;</strong>",
                        },
                    ),
                    line(
                        "assistant",
                        timestamp=(recent + timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
                        message={"role": "assistant", "content": [{"type": "text", "text": "r"}]},
                    ),
                ]
            )
            + "\n"
        )
        status, hidden_match = self.call("GET", "/api/prompts/search?q=strong")
        self.assertEqual(status, 200)
        self.assertEqual(hidden_match["prompts"], [])

        status, visible_match = self.call("GET", "/api/prompts/search?q=clear")
        self.assertEqual(status, 200)
        self.assertEqual([prompt["prompt_id"] for prompt in visible_match["prompts"]], ["markup-prompt"])

    def test_invalid_rating_value_rejected(self):
        self.assertEqual(self.call("PUT", "/api/ratings/a", {"value": 0, "session_id": "s", "position": 0})[0], 400)
        self.assertEqual(self.call("PUT", "/api/ratings/a", {"value": "5", "session_id": "s", "position": 0})[0], 400)

    def test_truncation(self):
        self.add_session("s1", [("a", "word " * 600, "r")])
        prompt = self.call("GET", "/api/sessions/s1")[1]["prompts"][0]
        self.assertTrue(prompt["is_truncated"])
        self.assertLess(len(prompt["text"]), 2001)
        full = self.call("GET", "/api/sessions/s1/prompts/a")[1]
        self.assertEqual(len(full["text"]), 3000)

    def test_malformed_session_does_not_break_list(self):
        self.add_session("good", [("a", "ok", "r")])
        (self.proj / "bad.jsonl").write_bytes(b"\xff\xfe{{{ not json\n{\"type\": \"user\"\n")
        status, data = self.call("GET", "/api/sessions")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["sessions"]), 1)
        self.assertEqual(self.call("GET", "/api/sessions/bad")[0], 200)

    def test_orphaned_rating_is_flagged_not_dropped(self):
        self.add_session("s1", [("a", "hi", "r")])
        self.call("PUT", "/api/ratings/a", {"value": 7, "session_id": "s1", "position": 0})
        (self.proj / "s1.jsonl").unlink()
        prompts = self.call("GET", "/api/top-rated")[1]["prompts"]
        self.assertEqual(len(prompts), 1)
        self.assertTrue(prompts[0]["is_orphaned"])
        self.assertNotIn("text", prompts[0])

    def test_corrupted_ratings_recovery(self):
        self.add_session("s1", [("a", "hi", "r")])
        self.store_path.parent.mkdir(parents=True)
        self.store_path.write_text("not json")
        status, data = self.call("GET", "/api/top-rated")
        self.assertEqual((status, data.get("ratings_invalid")), (409, True))
        detail = self.call("GET", "/api/sessions/s1")[1]
        self.assertTrue(detail["ratings_invalid"])
        self.assertEqual(self.call("POST", "/api/ratings/reset")[1], {"reset": True})
        self.assertEqual(self.call("GET", "/api/top-rated")[0], 200)
        self.assertEqual(self.call("PUT", "/api/ratings/a", {"value": 4, "session_id": "s1", "position": 0})[0], 200)

    def test_create_and_edit_favorite_prompts(self):
        status, created = self.call("POST", "/api/favorites", {"text": "First favorite"})
        self.assertEqual(status, 201)
        self.assertEqual(created["text"], "First favorite")

        status, listing = self.call("GET", "/api/favorites")
        self.assertEqual(status, 200)
        self.assertEqual(
            listing["prompts"],
            [
                {
                    "favorite_prompt_id": created["favorite_prompt_id"],
                    "text": "First favorite",
                    "created_at": created["created_at"],
                    "updated_at": created["updated_at"],
                }
            ],
        )

        status, updated = self.call(
            "PUT",
            f"/api/favorites/{created['favorite_prompt_id']}",
            {"text": "Updated favorite"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["text"], "Updated favorite")
        self.assertEqual(updated["created_at"], created["created_at"])
        self.assertGreater(updated["updated_at"], created["updated_at"])
        self.assertEqual(self.call("GET", "/api/favorites")[1]["prompts"][0]["text"], "Updated favorite")

    def test_invalid_favorite_payload_rejected(self):
        self.assertEqual(self.call("POST", "/api/favorites", {"text": ""})[0], 400)
        self.assertEqual(self.call("POST", "/api/favorites", {"text": "   "})[0], 400)
        self.assertEqual(self.call("PUT", "/api/favorites/nope", {"text": "ok"})[0], 404)

    def test_corrupted_favorites_recovery(self):
        self.favorites_path.parent.mkdir(parents=True)
        self.favorites_path.write_text("not json")
        status, data = self.call("GET", "/api/favorites")
        self.assertEqual((status, data.get("favorites_invalid")), (409, True))
        self.assertEqual(self.call("POST", "/api/favorites/reset")[1], {"reset": True})
        self.assertEqual(self.call("GET", "/api/favorites")[1], {"prompts": []})
        self.assertEqual(self.call("POST", "/api/favorites", {"text": "Recovered"})[0], 201)

    def test_errors_leak_no_paths_or_tracebacks(self):
        self.add_session("s1", [("a", "hi", "r")])
        for method, path in [("GET", "/api/sessions/nope"), ("GET", "/api/sessions/s1/prompts/zzz"),
                             ("GET", "/api/nothing"), ("DELETE", "/api/sessions"), ("PUT", "/api/ratings/a")]:
            status, data = self.call(method, path)
            self.assertGreaterEqual(status, 400, path)
            self.assertEqual(list(data), ["error"], path)
            for leak in ("Traceback", str(self.root), "/home/"):
                self.assertNotIn(leak, data["error"])


if __name__ == "__main__":
    unittest.main()
