import unittest

from substack_client import MarkdownToSubstack


class TestMarkdownToSubstack(unittest.TestCase):
    def test_inline_marks(self):
        doc = MarkdownToSubstack.convert(
            "Use `code` and **bold** and *ital* and [link](https://example.com)"
        )
        paragraph = doc["content"][0]
        self.assertEqual(paragraph["type"], "paragraph")
        nodes = paragraph["content"]

        def has_mark(text, mark_type, href=None):
            for node in nodes:
                if node.get("text") != text:
                    continue
                marks = node.get("marks", [])
                for mark in marks:
                    if mark.get("type") != mark_type:
                        continue
                    if href is None:
                        return True
                    if mark.get("attrs", {}).get("href") == href:
                        return True
            return False

        self.assertTrue(has_mark("code", "code"))
        self.assertTrue(has_mark("bold", "strong"))
        self.assertTrue(has_mark("ital", "em"))
        self.assertTrue(has_mark("link", "link", href="https://example.com"))

    def test_fenced_code_language_allows_symbols(self):
        doc = MarkdownToSubstack.convert("```c++\nint x = 0;\n```")
        node = doc["content"][0]
        self.assertEqual(node["type"], "codeBlock")
        self.assertEqual(node["attrs"]["language"], "c++")

    def test_numbered_list_structure(self):
        doc = MarkdownToSubstack.convert("1. First\n2. Second\n")
        node = doc["content"][0]
        self.assertEqual(node["type"], "orderedList")
        self.assertEqual(node["attrs"]["order"], 1)
        self.assertEqual(len(node["content"]), 2)

    def _list_item_text_nodes(self, list_node, item_idx=0):
        """Helper: pull the text-node array from a list's nth listItem paragraph."""
        item = list_node["content"][item_idx]
        self.assertEqual(item["type"], "listItem")
        paragraph = item["content"][0]
        self.assertEqual(paragraph["type"], "paragraph")
        return paragraph["content"]

    def test_bullet_list_inline_marks_parsed(self):
        """Bullet list items must run through inline parsing — bug: literal **text** rendered."""
        doc = MarkdownToSubstack.convert(
            "- **Bold item** and trailing text\n"
            "- Plain item\n"
            "- Item with *italic* and `code`\n"
        )
        node = doc["content"][0]
        self.assertEqual(node["type"], "bulletList")

        # Item 0: starts bold, then plain
        nodes0 = self._list_item_text_nodes(node, 0)
        # First node should be bold text, no asterisks
        self.assertEqual(nodes0[0]["text"], "Bold item")
        self.assertIn({"type": "strong"}, nodes0[0]["marks"])
        # Combined plain text in the item must not contain literal '**'
        flat = "".join(n.get("text", "") for n in nodes0)
        self.assertNotIn("**", flat)

        # Item 2: italic + code
        nodes2 = self._list_item_text_nodes(node, 2)
        flat2 = "".join(n.get("text", "") for n in nodes2)
        self.assertNotIn("*", flat2)
        self.assertNotIn("`", flat2)
        self.assertTrue(any(
            n.get("text") == "italic" and {"type": "em"} in n.get("marks", [])
            for n in nodes2
        ))
        self.assertTrue(any(
            n.get("text") == "code" and {"type": "code"} in n.get("marks", [])
            for n in nodes2
        ))

    def test_numbered_list_inline_marks_parsed(self):
        """Numbered list items must run through inline parsing too."""
        doc = MarkdownToSubstack.convert(
            "1. **First** with detail\n"
            "2. Second with [link](https://example.com)\n"
        )
        node = doc["content"][0]
        self.assertEqual(node["type"], "orderedList")

        nodes0 = self._list_item_text_nodes(node, 0)
        flat0 = "".join(n.get("text", "") for n in nodes0)
        self.assertNotIn("**", flat0)
        self.assertEqual(nodes0[0]["text"], "First")
        self.assertIn({"type": "strong"}, nodes0[0]["marks"])

        nodes1 = self._list_item_text_nodes(node, 1)
        # Find the link node
        link_node = next((n for n in nodes1 if n.get("text") == "link"), None)
        self.assertIsNotNone(link_node)
        marks = link_node.get("marks", [])
        self.assertTrue(any(
            m.get("type") == "link"
            and m.get("attrs", {}).get("href") == "https://example.com"
            for m in marks
        ))

    def test_heading_inline_marks_parsed(self):
        """Headings must run through inline parsing for **bold** etc."""
        doc = MarkdownToSubstack.convert("## A **bold** heading\n")
        node = doc["content"][0]
        self.assertEqual(node["type"], "heading")
        flat = "".join(n.get("text", "") for n in node["content"])
        self.assertNotIn("**", flat)
        self.assertTrue(any(
            n.get("text") == "bold"
            and {"type": "strong"} in n.get("marks", [])
            for n in node["content"]
        ))

    def test_blockquote_inline_marks_parsed(self):
        """Blockquotes must run through inline parsing."""
        doc = MarkdownToSubstack.convert("> A **strong** point with *flair*\n")
        node = doc["content"][0]
        self.assertEqual(node["type"], "blockquote")
        paragraph = node["content"][0]
        self.assertEqual(paragraph["type"], "paragraph")
        flat = "".join(n.get("text", "") for n in paragraph["content"])
        self.assertNotIn("**", flat)
        self.assertNotIn("*", flat)
        text_nodes = paragraph["content"]
        self.assertTrue(any(
            n.get("text") == "strong"
            and {"type": "strong"} in n.get("marks", [])
            for n in text_nodes
        ))
        self.assertTrue(any(
            n.get("text") == "flair"
            and {"type": "em"} in n.get("marks", [])
            for n in text_nodes
        ))


if __name__ == "__main__":
    unittest.main()
