"""ansorder —— 自检测试。

把评测答案的顺序偏置切成可核查的片段并标出关键位置

覆盖：正常路径、边界输入、防呆红线、幂等性。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ansorder  # noqa: E402

SAMPLE_TEXT = '你是助手。请分析数据。不要猜测。输出 JSON。'


class TestAnsorder(unittest.TestCase):
    """评测答案的顺序偏置"""

    def test_cli_help_exits_zero(self):
        """--help 必须能正常退出。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "ansorder.py"), "--help"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)

    def test_cli_rejects_empty_input(self):
        """空输入必须明确报错，不能静默成功。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "ansorder.py"), "--text", "   "],
            capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(proc.returncode, 0)

    def test_cli_json_output_parses(self):
        """--json 输出必须是合法 JSON。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "ansorder.py"), "--text", SAMPLE_TEXT,
             "--json"],
            capture_output=True, text=True, encoding="utf-8")
        if proc.returncode not in (0, 1):
            self.fail(f"退出码异常：{proc.returncode} {proc.stderr[:300]}")
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)

    def test_does_not_mutate_input(self):
        """防呆：分析过程不得改动调用方传入的对象。"""
        payload = SAMPLE_TEXT
        before = payload
        ansorder.ansorder_analyze(payload)
        self.assertEqual(before, payload)

    def test_is_idempotent(self):
        """同一输入跑两次结果必须一致。"""
        a = ansorder.ansorder_analyze(SAMPLE_TEXT)
        b = ansorder.ansorder_analyze(SAMPLE_TEXT)
        self.assertEqual(json.dumps(a, ensure_ascii=False, sort_keys=True),
                         json.dumps(b, ensure_ascii=False, sort_keys=True))

    def test_reports_unit_count(self):
        r = ansorder.ansorder_analyze(SAMPLE_TEXT)
        self.assertGreater(r["unit_count"], 0)

    def test_findings_carry_position(self):
        """每条命中都要能定位到具体单元——这是工具的承诺。"""
        r = ansorder.ansorder_analyze("缺失的要素。冲突的要素。")
        for f in r["findings"]:
            self.assertIn("unit_index", f)
            self.assertIn("rule", f)
            self.assertIn("text", f)
