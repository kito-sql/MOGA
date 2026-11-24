# -*- coding: utf-8 -*-
"""Tests for simple-terminal-version/terminal.py."""

import csv
import io
import os
import sys
import unittest
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import terminal as term


class TestSimpleTerminal(unittest.TestCase):
    def test_interactive_defaults_run(self):
        # Answer: default dataset 'y', pop=60, gens=250, mut=0.08, seed=42
        answers = iter(["y", "60", "250", "0.08", "42"])
        buf = io.StringIO()
        with patch("builtins.input", lambda _prompt="": next(answers)), patch("sys.stdout", buf):
            term.run_interactive(use_defaults=False)

        output = buf.getvalue()
        self.assertIn("ULTIMATE SOLUTION | f1(conflicts)=0", output)

        csv_path = os.path.join(HERE, "emploi_du_temps_simple.csv")
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), 24)  # header + 23 sessions


if __name__ == "__main__":
    unittest.main(verbosity=2)
