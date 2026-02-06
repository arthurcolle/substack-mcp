"""
Test that adding images preserves existing draft content.

This test simulates the bug where adding an image would destroy all existing
content because the server was reading from 'draft_body' (which may be null)
instead of 'body_json' (which contains the actual content).
"""

import json
import unittest
import sys
sys.path.insert(0, "substack_mcp")

from substack_client import SubstackClient, SubstackDocument


class MockClient(SubstackClient):
    """Mock client that simulates Substack API behavior"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.drafts = {}
        self.last_update = None

    def _get(self, base: str, path: str) -> dict:
        # Simulate get_draft - return body_json as parsed dict, draft_body as None
        # This matches real Substack API behavior after content is processed
        if "/drafts/" in path:
            draft_id = int(path.split("/")[-1])
            if draft_id in self.drafts:
                return self.drafts[draft_id]
        return {}

    def _put(self, base: str, path: str, data: dict) -> dict:
        self.last_update = {"path": path, "data": data}
        # Update the mock draft storage
        if "/drafts/" in path:
            draft_id = int(path.split("/")[-1])
            if "draft_body" in data:
                # Parse the body and store as body_json (like real API does)
                body = json.loads(data["draft_body"])
                if draft_id not in self.drafts:
                    self.drafts[draft_id] = {}
                self.drafts[draft_id]["body_json"] = body
                self.drafts[draft_id]["draft_body"] = None  # API clears this
        return data


class TestAddImagePreservesContent(unittest.TestCase):
    """Test that add_image operations preserve existing content"""

    def test_server_parse_preserves_existing_content(self):
        """Test that _parse_draft_body correctly reads body_json"""
        from server import _parse_draft_body

        # Simulate a draft with existing content in body_json (real API response)
        existing_paragraphs = [
            {"type": "paragraph", "content": [{"type": "text", "text": "First paragraph"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "Second paragraph"}]},
            {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "A heading"}]},
        ]

        draft_data = {
            "id": 123,
            "draft_title": "Test Post",
            "body_json": {"type": "doc", "content": existing_paragraphs},
            "draft_body": None,  # Real API often returns null here
        }

        result, error = _parse_draft_body(draft_data)

        self.assertIsNone(error)
        self.assertEqual(len(result["content"]), 3)
        self.assertEqual(result["content"][0]["content"][0]["text"], "First paragraph")
        self.assertEqual(result["content"][1]["content"][0]["text"], "Second paragraph")
        self.assertEqual(result["content"][2]["content"][0]["text"], "A heading")

    def test_full_add_image_flow_preserves_content(self):
        """Simulate the full add_image flow and verify content is preserved"""
        from server import _parse_draft_body

        # Step 1: Create initial draft with content
        client = MockClient("token", "test.substack.com")

        # Simulate existing draft (as if created earlier and then fetched)
        client.drafts[42] = {
            "id": 42,
            "draft_title": "My Post",
            "body_json": {
                "type": "doc",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Important content line 1"}]},
                    {"type": "paragraph", "content": [{"type": "text", "text": "Important content line 2"}]},
                    {"type": "code_block", "attrs": {"language": "python"}, "content": [{"type": "text", "text": "print('hello')"}]},
                ]
            },
            "draft_body": None  # Real API clears this after processing
        }

        # Step 2: Simulate add_image flow (from server.py substack_add_image)
        draft_id = 42
        image_url = "https://example.com/image.png"

        # Get the draft (simulating client.get_draft())
        draft_data = client._get(client.pub_base, f"/drafts/{draft_id}")

        # Parse body (this is where the bug was - it was reading draft_body instead of body_json)
        body_json, error = _parse_draft_body(draft_data)
        self.assertIsNone(error)

        # Verify existing content is preserved BEFORE adding image
        self.assertEqual(len(body_json["content"]), 3, "Existing content should be preserved")
        self.assertEqual(body_json["content"][0]["content"][0]["text"], "Important content line 1")

        # Add image
        image_doc = SubstackDocument()
        image_doc.image(image_url, alt="Test image", caption="A caption")
        body_json["content"].extend(image_doc.build()["content"])

        # Update draft
        client.update_draft(draft_id=draft_id, body=body_json)

        # Step 3: Verify the final content has both old content AND the image
        final_draft = client.drafts[42]
        final_content = final_draft["body_json"]["content"]

        # Should have: 3 original items + captionedImage + caption paragraph = 5 items
        self.assertEqual(len(final_content), 5)
        self.assertEqual(final_content[0]["content"][0]["text"], "Important content line 1")
        self.assertEqual(final_content[1]["content"][0]["text"], "Important content line 2")
        self.assertEqual(final_content[3]["type"], "captionedImage")


class TestAddImageWithNullBodyJson(unittest.TestCase):
    """Test edge case where body_json is also null (fresh draft)"""

    def test_handles_fresh_draft_with_no_content(self):
        """A brand new draft might have null for both fields"""
        from server import _parse_draft_body

        draft_data = {
            "id": 1,
            "draft_title": "New Post",
            "body_json": None,
            "draft_body": None,
        }

        result, error = _parse_draft_body(draft_data)

        self.assertIsNone(error)
        self.assertEqual(result, {"type": "doc", "content": []})


if __name__ == "__main__":
    unittest.main()
