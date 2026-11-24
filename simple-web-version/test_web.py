# -*- coding: utf-8 -*-
"""Integration tests for simple-web-version/app.py using Flask's test client."""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import app as web_app


class TestSimpleWeb(unittest.TestCase):
    def setUp(self):
        self.client = web_app.app.test_client()

    def test_index_renders_defaults(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Simple MOGA Timetabling", html)
        self.assertIn("Maths (CM)", html)

    def test_run_stream_and_download_csv(self):
        resp = self.client.post("/run", json={"pop": 80, "gens": 250, "mut": 0.08, "seed": 42})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"ok": True})

        sse_resp = self.client.get("/progress")
        self.assertEqual(sse_resp.status_code, 200)
        raw_stream = sse_resp.get_data(as_text=True)

        events = []
        for block in raw_stream.split("\n\n"):
            if block.startswith("data: "):
                events.append(json.loads(block[len("data: "):]))

        done_events = [e for e in events if e.get("type") == "done"]
        self.assertEqual(len(done_events), 1, f"Expected done event, got: {events[-3:]}")
        done = done_events[0]
        self.assertEqual(done["best"]["f1"], 0)
        self.assertEqual(len(done["timetables"]), 3)
        self.assertGreater(len(done["pareto_solutions"]), 0)

        dl = self.client.get("/download/schedule")
        self.assertEqual(dl.status_code, 200)
        csv_text = dl.get_data(as_text=True)
        self.assertIn("Course,Groups,Teacher", csv_text)
        self.assertIn("Maths (CM)", csv_text)
        dl.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
