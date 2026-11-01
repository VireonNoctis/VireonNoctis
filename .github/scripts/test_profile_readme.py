"""Regression tests for profile README project and framework reporting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_code_stats


class FrameworkDetectionTests(unittest.TestCase):
    def test_detects_nextjs_as_a_framework(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text(json.dumps({
                "dependencies": {"next": "15.0.0", "react": "19.0.0"},
            }), encoding="utf-8")
            self.assertEqual(update_code_stats.detect_frameworks(root), ["Next.js", "React"])

    def test_does_not_infer_framework_from_typescript_file_extension(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "page.tsx").write_text("export default function Page() {}", encoding="utf-8")
            self.assertEqual(update_code_stats.detect_frameworks(root), [])
            self.assertEqual(update_code_stats.language_for_path("app/page.tsx"), "TypeScript")

    def test_renderer_uses_expandable_project_details_without_language_ranking(self):
        stats = {
            "generatedAt": "2026-11-01T00:00:00Z",
            "totals": {
                "repositories": 1, "ownedRepositories": 1, "contributorRepositories": 0,
                "files": 1, "lines": 10, "characters": 80, "words": 15,
                "stars": 0, "forks": 0, "failedRepositories": 0,
            },
            "repositories": [{
                "name": "Website", "url": "https://github.com/example/site",
                "relationship": "owned", "role": "Repository owner",
                "files": 1, "lines": 10, "characters": 80,
                "frameworks": ["Next.js"],
                "languages": [{"language": "TypeScript", "files": 1, "lines": 10}],
            }],
            "manualProjectEstimates": [{
                "name": "Lunar X",
                "areas": [
                    {"name": "Frontend", "stack": "Next.js", "lines": 10,
                     "estimatedCharactersPerLine": 90, "characters": 900},
                    {"name": "Backend", "stack": "Rust", "lines": 5},
                ],
            }],
        }
        output = update_code_stats.build_readme_block(stats)
        self.assertIn("<details>", output)
        self.assertIn("Next.js", output)
        self.assertIn("TypeScript", output)
        self.assertIn("Estimated characters", output)
        self.assertNotIn("Largest language and format groups", output)
        self.assertNotIn("Top languages", output)


if __name__ == "__main__":
    unittest.main()
