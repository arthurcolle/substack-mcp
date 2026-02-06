import unittest

from substack_client import SubstackClient


class TestDraftBodyParsing(unittest.TestCase):
    def test_parse_draft_body_dict(self):
        parsed = SubstackClient._parse_draft_body({"content": "not-a-list"})
        self.assertEqual(parsed["type"], "doc")
        self.assertEqual(parsed["content"], [])

    def test_parse_draft_body_json_string(self):
        parsed = SubstackClient._parse_draft_body('{"type": "doc", "content": []}')
        self.assertEqual(parsed["type"], "doc")
        self.assertEqual(parsed["content"], [])

    def test_parse_draft_body_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            SubstackClient._parse_draft_body("{not-json}")


if __name__ == "__main__":
    unittest.main()
