import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from status_tracker import StatusTracker  # noqa: E402


class StatusTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        root = Path(self.tempdir.name)
        self.log_path = root / "app.log"
        self.log_path.write_text("", encoding="utf-8")
        self.state_path = root / "state.json"
        self.tracker = StatusTracker(self.log_path, state_path=self.state_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_queue_controls_and_sorting(self):
        self.tracker.start("b.mkv", "/tmp/b.mkv", state="queued")
        self.tracker.start("a.mkv", "/tmp/a.mkv", state="queued")
        self.tracker.start("c.mkv", "/tmp/c.mkv", state="queued")
        self.tracker.move_queue_item("c.mkv", -2)
        self.tracker.set_queue_hold("a.mkv", True)
        ordered = self.tracker.sort_candidate_paths(["a.mkv", "b.mkv", "c.mkv"])
        self.assertEqual(ordered, ["c.mkv", "b.mkv", "a.mkv"])

    def test_complete_records_notification_and_failed_source(self):
        self.tracker.start("movie.mkv", "/tmp/movie-out.mkv", state="running")
        self.tracker.complete("movie.mkv", False, "/tmp/movie-out.mkv", "HandBrake encode failed")
        notifications = self.tracker.notifications()
        self.assertEqual(self.tracker.last_failed_source(), "movie.mkv")
        self.assertTrue(any(item["kind"] == "job-failed" for item in notifications))


if __name__ == "__main__":
    unittest.main()
