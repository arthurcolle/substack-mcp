import json
import unittest
import urllib.parse

from substack_client import SubstackClient, SubstackDocument


class CaptureClient(SubstackClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_put = None

    def _put(self, base: str, path: str, data: dict) -> dict:
        self.last_put = {"base": base, "path": path, "data": data}
        return data


class TestImageHandling(unittest.TestCase):
    def test_document_image_caption_adds_paragraph(self):
        doc = SubstackDocument().image(
            "https://example.com/image.png",
            caption="Caption text",
            alt="Alt text"
        )
        built = doc.build()
        self.assertEqual(built["content"][0]["type"], "captionedImage")
        self.assertEqual(built["content"][1]["type"], "paragraph")
        marks = built["content"][1]["content"][0].get("marks", [])
        self.assertTrue(any(mark.get("type") == "em" for mark in marks))

    def test_fix_internal_redirects_sets_url(self):
        client = SubstackClient("token", "pub.example.com")
        body_json = {
            "type": "doc",
            "content": [{
                "type": "captionedImage",
                "content": [{
                    "type": "image2",
                    "attrs": {"src": "https://example.com/a b.png"}
                }]
            }]
        }
        client._fix_internal_redirects(body_json["content"], 123)
        attrs = body_json["content"][0]["content"][0]["attrs"]
        encoded = urllib.parse.quote("https://example.com/a b.png", safe="")
        expected = f"https://pub.example.com/i/123?img={encoded}"
        self.assertEqual(attrs.get("internalRedirect"), expected)

    def test_update_draft_applies_internal_redirects(self):
        client = CaptureClient("token", "pub.example.com")
        doc = SubstackDocument().image("https://example.com/with space.png")
        client.update_draft(42, body=doc)
        self.assertIsNotNone(client.last_put)
        draft_body = json.loads(client.last_put["data"]["draft_body"])
        image_attrs = draft_body["content"][0]["content"][0]["attrs"]
        encoded = urllib.parse.quote("https://example.com/with space.png", safe="")
        expected = f"https://pub.example.com/i/42?img={encoded}"
        self.assertEqual(image_attrs.get("internalRedirect"), expected)


class TestServerParseDraftBody(unittest.TestCase):
    """Test the server's _parse_draft_body function for API response handling"""

    def test_prefers_body_json_over_draft_body(self):
        """body_json should be preferred when both fields exist"""
        # Import the server's parser
        import sys
        sys.path.insert(0, "substack_mcp")
        from server import _parse_draft_body

        draft_data = {
            "body_json": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "From body_json"}]}]},
            "draft_body": '{"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "From draft_body"}]}]}'
        }
        result, error = _parse_draft_body(draft_data)
        self.assertIsNone(error)
        self.assertEqual(result["content"][0]["content"][0]["text"], "From body_json")

    def test_falls_back_to_draft_body_when_body_json_missing(self):
        """Should fall back to draft_body if body_json is missing/null"""
        import sys
        sys.path.insert(0, "substack_mcp")
        from server import _parse_draft_body

        draft_data = {
            "body_json": None,
            "draft_body": '{"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "From draft_body"}]}]}'
        }
        result, error = _parse_draft_body(draft_data)
        self.assertIsNone(error)
        self.assertEqual(result["content"][0]["content"][0]["text"], "From draft_body")

    def test_returns_empty_doc_when_both_missing(self):
        """Should return empty doc when both body_json and draft_body are missing"""
        import sys
        sys.path.insert(0, "substack_mcp")
        from server import _parse_draft_body

        draft_data = {}
        result, error = _parse_draft_body(draft_data)
        self.assertIsNone(error)
        self.assertEqual(result, {"type": "doc", "content": []})

    def test_handles_body_json_as_dict_directly(self):
        """body_json is typically already parsed as a dict by the API"""
        import sys
        sys.path.insert(0, "substack_mcp")
        from server import _parse_draft_body

        existing_content = [
            {"type": "paragraph", "content": [{"type": "text", "text": "Existing paragraph 1"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "Existing paragraph 2"}]}
        ]
        draft_data = {
            "body_json": {"type": "doc", "content": existing_content},
            "draft_body": None
        }
        result, error = _parse_draft_body(draft_data)
        self.assertIsNone(error)
        self.assertEqual(len(result["content"]), 2)
        self.assertEqual(result["content"][0]["content"][0]["text"], "Existing paragraph 1")


if __name__ == "__main__":
    unittest.main()
