#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("laoma_memory.py")
SPEC = importlib.util.spec_from_file_location("laoma_memory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class LaomaMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "memory"
        self.root.mkdir()
        for name in MODULE.CORE_FILES:
            (self.root / name).write_text(f"# {name}\n測試記憶\n", encoding="utf-8")
        (self.root / "projects" / "demo").mkdir(parents=True)
        (self.root / "projects" / "demo" / "PROJECT_CONTEXT.md").write_text("# demo\n已確認內容\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_explicit_repository_resolution(self):
        self.assertEqual(MODULE.resolve_repo(str(self.root)), self.root.resolve())

    def test_matching_project_from_unrelated_depth(self):
        cwd = self.root.parent / "work" / "demo" / "src"
        cwd.mkdir(parents=True)
        self.assertEqual(MODULE.matching_project(self.root, cwd).name, "demo")

    def test_safe_pull_skips_dirty_repository(self):
        (self.root / "dirty.md").write_text("dirty", encoding="utf-8")
        self.assertEqual(MODULE.safe_pull(self.root), "skipped-dirty")

    def test_candidate_summaries_do_not_expose_content(self):
        folder = self.root / ".memory-growth" / "candidates"
        folder.mkdir(parents=True)
        (folder / "one.json").write_text(
            json.dumps({"id": "one", "title": "候選", "category": "fact", "confidence": "OBSERVED", "content": "不應輸出"}, ensure_ascii=False),
            encoding="utf-8",
        )
        summaries = MODULE.candidate_summaries(self.root)
        self.assertEqual(summaries[0]["id"], "one")
        self.assertNotIn("content", summaries[0])

    def test_unicode_escaped_wing_name_is_decoded(self):
        (self.root / "mempalace.yaml").write_text(
            'wing: "\\u8001\\u99AC\\u7684\\u5B8C\\u5168ai\\u8A18\\u61B6"\n',
            encoding="utf-8",
        )
        self.assertEqual(MODULE.wing_name(self.root), "老馬的完全ai記憶")


if __name__ == "__main__":
    unittest.main()
