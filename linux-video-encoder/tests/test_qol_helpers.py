import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qol_helpers import build_job_details, build_name_suggestion, guess_library_type  # noqa: E402


class QolHelpersTests(unittest.TestCase):
    def test_guess_library_type(self):
        self.assertEqual(guess_library_type("/tmp/Show.S01E02.mkv"), "tv")
        self.assertEqual(guess_library_type("/tmp/bonus_featurette.mkv"), "extras")
        self.assertEqual(guess_library_type("/tmp/Movie.mkv"), "movies")

    def test_build_name_suggestion_replaces_tokens(self):
        suggestion = build_name_suggestion(
            "/tmp/Movie File.mkv",
            "movies",
            {"movie": "{title} ({resolution}) [{encoder}]", "disc": "{disc_label}"},
            title="The Movie",
            resolution="1080p",
            encoder="nvenc_h265",
        )
        self.assertEqual(suggestion, "The Movie (1080p) [nvenc_h265]")

    def test_build_job_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "Show.S01E01.mkv"
            source.write_text("x", encoding="utf-8")
            details = build_job_details(
                {
                    "source": str(source),
                    "destination": str(source),
                    "state": "error",
                    "message": "HandBrake failed",
                },
                "recent",
                {"disc_label": "Sample Disc"},
                {"tv": "/library/tv", "movies": "/library/movies", "extras": "/library/extras"},
                {"movie": "{title}", "disc": "{disc_label}"},
            )
            self.assertEqual(details["library_type"], "tv")
            self.assertEqual(details["recommended_destination_root"], "/library/tv")
            self.assertEqual(details["error_class"], "encoder-run")


if __name__ == "__main__":
    unittest.main()
