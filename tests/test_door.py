import json, unittest
from kingdom.host import door


class _Recorder:
    """Fake runner: records commands, returns scripted stdout per command-prefix."""
    def __init__(self, replies=None):
        self.calls = []
        self.replies = replies or {}
    def __call__(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        for prefix, out in self.replies.items():
            if " ".join(cmd).startswith(prefix):
                return out
        return ""


class TestState(unittest.TestCase):
    def test_load_missing_returns_empty(self):
        from pathlib import Path
        self.assertEqual(door.load_state(Path("/nonexistent/door.state.json")), {})

    def test_save_load_roundtrip(self):
        import tempfile, pathlib
        p = pathlib.Path(tempfile.mkdtemp()) / "door.state.json"
        door.save_state({"7": {"name": "river"}}, p)
        self.assertEqual(door.load_state(p), {"7": {"name": "river"}})


class TestListIssues(unittest.TestCase):
    def test_parses_gh_json(self):
        rec = _Recorder({"gh issue list": json.dumps([
            {"number": 7, "title": "citizen: river", "body": "### Your name, handle, or anon\n\nriver"}
        ])})
        issues = door.list_open_citizen_issues(runner=rec)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["number"], 7)
        self.assertEqual(rec.calls[0][:3], ["gh", "issue", "list"])

    def test_bad_json_returns_empty(self):
        rec = _Recorder({"gh issue list": "not json"})
        self.assertEqual(door.list_open_citizen_issues(runner=rec), [])


class TestReDraftGuard(unittest.TestCase):
    def test_state_blocks_redraft(self):
        self.assertTrue(door.already_drafted(7, {"7": {}}))
        self.assertFalse(door.already_drafted(8, {"7": {}}))

    def test_remote_branch_exists_true(self):
        rec = _Recorder({"git ls-remote": "abc123\trefs/heads/citizen/07-river"})
        self.assertTrue(door.remote_branch_exists("citizen/07-river", runner=rec))

    def test_remote_branch_exists_false(self):
        rec = _Recorder({"git ls-remote": ""})
        self.assertFalse(door.remote_branch_exists("citizen/07-river", runner=rec))


if __name__ == "__main__":
    unittest.main()