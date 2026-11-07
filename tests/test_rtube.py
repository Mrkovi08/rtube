"""Rtube unit tests. Run from the repo root:  python3 -m unittest discover -s tests -v

They need PyGObject (GTK4 / GStreamer typelibs), like the app itself, but no display,
no network and no yt-dlp: external commands are replaced with fakes.
"""
import importlib.util
import os
import sys
import threading
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

os.environ["RTUBE_LANG"] = "en"  # deterministic messages
ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("rtube_app", ROOT / "rtube.py")
rt = importlib.util.module_from_spec(spec)
sys.modules["rtube_app"] = rt
spec.loader.exec_module(rt)


class TimeAndDuration(unittest.TestCase):
    def test_fmt_time(self):
        self.assertEqual(rt.fmt_time(None), "—")
        self.assertEqual(rt.fmt_time("abc"), "—")
        self.assertEqual(rt.fmt_time(-5), "—")
        self.assertEqual(rt.fmt_time(65), "1:05")
        self.assertEqual(rt.fmt_time(213.9), "3:33")

    def test_norm_duration(self):
        self.assertIsNone(rt.norm_duration(None))
        self.assertIsNone(rt.norm_duration("x"))
        self.assertEqual(rt.norm_duration("12.7"), 12)


class FriendlyError(unittest.TestCase):
    def test_unavailable_video(self):
        msg = rt.friendly_error("ERROR: [youtube] abc: Video unavailable")
        self.assertEqual(msg, rt.tr("A videó nem elérhető."))

    def test_private_video(self):
        msg = rt.friendly_error("ERROR: Private video. Sign in if you've been granted access")
        self.assertEqual(msg, rt.tr("A videó nem elérhető."))

    def test_no_audio_format(self):
        msg = rt.friendly_error("ERROR: Requested format is not available")
        self.assertEqual(msg, rt.tr("Ehhez a videóhoz nincs lejátszható hang."))

    def test_timeout(self):
        self.assertEqual(rt.friendly_error(rt.TIMEOUT_MSG), rt.tr(rt.TIMEOUT_MSG))

    def test_unknown_error_uses_last_line_and_is_capped(self):
        msg = rt.friendly_error("first\n" + "x" * 500)
        self.assertEqual(len(msg), 160)
        self.assertTrue(msg.startswith("xxx"))

    def test_empty_error(self):
        self.assertEqual(rt.friendly_error(""), rt.tr("Ismeretlen hiba."))


class ParseTracks(unittest.TestCase):
    def test_skips_invalid_and_fills_defaults(self):
        payload = {
            "entries": [
                None,
                {"title": "no id"},
                {"id": "abc", "title": "Song", "uploader": "Up", "duration": "61.2",
                 "thumbnails": [{"url": "small"}, {"url": "big"}]},
                {"id": "def"},
            ]
        }
        tracks = rt.parse_tracks(payload)
        self.assertEqual([t["id"] for t in tracks], ["abc", "def"])
        self.assertEqual(tracks[0]["channel"], "Up")
        self.assertEqual(tracks[0]["duration"], 61)
        self.assertEqual(tracks[0]["thumb"], "big")
        self.assertEqual(tracks[1]["title"], "def")
        self.assertIsNone(tracks[1]["thumb"])

    def test_empty_payload(self):
        self.assertEqual(rt.parse_tracks({}), [])


class YtDlpVersion(unittest.TestCase):
    def test_date_parsing(self):
        self.assertEqual(rt._ytdlp_date("2026.10.26"), (2026, 10, 26))
        self.assertEqual(rt._ytdlp_date("2026.11.04.232659"), (2026, 11, 4))
        self.assertIsNone(rt._ytdlp_date("garbage"))
        self.assertIsNone(rt._ytdlp_date(None))

    def test_freshness(self):
        recent = (date.today() - timedelta(days=5)).strftime("%Y.%m.%d")
        old = (date.today() - timedelta(days=rt.YTDLP_MAX_AGE_DAYS + 30)).strftime("%Y.%m.%d")
        self.assertTrue(rt._ytdlp_fresh(recent))
        self.assertFalse(rt._ytdlp_fresh(old))
        self.assertFalse(rt._ytdlp_fresh("garbage"))


class Language(unittest.TestCase):
    def test_tr_english_and_hungarian(self):
        self.assertEqual(rt.tr("Szól", lang="hu"), "Szól")
        self.assertEqual(rt.tr("Szól", lang="en"), rt.EN["Szól"])

    def test_every_english_value_is_non_empty(self):
        self.assertTrue(all(v.strip() for v in rt.EN.values()))


