#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().with_name("memory_growth.py")


class MemoryGrowthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "projects" / "demo").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.env = os.environ.copy()
        self.env["MEMORY_REPO_ROOT"] = str(self.root)
        self.env["PYTHONIOENCODING"] = "utf-8"

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_capture_approve_and_deduplicate(self):
        result = self.run_tool(
            "capture", "--title", "可重用經驗", "--category", "pattern",
            "--content", "先檢查來源，再更新索引。",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        candidate = next((self.root / ".memory-growth" / "candidates").glob("*.json"))
        memory_id = json.loads(candidate.read_text(encoding="utf-8"))["id"]
        approved = self.run_tool("approve", memory_id)
        self.assertEqual(approved.returncode, 0, approved.stderr)
        self.assertEqual(len(list((self.root / "knowledge" / "pattern").glob("*.md"))), 1)
        duplicate = self.run_tool(
            "capture", "--title", "重複", "--category", "pattern",
            "--content", "先檢查來源，再更新索引。",
        )
        self.assertEqual(duplicate.returncode, 0)
        self.assertIn("duplicate", duplicate.stderr)

    def test_sensitive_value_is_blocked(self):
        result = self.run_tool(
            "capture", "--title", "不安全", "--content", "api_key=" + "sk-" + "example12345678901234567890",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("blocked-sensitive", result.stderr)

    def test_memory_id_is_not_mistaken_for_payment_card(self):
        memory_id = 'id: "' + "20260801" + "-" + "214021" + "-合法記憶-1234abcd\""
        result = self.run_tool(
            "capture", "--title", "合法 ID", "--content",
            memory_id,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_payment_card_like_value_is_blocked(self):
        value = "4111 " * 3 + "4111"
        result = self.run_tool(
            "capture", "--title", "不安全卡號", "--content", "card=" + value,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("credit-card-like", result.stderr)

    def test_harvest_creates_candidate_once(self):
        worklog = self.root / "projects" / "demo" / "AI_WORKLOG.md"
        worklog.write_text(
            "# AI WORKLOG\n\n## 2026-08-01\n- GOAL：建立安全記憶。\n- COMPLETED：完成測試。\n",
            encoding="utf-8",
        )
        first = self.run_tool("harvest")
        second = self.run_tool("harvest")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertIn("新增 1", first.stdout)
        self.assertIn("新增 0", second.stdout)

    def test_harvest_ignores_template_worklog(self):
        template = self.root / "projects" / "_template"
        template.mkdir(parents=True)
        (template / "AI_WORKLOG.md").write_text(
            "# AI WORKLOG\n\n## YYYY-MM-DD\n- GOAL：範例。\n",
            encoding="utf-8",
        )
        result = self.run_tool("harvest")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("新增 0", result.stdout)


if __name__ == "__main__":
    unittest.main()
