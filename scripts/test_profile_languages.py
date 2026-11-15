import unittest
from collections import Counter
from unittest.mock import patch
import profile_languages as p


class TestLanguageChart(unittest.TestCase):
    def test_collect_ignores_forks_and_sums_bytes(self):
        repos = [
            {"owner":{"login":"imsayon"},"fork":False,"private":False,
             "languages_url":"https://api.github.com/repos/imsayon/a/languages"},
            {"owner":{"login":"imsayon"},"fork":True,"private":False,
             "languages_url":"https://api.github.com/repos/imsayon/b/languages"},
            {"owner":{"login":"imsayon"},"fork":False,"private":False,
             "languages_url":"https://api.github.com/repos/imsayon/c/languages"},
        ]
        with patch.object(p, "fetch_json", side_effect=[repos,{"C++":120,"TypeScript":30},{"C++":30,"SQL":40}]):
            totals, count = p.collect("token")
        self.assertEqual(count, 2)
        self.assertEqual(totals, Counter({"C++":150,"SQL":40,"TypeScript":30}))

    def test_invalid_sizes_are_rejected(self):
        repos = [{"owner":{"login":"imsayon"},"fork":False,"private":False,
                  "languages_url":"https://api.github.com/repos/imsayon/a/languages"}]
        with patch.object(p, "fetch_json", side_effect=[repos,{"C++":"100"}]):
            with self.assertRaisesRegex(RuntimeError, "Invalid"):
                p.collect("token")

    def test_render_labels_and_percentages(self):
        svg = p.render(Counter({"C++":750,"TypeScript":250}), 2, "15 Nov 2026 UTC")
        self.assertIn("LANGUAGES / BY FILE SIZE",svg)
        self.assertIn("75.0%",svg)
        self.assertIn("25.0%",svg)
        self.assertIn("2 PUBLIC REPOS",svg)
        self.assertIn("GitHub Linguist",svg)

    def test_invalid_data_rejected(self):
        with self.assertRaises(ValueError):
            p.render(Counter({"C++":0}),1,"x")
        with self.assertRaises(ValueError):
            p.render(Counter({"C++":-1}),1,"x")


if __name__ == "__main__":
    unittest.main()
