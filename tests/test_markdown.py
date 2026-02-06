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


if __name__ == "__main__":
    unittest.main()
