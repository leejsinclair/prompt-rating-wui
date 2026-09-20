import json
import tempfile
import unittest
from pathlib import Path

from src.parsing import parse_session_file
from src.server.common import humanize_command_markup


def user(text, prompt_id="p1", ts="2026-01-01T00:00:00Z", **extra):
    line = {"type": "user", "promptId": prompt_id, "timestamp": ts, "cwd": "/work/proj",
            "message": {"role": "user", "content": text}}
    line.update(extra)
    return line


def assistant(blocks, ts="2026-01-01T00:00:01Z", **extra):
    line = {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": blocks}}
    line.update(extra)
    return line


class ParserTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def parse(self, lines, name="sess-1.jsonl"):
        path = self.dir / name
        path.write_text("\n".join(l if isinstance(l, str) else json.dumps(l) for l in lines) + "\n")
        return parse_session_file(path)

    def test_extracts_prompt_fields(self):
        s = self.parse([user("hello", prompt_id="abc", ts="2026-01-01T10:00:00Z"),
                        assistant([{"type": "text", "text": "hi there"}])])
        self.assertEqual(s.session_id, "sess-1")
        self.assertEqual(s.project_path, "/work/proj")
        self.assertEqual(len(s.prompts), 1)
        p = s.prompts[0]
        self.assertEqual((p.prompt_id, p.position, p.text, p.timestamp), ("abc", 0, "hello", "2026-01-01T10:00:00Z"))
        self.assertEqual(p.response_text, "hi there")
        self.assertEqual(s.started_at, "2026-01-01T10:00:00Z")
        self.assertEqual(s.last_activity_at, "2026-01-01T00:00:01Z")

    def test_list_content_user_lines_are_not_prompts(self):
        s = self.parse([user("real"),
                        {"type": "user", "timestamp": "t", "message": {"role": "user", "content": [
                            {"type": "tool_result", "content": "output"}]}}])
        self.assertEqual([p.text for p in s.prompts], ["real"])

    def test_meta_and_sidechain_excluded(self):
        s = self.parse([user("meta", prompt_id="m", isMeta=True),
                        user("side", prompt_id="s", isSidechain=True),
                        user("kept", prompt_id="k")])
        self.assertEqual([p.text for p in s.prompts], ["kept"])

    def test_response_text_concatenates_text_blocks_across_assistant_lines(self):
        s = self.parse([user("q"),
                        assistant([{"type": "text", "text": "first"}, {"type": "tool_use", "name": "Bash"}]),
                        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result"}]}},
                        assistant([{"type": "text", "text": "second"}])])
        self.assertEqual(s.prompts[0].response_text, "first\n\nsecond")

    def test_sidechain_assistant_text_ignored(self):
        s = self.parse([user("q"), assistant([{"type": "text", "text": "sub-agent"}], isSidechain=True)])
        self.assertEqual(s.prompts[0].response_text, "")

    def test_responses_attach_to_their_own_prompt(self):
        s = self.parse([user("one", "p1"), assistant([{"type": "text", "text": "A1"}]),
                        user("two", "p2"), assistant([{"type": "text", "text": "A2"}])])
        self.assertEqual([(p.position, p.response_text) for p in s.prompts], [(0, "A1"), (1, "A2")])

    def test_activity_summary_rules(self):
        cases = [
            ([{"type": "tool_use"}], "used 1 tool"),
            ([{"type": "tool_use"}, {"type": "tool_use"}], "used 2 tools"),
            ([{"type": "tool_use"}, {"type": "thinking", "thinking": "x"}], "used 1 tool, with reasoning"),
            ([{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "hi"}], "internal reasoning"),
            ([{"type": "text", "text": "plain"}], None),
        ]
        for blocks, expected in cases:
            with self.subTest(expected=expected):
                s = self.parse([user("q"), assistant(blocks)])
                self.assertEqual(s.prompts[0].activity_summary, expected)

    def test_malformed_and_unrecognized_lines_are_skipped_per_line(self):
        s = self.parse(["{not json", "[1,2]", {"type": "brand-new-type", "x": 1}, user("ok")])
        self.assertTrue(s.is_parseable)
        self.assertEqual([p.text for p in s.prompts], ["ok"])
        self.assertTrue(any("malformed" in w for w in s.parse_warnings))

    def test_missing_prompt_id_falls_back_to_session_and_position(self):
        line = user("q")
        del line["promptId"]
        s = self.parse([line])
        self.assertEqual(s.prompts[0].prompt_id, "sess-1:0")

    def test_duplicate_prompt_id_gets_unique_fallback(self):
        s = self.parse([user("a", "same"), user("b", "same")])
        ids = [p.prompt_id for p in s.prompts]
        self.assertEqual(len(set(ids)), 2)

    def test_duration_is_prompt_to_last_assistant_activity(self):
        s = self.parse([user("q", ts="2026-01-01T00:00:00Z"),
                        assistant([{"type": "tool_use"}], ts="2026-01-01T00:01:00Z"),
                        {"type": "user", "timestamp": "2026-01-01T00:03:00Z",
                         "message": {"role": "user", "content": [{"type": "tool_result"}]}},
                        assistant([{"type": "text", "text": "done"}], ts="2026-01-01T00:02:30.500Z")])
        self.assertEqual(s.prompts[0].duration_seconds, 150)

    def test_duration_none_without_assistant_activity_or_timestamps(self):
        s = self.parse([user("q")])
        self.assertIsNone(s.prompts[0].duration_seconds)

    def test_unreadable_file_is_not_parseable(self):
        s = parse_session_file(self.dir / "does-not-exist.jsonl")
        self.assertFalse(s.is_parseable)
        self.assertEqual(s.prompts, [])
        self.assertTrue(s.error)
        self.assertNotIn(str(self.dir), s.error)

    def test_session_with_no_prompts(self):
        s = self.parse([{"type": "mode", "mode": "normal"}])
        self.assertTrue(s.is_parseable)
        self.assertEqual(s.prompt_count, 0)

    def test_humanizes_command_markup(self):
        text = "<strong>&lt;command-name&gt;/clear&lt;/command-name&gt; &lt;command-message&gt;clear&lt;/command-message&gt; &lt;command-args&gt;&lt;/command-args&gt;</strong>"
        self.assertEqual(humanize_command_markup(text), "<strong>/clear</strong>")


if __name__ == "__main__":
    unittest.main()
