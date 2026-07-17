import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_validation import normalize_config, validate_update_payload  # noqa: E402


DEFAULTS = {
    "output_dir": "/mnt/output",
    "rip_dir": "/mnt/ripped",
    "final_dir": "",
    "smb_staging_dir": "/mnt/smb_staging",
    "usb_staging_dir": "/mnt/usb_staging",
    "max_threads": 4,
    "rescan_interval": 30,
    "min_size_mb": 100,
    "makemkv_minlength": 1200,
    "auth_user": "admin",
    "auth_password": "changeme",
    "auth_additional_users": [],
    "handbrake": {"quality": 20, "audio_bitrate_kbps": 128, "audio_mode": "encode", "audio_encoder": "av_aac"},
    "handbrake_dvd": {"quality": 20, "audio_bitrate_kbps": 128, "audio_mode": "encode", "audio_encoder": "av_aac"},
    "handbrake_br": {"quality": 25, "audio_bitrate_kbps": 128, "audio_mode": "encode", "audio_encoder": "av_aac"},
    "makemkv_titles": [],
    "makemkv_audio_langs": [],
    "makemkv_subtitle_langs": [],
    "makemkv_preferred_audio_langs": ["eng"],
    "makemkv_preferred_subtitle_langs": ["eng"],
    "makemkv_keep_ripped": False,
    "makemkv_exclude_commentary": False,
    "makemkv_prefer_surround": True,
    "makemkv_auto_rip": False,
    "low_bitrate_auto_proceed": False,
    "low_bitrate_auto_skip": False,
    "advanced_mode": False,
    "queue_pause_after_current": False,
    "naming_template_movie": "{title}",
    "naming_template_disc": "{disc_label}",
    "final_destinations": {"movies": "", "tv": "", "extras": ""},
    "notifications": {"browser": True, "job_start": True, "job_complete": True, "job_failed": True},
    "home_assistant": {"enabled": False, "url": "", "token": "", "notify_service": "", "title_prefix": "Linux Video Encoder"},
    "audio_subtitle_presets": {},
    "disc_profile_presets": {},
    "disc_workflow": {"mode": "movies", "show_title": "", "show_id": "", "season_number": 1, "episode_start": 1, "metadata_provider": "tvmaze", "auto_apply_plan": True, "episode_count": 4},
    "disc_title_preferences": {},
    "disc_episode_preferences": {},
    "handbrake_presets": [],
}


class ConfigValidationTests(unittest.TestCase):
    def test_normalize_config_clamps_and_normalizes(self):
        cfg = normalize_config(
            {
                "rescan_interval": "9999",
                "makemkv_titles": "1, 2 ,3",
                "notifications": {"browser": 0, "job_failed": 1},
                "home_assistant": {"enabled": 1, "url": "https://ha.local/", "token": "abc", "notify_service": "notify.phone"},
                "final_destinations": {"movies": "/movies", "tv": "/tv"},
                "naming_template_movie": "bad-template-without-tokens",
                "disc_title_preferences": {"disc-a": {"prefer_titles": "5,6", "blocked_titles": ["7"]}},
                "disc_workflow": {"mode": "tv", "show_title": "Test Show", "season_number": "2", "episode_start": "4", "episode_count": "8"},
                "disc_episode_preferences": {"disc-a": {"show_title": "Test Show", "selected_titles": "1,2", "planned_titles": [{"title_id": "1", "season": "2", "episode": "4"}]}},
            },
            DEFAULTS,
        )
        self.assertEqual(cfg["rescan_interval"], 600)
        self.assertEqual(cfg["makemkv_titles"], ["1", "2", "3"])
        self.assertFalse(cfg["notifications"]["browser"])
        self.assertTrue(cfg["notifications"]["job_failed"])
        self.assertTrue(cfg["home_assistant"]["enabled"])
        self.assertEqual(cfg["home_assistant"]["url"], "https://ha.local")
        self.assertEqual(cfg["home_assistant"]["notify_service"], "notify.phone")
        self.assertEqual(cfg["final_destinations"]["movies"], "/movies")
        self.assertEqual(cfg["final_destinations"]["tv"], "/tv")
        self.assertEqual(cfg["naming_template_movie"], "{title}")
        self.assertEqual(cfg["disc_title_preferences"]["disc-a"]["prefer_titles"], ["5", "6"])
        self.assertEqual(cfg["disc_workflow"]["mode"], "tv")
        self.assertEqual(cfg["disc_workflow"]["season_number"], 2)
        self.assertEqual(cfg["disc_episode_preferences"]["disc-a"]["selected_titles"], ["1", "2"])

    def test_validate_update_payload_returns_warnings(self):
        payload, warnings = validate_update_payload(
            {
                "rescan_interval": 0,
                "makemkv_minlength": 999999,
                "naming_template_disc": "no-token-value",
            }
        )
        self.assertEqual(payload["rescan_interval"], 1)
        self.assertEqual(payload["makemkv_minlength"], 43200)
        self.assertEqual(payload["naming_template_disc"], "{disc_label}")
        self.assertGreaterEqual(len(warnings), 2)


if __name__ == "__main__":
    unittest.main()