class PlaybackFallback(unittest.TestCase):
    """_resolve_worker: web_embedded first, then the default client (after waiting)."""

    def make_app(self):
        app = types.SimpleNamespace(
            play_gen=1, closing=False, procs={}, proc_lock=threading.Lock()
        )
        app._apply_stream = object()
        app._resolve_worker = lambda vid, gen, attempt=0: rt.Rtube._resolve_worker(app, vid, gen, attempt)
        return app

    def run_worker(self, results, **patches):
        """results: list of (stdout, stderr, code) returned by successive run_cmd calls."""
        app = self.make_app()
        calls, applied = [], []

        def fake_run(cmd, *_a):
            calls.append(cmd)
            return results[len(calls) - 1]

        with mock.patch.object(rt, "run_cmd", fake_run), \
             mock.patch.object(rt, "ytdlp_bin", lambda: Path("yt-dlp")), \
             mock.patch.object(rt.time, "sleep") as sleep, \
             mock.patch.object(rt.GLib, "idle_add", lambda fn, *a: applied.append(a)):
            app._resolve_worker("vid", 1, 0)
        return calls, applied, sleep

    def test_first_client_success_uses_web_embedded_and_does_not_wait(self):
        calls, applied, sleep = self.run_worker([("https://x/audio\n", "", 0)])
        self.assertEqual(len(calls), 1)
        self.assertIn("youtube:player_client=web_embedded", calls[0])
        sleep.assert_not_called()
        self.assertEqual(applied, [(1, "https://x/audio", None, 0)])

    def test_failure_falls_back_to_default_client_and_waits(self):
        calls, applied, sleep = self.run_worker(
            [("", "ERROR: embedding disabled", 1), ("https://x/audio\n", "", 0)]
        )
        self.assertEqual(len(calls), 2)
        self.assertNotIn("youtube:player_client=web_embedded", calls[1])
        sleep.assert_called_once_with(rt.AD_GATE_WAIT)
        self.assertEqual(applied, [(1, "https://x/audio", None, 1)])

    def test_all_attempts_fail_reports_the_error(self):
        calls, applied, _ = self.run_worker(
            [("", "ERROR: Video unavailable", 1), ("", "ERROR: Video unavailable", 1)]
        )
        self.assertEqual(len(calls), 2)
        gen, url, message, attempt = applied[0]
        self.assertEqual(url, "")
        self.assertEqual(message, rt.tr("A videó nem elérhető."))

    def test_stale_generation_stops_retrying(self):
        app = self.make_app()
        app.play_gen = 2  # the user already started another song
        calls = []
        with mock.patch.object(rt, "run_cmd", lambda cmd, *_a: calls.append(cmd) or ("", "ERROR", 1)), \
             mock.patch.object(rt, "ytdlp_bin", lambda: Path("yt-dlp")), \
             mock.patch.object(rt.GLib, "idle_add", lambda *_a: None):
            app._resolve_worker("vid", 1, 0)
        self.assertEqual(len(calls), 1)


class Theme(unittest.TestCase):
    def test_dark_css_is_unchanged(self):
        self.assertEqual(rt.themed_css(rt.MODERN_CSS, dark=True), rt.MODERN_CSS)

    def test_every_mapped_color_exists_in_the_stylesheet(self):
        for dark_color in rt.LIGHT_COLORS:
            self.assertIn(dark_color, rt.MODERN_CSS, dark_color)

    def test_light_css_has_no_dark_surface_colors_left(self):
        light = rt.themed_css(rt.MODERN_CSS, dark=False)
        for dark_only in ("#232327", "#ededf0", "#2a2a2f", "#323238"):
            self.assertNotIn(dark_only, light)
        self.assertIn("background-color: #f4f4f6;", light)  # window background
        self.assertIn("color: #1c1c1f;", light)  # text

    def test_unknown_colors_are_left_alone(self):
        self.assertEqual(rt.themed_css("a { color: #123456; }", dark=False), "a { color: #123456; }")

    def settings_stub(self, scheme, name):
        props = {"gtk-interface-color-scheme": scheme, "gtk-theme-name": name}
        return types.SimpleNamespace(get_property=lambda key: props[key])

    def test_system_theme_detection(self):
        cases = [(1, "Adwaita", True), (2, "Adwaita-dark", False),
                 (0, "Adwaita-dark", True), (0, "Adwaita", False), (0, "", True)]
        for scheme, name, expected in cases:
            with mock.patch.object(rt.Gtk.Settings, "get_default",
                                   return_value=self.settings_stub(scheme, name)):
                self.assertEqual(rt.detect_system_dark(), expected, (scheme, name))

    def test_theme_button_cycles_and_saves(self):
        saved, applied = [], []
        app = types.SimpleNamespace(
            theme_mode="dark",
            _save_state=lambda **kw: saved.append(kw),
            _apply_theme=lambda: applied.append(1),
        )
        seen = []
        for _ in range(4):
            rt.Rtube._on_theme_click(app)
            seen.append(app.theme_mode)
        self.assertEqual(seen, ["light", "auto", "dark", "light"])
        self.assertEqual(saved[0], {"theme": "light"})
        self.assertEqual(len(applied), 4)

    def test_load_theme_from_state_file(self):
        import json, tempfile
        app = types.SimpleNamespace()
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            with mock.patch.object(rt, "STATE_PATH", state):
                self.assertEqual(rt.Rtube._load_theme(app), "dark")  # no file
                state.write_text(json.dumps({"theme": "light"}))
                self.assertEqual(rt.Rtube._load_theme(app), "light")
                state.write_text(json.dumps({"theme": "neon"}))
                self.assertEqual(rt.Rtube._load_theme(app), "dark")  # invalid value
                state.write_text("not json")
                self.assertEqual(rt.Rtube._load_theme(app), "dark")


if __name__ == "__main__":
    unittest.main()
