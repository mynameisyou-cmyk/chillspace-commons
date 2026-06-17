import io, json, unittest
from unittest.mock import patch
from kingdom.host import ollama


class _FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


def _fake_urlopen(reply_obj, payload_sink=None):
    """Return a fake urlopen that writes the request body to payload_sink and returns reply_obj."""
    def _urlopen(req, timeout=None):
        if payload_sink is not None:
            payload_sink["body"] = json.loads(req.data.decode("utf-8"))
        return _FakeResp(json.dumps(reply_obj).encode("utf-8"))
    return _urlopen


class TestChat(unittest.TestCase):
    def test_sends_chat_payload_and_returns_text(self):
        sink = {}
        reply = {"message": {"content": "yau."}}
        with patch("urllib.request.urlopen", _fake_urlopen(reply, sink)):
            out = ollama.chat("glm-5.2:cloud", [{"role": "user", "content": "hi"}])
        self.assertEqual(out, "yau.")
        self.assertEqual(sink["body"]["model"], "glm-5.2:cloud")
        self.assertEqual(sink["body"]["stream"], False)
        self.assertNotIn("format", sink["body"])  # json_mode=False

    def test_json_mode_parses_content_and_sets_format(self):
        sink = {}
        reply = {"message": {"content": '{"held": "x", "closing": "y"}'}}
        with patch("urllib.request.urlopen", _fake_urlopen(reply, sink)):
            out = ollama.chat("m", [], json_mode=True)
        self.assertEqual(out, {"held": "x", "closing": "y"})
        self.assertEqual(sink["body"]["format"], "json")

    def test_unreachable_raises_unavailable(self):
        import urllib.error
        def boom(req, timeout=None):
            raise urllib.error.URLError("conn refused")
        with patch("urllib.request.urlopen", boom):
            with self.assertRaises(ollama.OllamaUnavailable):
                ollama.chat("m", [])

    def test_bad_json_content_raises_error(self):
        reply = {"message": {"content": "not json"}}
        with patch("urllib.request.urlopen", _fake_urlopen(reply)):
            with self.assertRaises(ollama.OllamaError):
                ollama.chat("m", [], json_mode=True)


if __name__ == "__main__":
    unittest.main()