import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tv_disc_helpers import build_episode_plan, classify_tv_candidates, tvmaze_search  # noqa: E402


SAMPLE_PARSED = {
    "titles": [
        {"id": 4, "duration": "00:22:01", "duration_seconds": 1321, "chapters": 6, "playlist": "4", "title_confidence": "alternate", "title_duplicate_group_size": 2},
        {"id": 5, "duration": "00:21:58", "duration_seconds": 1318, "chapters": 6, "playlist": "5", "title_confidence": "alternate", "title_duplicate_group_size": 2},
        {"id": 12, "duration": "01:46:00", "duration_seconds": 6360, "chapters": 18, "playlist": "12", "title_confidence": "high", "title_duplicate_group_size": 1},
    ],
    "summary": {"disc_label": "Sample Disc", "drive": "/dev/sr0"},
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TvDiscHelperTests(unittest.TestCase):
    def test_classify_tv_candidates_prefers_episode_lengths(self):
        data = classify_tv_candidates(SAMPLE_PARSED)
        ids = [item["id"] for item in data["episode_candidates"]]
        self.assertEqual(ids[:2], [4, 5])
        self.assertEqual(data["episode_candidates"][0]["content_kind"], "episode")

    def test_build_episode_plan_maps_consecutive_titles(self):
        plan = build_episode_plan(
            SAMPLE_PARSED,
            "Sample Show",
            2,
            4,
            selected_titles=["4", "5"],
            metadata_episodes=[
                {"season": 2, "number": 4, "name": "First"},
                {"season": 2, "number": 5, "name": "Second"},
            ],
        )
        self.assertEqual(plan["selected_titles"], ["4", "5"])
        self.assertEqual(plan["planned_titles"][0]["code"], "S02E04")
        self.assertIn("First", plan["planned_titles"][0]["filename"])

    @patch("tv_disc_helpers.urllib.request.urlopen")
    def test_tvmaze_search_parses_results(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(
            [
                {"show": {"id": 10, "name": "Sample Show", "premiered": "2010-01-01", "status": "Ended", "summary": "<p>Example</p>"}}
            ]
        )
        results = tvmaze_search("sample")
        self.assertEqual(results[0]["id"], 10)
        self.assertEqual(results[0]["name"], "Sample Show")
        self.assertEqual(results[0]["summary"], "Example")


if __name__ == "__main__":
    unittest.main()
