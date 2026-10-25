#!/usr/bin/env python3
"""Rtube — YouTube kereső, csak hang. Matt szürke dizájn kék gombokkal és közvetlen mpv videó integrációval."""

import hashlib
import json
import os
import platform
import re
import shutil
import signal
import sys
import subprocess
import tempfile
import threading
import time
import zipfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gst", "1.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gst, Gtk, Pango

APP_ID = "io.github.rtube.Rtube"
# X11: a WM_CLASS egyezzen a .desktop StartupWMClass-szal (különben "rtube.py" lenne)
GLib.set_prgname(APP_ID)
GLib.set_application_name("Rtube")

HOME = Path.home()
CONF = HOME / ".config/rtube"
OLD_CONF = HOME / ".config/hangzo"
CACHE = HOME / ".cache/rtube/thumbs"
FAV_PATH = CONF / "favorites.json"
STATE_PATH = CONF / "state.json"
SETTINGS_PATH = HOME / ".config/DankMaterialShell/settings.json"
# Felhasználói eszközök (friss yt-dlp, deno), ha a rendszeré hiányzik/régi (pl. Ubuntu/Mint)
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
TOOLS_DIR = DATA_HOME / "rtube/bin"
TOOLS_STATE = CONF / "tools.json"

AUDIO_FORMAT = (
    "bestaudio[acodec=opus][ext=webm]/"
    "bestaudio[acodec=opus]/"
    "bestaudio[ext=webm]/"
    "bestaudio[ext=mp3]"
)
UA = "Mozilla/5.0"

# Kinézet: RTUBE_SKIN=modern|winamp, vagy rtube --modern / --winamp
SKIN = os.environ.get("RTUBE_SKIN", "").strip().lower()
if "--modern" in sys.argv:
    SKIN = "modern"
elif "--winamp" in sys.argv:
    SKIN = "winamp"
MODERN = SKIN == "modern"
# A modern kinézet saját SVG ikonjai ide kerülnek (felhasználói cache, csomagból telepítve is írható)
ICON_DIR = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache") / "rtube/icons"


def T(hu, en):
    """Kétnyelvű felirat: magyar nyelvnél magyar, egyébként angol (LANG lent, detect_lang)."""
    return hu if LANG == "hu" else en


# Szív ikonok (symbolic SVG, a GTK a szövegszínre színezi őket).
HEART_OUTLINE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    '<path fill="#2e3436" fill-rule="evenodd" d="M8 14.6 2.5 9.2C1 7.7 1 5.3 2.5 3.8 4 2.3 6.4 2.3 7.9 3.8L8 3.9l.1-.1'
    'c1.5-1.5 3.9-1.5 5.4 0 1.5 1.5 1.5 3.9 0 5.4Z'
    'M8 12.5l4.4-4.3c.9-.9.9-2.4 0-3.3-.9-.9-2.4-.9-3.3 0L8 6 6.9 4.9c-.9-.9-2.4-.9-3.3 0-.9.9-.9 2.4 0 3.3Z"/></svg>'
)
HEART_FILLED_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    '<path fill="#2e3436" d="M8 14.6 2.5 9.2C1 7.7 1 5.3 2.5 3.8 4 2.3 6.4 2.3 7.9 3.8L8 3.9l.1-.1'
    'c1.5-1.5 3.9-1.5 5.4 0 1.5 1.5 1.5 3.9 0 5.4Z"/></svg>'
)


_SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
PLAY_SVG = _SVG_HEAD + (
    '<path fill="#2e3436" d="M5 3.1v9.8c0 .7.8 1.1 1.3.7l7.3-4.9c.5-.3.5-1.1 0-1.4L6.3 2.4C5.8 2 5 2.4 5 3.1Z"/></svg>'
)
PAUSE_SVG = _SVG_HEAD + (
    '<rect fill="#2e3436" x="3.5" y="2.5" width="3.2" height="11" rx="1"/>'
    '<rect fill="#2e3436" x="9.3" y="2.5" width="3.2" height="11" rx="1"/></svg>'
)
VIDEO_SVG = _SVG_HEAD + (
    '<path fill="#2e3436" fill-rule="evenodd" d="M3 3.5h6.5A2 2 0 0 1 11.5 5.5v5a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2Z'
    'M3 5a.5.5 0 0 0-.5.5v5a.5.5 0 0 0 .5.5h6.5a.5.5 0 0 0 .5-.5v-5A.5.5 0 0 0 9.5 5Z"/>'
    '<path fill="#2e3436" d="m12.5 6.6 2.2-1.5c.3-.2.8 0 .8.4v5c0 .4-.5.6-.8.4l-2.2-1.5Z"/></svg>'
)
COMPACT_SVG = _SVG_HEAD + (
    '<path fill="#2e3436" fill-rule="evenodd" d="M6 1h4a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2Z'
    'M6 2.5a.5.5 0 0 0-.5.5v10a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5V3a.5.5 0 0 0-.5-.5Z"/>'
    '<rect fill="#2e3436" x="6.5" y="4" width="3" height="3" rx=".6"/>'
    '<rect fill="#2e3436" x="6.5" y="9" width="3" height="1.3" rx=".6"/></svg>'
)


def ensure_heart_icons():
    """A saját symbolic ikonokat a cache-be írja; True, ha használhatók."""
    try:
        # SVG betöltő (librsvg) nélkül a saját ikonok törött képként jelennének meg:
        # ilyenkor maradnak a téma beépített ikonjai
        if not any("svg" in (f.get_name() or "") for f in GdkPixbuf.Pixbuf.get_formats()):
            return False
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        for name, data in (
            ("rtube-heart-outline-symbolic.svg", HEART_OUTLINE_SVG),
            ("rtube-heart-filled-symbolic.svg", HEART_FILLED_SVG),
            ("rtube-play-symbolic.svg", PLAY_SVG),
            ("rtube-pause-symbolic.svg", PAUSE_SVG),
            ("rtube-video-symbolic.svg", VIDEO_SVG),
            ("rtube-compact-symbolic.svg", COMPACT_SVG),
        ):
            path = ICON_DIR / name
            if not path.exists() or path.read_text() != data:
                path.write_text(data)
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        theme.add_search_path(str(ICON_DIR))
        return True
    except Exception:
        return False


# ---- NYELV (magyar / angol) ----
def detect_lang():
    """RTUBE_LANG=hu|en felülír; különben a rendszer nyelve (LC_ALL, LC_MESSAGES, LANG)."""
    forced = os.environ.get("RTUBE_LANG", "").strip().lower()
    if forced.startswith("hu"):
        return "hu"
    if forced.startswith("en"):
        return "en"
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "").strip()
        if value:
            return "hu" if value.lower().startswith("hu") else "en"
    return "en"


LANG = detect_lang()

# Magyar (eredeti) szöveg -> angol fordítás
EN = {
    # Kezelőfelület
    "YouTube keresés…": "Search YouTube…",
    "Keresés": "Search",
    "Kedvencek": "Favorites",
    "Keress egy számra, vagy nyisd meg a kedvenceket.": "Search for a song, or open your favorites.",
    "Keress egy számra.": "Search for a song.",
    "Nincs lejátszás": "Nothing playing",
    "Válassz egy számot": "Pick a song",
    "Hangerő": "Volume",
    "Megnyitás videóként (mpv)": "Open as video (mpv)",
    "Még nincs kedvenc. A szív menti a számot.": "No favorites yet. Tap the heart to save a song.",
    # Állapotüzenetek
    "Keresés…": "Searching…",
    "Nincs találat.": "No results.",
    "{n} találat": "{n} results",
    "A keresés nem sikerült.": "Search failed.",
    "A találatokat nem sikerült olvasni.": "Couldn't read the search results.",
    "Hiányzik a yt-dlp.": "yt-dlp is missing.",
    "Hangfolyam betöltése…": "Loading audio stream…",
    "Nincs hangfolyam.": "No audio stream.",
    "Szól": "Playing",
    "Szünet": "Paused",
    "Vége": "Finished",
    "Pufferelés {percent}%": "Buffering {percent}%",
    "Lejátszás sikertelen.": "Playback failed.",
    "mpv indítása...": "Starting mpv...",
    "mpv elindítva.": "mpv started.",
    "Hiba: Az mpv nincs telepítve.": "Error: mpv is not installed.",
    # Hibaüzenetek
    "Ehhez a videóhoz nincs lejátszható hang.": "No playable audio for this video.",
    "A videó nem elérhető.": "The video is unavailable.",
    "Lejárt a várakozás.": "Timed out.",
    "Ismeretlen hiba.": "Unknown error.",
    "hiba": "error",
    "A GStreamer playbin nem elérhető.": "GStreamer playbin is not available.",
    # Eszközök (yt-dlp, deno) letöltése
    "yt-dlp letöltése…": "Downloading yt-dlp…",
    "yt-dlp frissítése…": "Updating yt-dlp…",
    "yt-dlp kész: {version}": "yt-dlp ready: {version}",
    "deno letöltése (YouTube JS futtatókörnyezet)…": "Downloading deno (YouTube JS runtime)…",
    "deno kész: {version}": "deno ready: {version}",
    "A letöltés nem sikerült: {name}": "Download failed: {name}",
    "A yt-dlp még töltődik…": "yt-dlp is still downloading…",
}


def tr(text, lang=None, **kwargs):
    """Fordítás: magyar nyelvnél az eredeti szöveg, különben az angol."""
    lang = lang or LANG
    out = text if lang == "hu" else EN.get(text, text)
    if kwargs:
        if lang != "hu" and text == "{n} találat" and kwargs.get("n") == 1:
            out = "1 result"
        out = out.format(**kwargs)
    return out


# Belső jelzés időtúllépésre (friendly_error fordítja le)
TIMEOUT_MSG = "Lejárt a várakozás."


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")[:6]
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def load_palette():
    # Fix matt szürke és kék paletta
    return {
        "surface": "#3b3e42",           # Matt szürke fő háttér
        "surface_low": "#323538",       # Kicsit sötétebb (pl. keresőmező)
        "surface_high": "#45484d",      # Világosabb szürke (panelek)
        "surface_highest": "#54585e",   # Legvilágosabb szürke (kiemelések)
        "on_surface": "#ffffff",        # Fehér betűk
        "on_variant": "#b8c0c9",        # Halványabb betűk
        "primary": "#3a86ff",           # Kék szín a kereteknek/gomboknak
        "on_primary": "#ffffff",        # Fehér betű a kék gombokon
        "primary_container": "#2563eb", # Sötétebb kék (aktív gombok)
        "on_primary_container": "#ffffff",
    }


def load_radius():
    try:
        value = json.loads(SETTINGS_PATH.read_text()).get("cornerRadius", 12)
        return max(8, min(24, int(value)))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return 12


def build_css(p, radius):
    pill = radius + 12
    return f"""
    window, window.background {{
      background-color: {rgba(p["surface"], 0.55)};
      color: {p["on_surface"]};
    }}
    label {{ color: {p["on_surface"]}; }}
    label.brand {{
      color: {p["primary"]};
      font-weight: 700;
      font-size: 1.35em;
    }}
    label.title {{ font-weight: 600; }}
    label.dim {{ color: {p["on_variant"]}; font-size: 0.92em; }}
    .panel {{
      background-color: {rgba(p["surface_high"], 0.40)};
      border-radius: {radius}px;
      border: 1px solid rgba(255, 255, 255, 0.10);
      box-shadow: inset 0 1px rgba(255, 255, 255, 0.06);
      padding: 12px;
    }}
    entry.search, entry.search:focus, entry.search:focus-visible {{
      background-color: {rgba(p["surface_low"], 0.45)};
      color: {p["on_surface"]};
      caret-color: {p["primary"]};
      border-radius: {pill}px;
      border: 1px solid {p["primary"]};
      padding: 6px 14px;
      min-height: 28px;
      outline: none;
      outline-width: 0;
      box-shadow: none;
    }}
    entry.search:focus, entry.search:focus-visible {{
      border-color: {p["primary"]};
    }}
    button {{
      background-image: none;
      background-color: transparent;
      color: {p["on_surface"]};
      border-radius: {radius}px;
      border: 1px solid {p["primary"]};
      padding: 6px 14px;
      box-shadow: none;
      outline: none;
    }}
    button:hover {{
      background-image: none;
      background-color: {rgba(p["primary"], 0.16)};
    }}
    button.accent, button.play {{
      background-image: none;
      background-color: {p["primary"]};
      color: {p["on_primary"]};
      border-color: transparent;
    }}
    button.accent:hover, button.play:hover {{
      background-image: none;
      background-color: {p["primary_container"]};
      color: {p["on_primary_container"]};
    }}
    button.active-view {{
      background-image: none;
      background-color: {p["primary_container"]};
      color: {p["on_primary_container"]};
      border-color: transparent;
    }}
    button.play {{
      min-width: 46px;
      min-height: 46px;
      border-radius: 23px;
      font-size: 16px;
      padding: 0;
    }}
    button.icon-btn {{
      min-width: 40px;
      min-height: 40px;
      padding: 0;
      font-size: 18px;
    }}
    button.heart {{
      border: none;
      background-image: none;
      background-color: transparent;
      min-width: 40px;
      min-height: 40px;
      padding: 0;
      font-size: 18px;
      border-radius: 20px;
    }}
    button.heart.fav {{ color: {p["primary"]}; }}
    list, scrolledwindow, viewport {{ background: transparent; }}
    list row {{
      background: transparent;
      border-radius: {radius}px;
      padding: 4px 6px;
      border: 1px solid transparent;
    }}
    list row:hover {{ background-color: rgba(255, 255, 255, 0.08); }}
    list row.playing {{
      background-color: {rgba(p["primary"], 0.20)};
      border-color: {p["primary"]};
    }}
    .cover-frame {{
      background-color: {rgba(p["surface_highest"], 0.50)};
      border-radius: 8px;
    }}
    scale trough {{
      background-color: rgba(255, 255, 255, 0.15);
      border-radius: 99px;
      min-height: 6px;
    }}
    scale highlight {{
      background-color: {p["primary"]};
      border-radius: 99px;
    }}
    scale slider {{
      background-color: {p["primary"]};
      border-radius: 99px;
    }}
    button.play.player-btn {{
      min-width: 40px;
      min-height: 40px;
      border-radius: {radius}px;
      font-size: 18px;
      padding: 0;
    }}
    button.icon-btn.fav {{ color: {p["primary"]}; }}
    """


WINAMP_CSS = """
window, window.background {
  background-color: #232333;
  color: #00e600;
  font-family: "DejaVu Sans Mono", monospace;
}
label { color: #00e600; font-family: "DejaVu Sans Mono", monospace; }
label.brand {
  color: #f0c000;
  font-weight: 800;
  letter-spacing: 3px;
  text-shadow: 1px 1px #000000;
}
label.dim { color: #4fa64f; }
.panel {
  background-color: #000000;
  border-radius: 0;
  border-style: solid;
  border-width: 2px;
  border-color: #10101a #6a6a8a #6a6a8a #10101a;
  box-shadow: 0 0 0 2px #3a3a50;
}
entry.search, entry.search:focus, entry.search:focus-visible {
  background-color: #000000;
  color: #00e600;
  caret-color: #00e600;
  border-radius: 0;
  border-style: solid;
  border-width: 2px;
  border-color: #10101a #6a6a8a #6a6a8a #10101a;
}
button, button.accent, button.active-view, button.icon-btn {
  background-image: linear-gradient(to bottom, #d6d6e0, #8a8a9c);
  background-color: #b0b0c0;
  color: #101018;
  border-radius: 1px;
  border-style: solid;
  border-width: 1px;
  border-color: #ffffff #3a3a48 #3a3a48 #ffffff;
  font-weight: 700;
}
button label { color: #101018; }
button:hover, button.accent:hover, button.icon-btn:hover {
  background-image: linear-gradient(to bottom, #e8e8f0, #a0a0b4);
}
button:active, button.active-view {
  background-image: linear-gradient(to bottom, #7a7a8c, #b8b8c8);
  border-color: #3a3a48 #ffffff #ffffff #3a3a48;
}
button.play, button.play:hover {
  background-image: linear-gradient(to bottom, #d6d6e0, #8a8a9c);
  color: #101018;
  border-radius: 1px;
  border-style: solid;
  border-width: 1px;
  border-color: #ffffff #3a3a48 #3a3a48 #ffffff;
}
button.heart, button.heart label { background-image: none; background-color: transparent; border: none; color: #4fa64f; }
button.heart.fav, button.heart.fav label { color: #f0c000; }
button.icon-btn.fav, button.icon-btn.fav label { color: #c00000; }
list row { border-radius: 0; }
list row:hover { background-color: #0a2a0a; }
list row.playing { background-color: #00309a; border-color: #00309a; }
list row.playing label { color: #ffffff; }
.cover-frame { background-color: #000000; border-radius: 0; }
scale trough {
  background-color: #000000;
  border-radius: 0;
  border-style: solid;
  border-width: 1px;
  border-color: #10101a #6a6a8a #6a6a8a #10101a;
}
scale highlight { background-image: linear-gradient(to right, #00a000, #e0e000, #e08000); background-color: #00c000; border-radius: 0; }
scale slider {
  background-image: linear-gradient(to bottom, #d6d6e0, #8a8a9c);
  border-radius: 1px;
  min-width: 14px;
  border: 1px solid #3a3a48;
}
"""


MODERN_CSS = """
window, window.background {
  background-color: #1c1c1f;
  color: #ededf0;
  font-family: "Inter", "Inter Variable", "Noto Sans", "Cantarell", sans-serif;
}
label { color: #ededf0; }
label.brand { color: #ededf0; font-weight: 700; font-size: 17px; }
label.title { font-weight: 500; font-size: 13.5px; }
label.dim { color: #9a9aa3; font-size: 12px; }
label.list-head { font-weight: 600; font-size: 13px; }
label.np-label { color: #6b6b74; font-size: 11px; font-weight: 600; letter-spacing: 1.2px; }
label.np-artist { color: #9a9aa3; font-size: 13px; font-weight: 500; }
label.np-title { color: #ededf0; font-size: 19px; font-weight: 600; }
label.time, label.status-line { color: #6b6b74; font-size: 11.5px; font-feature-settings: "tnum"; }
.logo {
  background-color: #5b8cff;
  color: #0f1422;
  border-radius: 8px;
  min-width: 26px;
  min-height: 26px;
}
.panel {
  background-color: #232327;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow: none;
  padding: 12px 10px 10px 10px;
}
.panel.np-card { padding: 22px 24px 20px 24px; }
entry.search, entry.search:focus, entry.search:focus-visible, entry.search:focus-within {
  background-color: #232327;
  color: #ededf0;
  caret-color: #5b8cff;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  padding: 0 12px;
  min-height: 38px;
  outline: none;
  box-shadow: none;
}
entry.search:focus-within { border-color: rgba(91, 140, 255, 0.55); }
entry.search image { color: #6b6b74; }
entry.search text placeholder { color: #6b6b74; }
button {
  background-image: none;
  background-color: transparent;
  color: #9a9aa3;
  border-radius: 12px;
  border: 1px solid transparent;
  box-shadow: none;
  outline: none;
  padding: 0 12px;
}
button:hover { background-color: #2a2a2f; color: #ededf0; }
button:disabled { opacity: 0.45; }
.seg {
  background-color: #232327;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  padding: 3px;
}
.seg button { border-radius: 9px; min-height: 32px; padding: 0 14px; font-weight: 500; font-size: 13px; }
.seg button.active-view, .seg button.active-view:hover {
  background-color: #323238;
  color: #ededf0;
  border-color: transparent;
}
.seg button label { color: inherit; }
button.np-icon {
  min-width: 40px;
  min-height: 40px;
  padding: 0;
  border-radius: 20px;
  background-color: #2a2a2f;
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: #9a9aa3;
  font-size: 17px;
}
button.np-icon:hover { background-color: #323238; color: #ededf0; }
button.np-icon.fav, button.np-icon.fav label { color: #5b8cff; }
button.np-play, button.np-play:hover {
  min-width: 56px;
  min-height: 56px;
  padding: 0;
  border-radius: 28px;
  background-color: #5b8cff;
  color: #0f1422;
  border: none;
  box-shadow: 0 8px 22px rgba(91, 140, 255, 0.35);
  -gtk-icon-size: 20px;
}
button.np-play:hover { background-color: #7aa2ff; }
button.np-play label { color: #0f1422; font-size: 18px; }
button.np-play:disabled { opacity: 0.55; box-shadow: none; }
button.heart {
  border: none;
  background-image: none;
  background-color: transparent;
  min-width: 32px;
  min-height: 32px;
  padding: 0;
  border-radius: 16px;
  color: #6b6b74;
  font-size: 16px;
}
button.heart label { color: inherit; }
button.heart:hover { background-color: #2a2a2f; color: #ededf0; }
button.heart.fav, button.heart.fav:hover { color: #5b8cff; }
list, scrolledwindow, viewport { background: transparent; }
list row {
  background: transparent;
  border-radius: 14px;
  padding: 8px 10px;
  border: 1px solid transparent;
}
list row:hover { background-color: rgba(255, 255, 255, 0.035); }
list row.playing {
  background-color: rgba(91, 140, 255, 0.14);
  border-color: rgba(91, 140, 255, 0.28);
}
list row.playing label.title { color: #7aa2ff; }
.cover-frame {
  background-color: #2a2a2f;
  background-image: radial-gradient(circle at 30% 28%, rgba(255, 178, 122, 0.35), transparent 45%),
                    radial-gradient(circle at 75% 70%, rgba(109, 93, 252, 0.45), transparent 55%),
                    linear-gradient(145deg, #2a2550, #151526);
  border-radius: 10px;
}
.cover-frame.np-cover {
  border-radius: 18px;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45), 0 4px 10px rgba(0, 0, 0, 0.25);
}
scale { padding: 6px 0; }
scale trough {
  background-color: #323238;
  border: none;
  border-radius: 99px;
  min-height: 4px;
}
scale highlight {
  background-color: #5b8cff;
  border: none;
  border-radius: 99px;
  min-height: 4px;
  margin: 0;
}
scale.vol highlight { background-color: #9a9aa3; }
scale slider {
  background-color: transparent;
  background-image: none;
  border: none;
  box-shadow: none;
  outline: none;
  min-width: 0;
  min-height: 0;
  margin: 0;
  border-radius: 99px;
  transition: min-width 120ms ease-out, min-height 120ms ease-out, margin 120ms ease-out;
}
scale:hover slider, scale:active slider, scale slider:active {
  background-color: #ffffff;
  min-width: 12px;
  min-height: 12px;
  margin: -4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}
image.vol-icon { color: #9a9aa3; }
button.compact-btn {
  min-width: 40px;
  min-height: 40px;
  padding: 0;
  border-radius: 12px;
  background-color: #232327;
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: #9a9aa3;
}
button.compact-btn:hover { background-color: #2a2a2f; color: #ededf0; }
button.np-head-btn {
  min-height: 24px;
  padding: 0 8px;
  border-radius: 8px;
  font-size: 12px;
  color: #9a9aa3;
}
button.np-head-btn label { color: inherit; font-size: 12px; }
button.np-head-btn:hover { background-color: #2a2a2f; color: #ededf0; }
.panel.upnext { padding: 8px 8px 8px 10px; border-radius: 16px; }
button.upnext-main { padding: 2px; border-radius: 12px; }
button.upnext-main:hover { background-color: rgba(255, 255, 255, 0.035); }
label.upnext-label { color: #6b6b74; font-size: 10.5px; font-weight: 600; letter-spacing: 1.1px; }
label.upnext-title { color: #ededf0; font-size: 13px; font-weight: 500; }
button.upnext-up { min-width: 32px; min-height: 32px; padding: 0; border-radius: 16px; color: #6b6b74; }
button.upnext-up:hover { background-color: #2a2a2f; color: #ededf0; }
"""


def load_css(provider, css):
    """GTK 4.12+: load_from_string; régebbi GTK 4-en load_from_data."""
    if hasattr(provider, "load_from_string"):
        provider.load_from_string(css)
    else:
        try:
            provider.load_from_data(css, -1)
        except TypeError:
            provider.load_from_data(css.encode("utf-8"))


def fmt_time(seconds):
    if seconds is None:
        return "—"
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "—"
    if total < 0:
        return "—"
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def subtitle(track):
    bits = []
    if track.get("channel"):
        bits.append(track["channel"])
    dur = fmt_time(track.get("duration"))
    if dur != "—":
        bits.append(dur)
    return " · ".join(bits) if bits else "YouTube"


def norm_duration(value):
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


YTDLP_MAX_AGE_DAYS = 90      # ennél régebbi rendszer yt-dlp-t nem használunk YouTube-hoz
YTDLP_JS_MIN = (2025, 11, 12)  # ettől ismeri a --js-runtimes kapcsolót
YTDLP_CHECK_EVERY = 86400    # a saját yt-dlp frissességét naponta egyszer nézzük
NODE_MIN = 20
DENO_MIN = 2

TOOLS = {"ytdlp": None, "js": None, "busy": True}  # induláskor ensure_tools() állítja be
_TOOLS_LOCK = threading.Lock()


def _tool_version(path, args=("--version",)):
    try:
        out = subprocess.run(
            [str(path), *args], capture_output=True, text=True, timeout=20
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return out.strip().splitlines()[0] if out.strip() else None


def _ytdlp_date(version):
    m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", version or "")
    return tuple(int(x) for x in m.groups()) if m else None


def _ytdlp_fresh(version):
    d = _ytdlp_date(version)
    if not d:
        return False
    try:
        return (date.today() - date(*d)).days <= YTDLP_MAX_AGE_DAYS
    except ValueError:
        return False


def _ytdlp_candidates():
    seen, out = set(), []
    env = os.environ.get("RTUBE_YTDLP")
    for c in (env, TOOLS_DIR / "yt-dlp", HOME / ".local/bin/yt-dlp", shutil.which("yt-dlp")):
        if c and Path(c).is_file() and os.access(c, os.X_OK) and str(c) not in seen:
            seen.add(str(c))
            out.append(Path(c))
    return out


def ytdlp_bin():
    """A használandó yt-dlp: a kiválasztott friss, különben a legjobb meglévő."""
    if TOOLS["ytdlp"] is not None:
        return TOOLS["ytdlp"]
    found = _ytdlp_candidates()
    return found[0] if found else TOOLS_DIR / "yt-dlp"


def ytdlp_extra_args():
    """JS futtatókörnyezet a YouTube-hoz (a felhasználói yt-dlp config érvényben marad)."""
    js = TOOLS.get("js")
    return ["--js-runtimes", f"{js[0]}:{js[1]}"] if js else []


def _arch():
    m = platform.machine().lower()
    if m in ("x86_64", "amd64"):
        return "x86_64"
    if m in ("aarch64", "arm64"):
        return "aarch64"
    return None


def _http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "rtube"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _download_verified(url, sha_url, sha_name, dest_tmp):
    """Letölt egy kiadási fájlt és ellenőrzi az SHA-256 összegét."""
    sums = _http_get(sha_url, 30).decode("utf-8", "replace")
    want = None
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == sha_name:
            want = parts[0].lower()
    if not want:
        raise RuntimeError("checksum missing")
    h = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "rtube"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_tmp, "wb") as fh:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            fh.write(chunk)
    if h.hexdigest() != want:
        raise RuntimeError("checksum mismatch")


def _fetch_ytdlp():
    arch = _arch()
    # x86_64/aarch64: önálló bináris (benne van a sütik visszafejtéséhez kellő secretstorage is)
    name = {"x86_64": "yt-dlp_linux", "aarch64": "yt-dlp_linux_aarch64"}.get(arch, "yt-dlp")
    base = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=TOOLS_DIR, prefix=".yt-dlp.")
    os.close(fd)
    try:
        _download_verified(base + name, base + "SHA2-256SUMS", name, tmp)
        os.chmod(tmp, 0o755)
        os.replace(tmp, TOOLS_DIR / "yt-dlp")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return TOOLS_DIR / "yt-dlp"


def _fetch_deno():
    arch = _arch()
    if not arch:
        raise RuntimeError("unsupported architecture")
    name = f"deno-{arch}-unknown-linux-gnu.zip"
    base = "https://github.com/denoland/deno/releases/latest/download/"
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmpzip = tempfile.mkstemp(dir=TOOLS_DIR, prefix=".deno.", suffix=".zip")
    os.close(fd)
    tmpbin = TOOLS_DIR / ".deno.new"
    try:
        _download_verified(base + name, base + name + ".sha256sum", name, tmpzip)
        with zipfile.ZipFile(tmpzip) as zf, zf.open("deno") as src, open(tmpbin, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(tmpbin, 0o755)
        os.replace(tmpbin, TOOLS_DIR / "deno")
    finally:
        for f in (tmpzip, tmpbin):
            if os.path.exists(f):
                os.unlink(f)
    return TOOLS_DIR / "deno"


def _major(version):
    m = re.search(r"(\d+)\.\d+", version or "")
    return int(m.group(1)) if m else 0


def _find_js_runtime():
    """deno (>=2) vagy node (>=20) — ezeket tudja a yt-dlp YouTube-hoz."""
    for path in (TOOLS_DIR / "deno", shutil.which("deno"), HOME / ".deno/bin/deno", HOME / ".local/bin/deno"):
        if path and Path(path).is_file():
            v = _tool_version(path)
            if _major(v) >= DENO_MIN:
                return ("deno", str(path), v.split()[1] if v and len(v.split()) > 1 else v)
    for name in ("node", "nodejs"):
        path = shutil.which(name)
        if path:
            v = _tool_version(path)
            if _major((v or "").lstrip("v")) >= NODE_MIN:
                return ("node", path, v)
    return None


def _load_tools_state():
    try:
        return json.loads(TOOLS_STATE.read_text())
    except (OSError, ValueError):
        return {}


def _save_tools_state(state):
    try:
        CONF.mkdir(parents=True, exist_ok=True)
        TOOLS_STATE.write_text(json.dumps(state))
    except OSError:
        pass


def _latest_ytdlp_tag():
    req = urllib.request.Request(
        "https://github.com/yt-dlp/yt-dlp/releases/latest", headers={"User-Agent": "rtube"}, method="HEAD"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.geturl().rstrip("/").rsplit("/", 1)[-1]


def select_ytdlp(status=lambda _msg: None, allow_download=True):
    """Friss yt-dlp kiválasztása; ha nincs, letöltés a felhasználói könyvtárba."""
    best, best_ver = None, None
    for cand in _ytdlp_candidates():
        ver = _tool_version(cand)
        if not ver:
            continue
        if best is None or (_ytdlp_date(ver) or ()) > (_ytdlp_date(best_ver) or ()):
            best, best_ver = cand, ver
        if _ytdlp_fresh(ver) and cand != TOOLS_DIR / "yt-dlp":
            return cand, ver  # friss rendszer/felhasználói példány: azt használjuk
    managed = TOOLS_DIR / "yt-dlp"
    if allow_download:
        state = _load_tools_state()
        need = not managed.is_file() or best != managed
        if not need and time.time() - state.get("ytdlp_checked", 0) > YTDLP_CHECK_EVERY:
            try:
                tag = _latest_ytdlp_tag()
                state["ytdlp_checked"] = time.time()
                _save_tools_state(state)
                need = bool(tag) and tag != best_ver
            except (OSError, urllib.error.URLError, ValueError):
                pass
        if need:
            status(tr("yt-dlp frissítése…") if managed.is_file() else tr("yt-dlp letöltése…"))
            try:
                _fetch_ytdlp()
                ver = _tool_version(managed)
                state["ytdlp_checked"] = time.time()
                _save_tools_state(state)
                status(tr("yt-dlp kész: {version}", version=ver or "?"))
                return managed, ver
            except Exception:
                status(tr("A letöltés nem sikerült: {name}", name="yt-dlp"))
    return best, best_ver


def select_js(ytdlp_ver, status=lambda _msg: None, allow_download=True):
    if (_ytdlp_date(ytdlp_ver) or ()) < YTDLP_JS_MIN:
        return None
    js = _find_js_runtime()
    if js or not allow_download or not _arch():
        return js
    status(tr("deno letöltése (YouTube JS futtatókörnyezet)…"))
    try:
        path = _fetch_deno()
        v = _tool_version(path)
        status(tr("deno kész: {version}", version=(v or "?").split()[1] if v and len(v.split()) > 1 else (v or "?")))
        return ("deno", str(path), v)
    except Exception:
        status(tr("A letöltés nem sikerült: {name}", name="deno"))
        return None


def ensure_tools(status=lambda _msg: None, allow_download=True):
    """Háttérszálon fut induláskor: yt-dlp + JS futtatókörnyezet kiválasztása/letöltése."""
    with _TOOLS_LOCK:
        TOOLS["busy"] = True
        try:
            path, ver = select_ytdlp(status, allow_download)
            if path is not None:
                TOOLS["ytdlp"] = path
            TOOLS["js"] = select_js(ver, status, allow_download)
            TOOLS["ytdlp_version"] = ver
        finally:
            TOOLS["busy"] = False
    return TOOLS


def cava_version():
    out = _tool_version("cava", ("-v",)) or ""
    m = re.search(r"(\d+)\.(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else None


def cava_inputs():
    """cava 0.9+ natív pipewire, régebbi (pl. Ubuntu 24.04: 0.7.4) pulse; RTUBE_CAVA_INPUT felülír."""
    forced = os.environ.get("RTUBE_CAVA_INPUT", "").strip()
    if forced:
        return [forced]
    ver = cava_version()
    if ver is None:
        # Egyes disztró buildek (pl. Ubuntu) üres verziót írnak ki: a binárisban keresünk
        try:
            ver = (0, 9) if b"pipewire" in Path(shutil.which("cava")).read_bytes() else (0, 8)
        except (OSError, TypeError):
            ver = (0, 8)
    if ver >= (0, 9):
        return ["pipewire", "pulse"]
    return ["pulse", "pipewire"]


def stop_proc(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def run_cmd(cmd, timeout, holder, key, lock):
    with lock:
        stop_proc(holder.get(key))
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        holder[key] = proc
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_proc(proc)
        out, err = proc.communicate()
        return "", TIMEOUT_MSG, -1
    return out or "", err or "", proc.returncode


def migrate_conf():
    """A régi Hangzó beállítást átveszi, ha az Rtube-nak még nincs sajátja."""
    CONF.mkdir(parents=True, exist_ok=True)
    for name in ("state.json", "favorites.json"):
        dest = CONF / name
        src = OLD_CONF / name
        if dest.exists() or not src.is_file() or src.stat().st_size == 0:
            continue
        dest.write_bytes(src.read_bytes())


def parse_tracks(payload):
    tracks = []
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        video_id = entry.get("id")
        if not video_id:
            continue
        thumbs = entry.get("thumbnails") or []
        thumb = thumbs[-1].get("url") if thumbs and isinstance(thumbs[-1], dict) else None
        tracks.append(
            {
                "id": video_id,
                "title": entry.get("title") or video_id,
                "channel": entry.get("channel") or entry.get("uploader") or "",
                "duration": norm_duration(entry.get("duration")),
                "thumb": thumb,
            }
        )
    return tracks


def friendly_error(err):
    text = (err or "").strip()
    low = text.lower()
    if "not available" in low or "requested format" in low:
        return tr("Ehhez a videóhoz nincs lejátszható hang.")
    if "unavailable" in low or "private" in low:
        return tr("A videó nem elérhető.")
    if TIMEOUT_MSG.lower() in low or "lejárt" in low:
        return tr(TIMEOUT_MSG)
    line = text.splitlines()[-1] if text else tr("Ismeretlen hiba.")
    return line[:160]


def fetch_thumb(video_id, url):
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"{video_id}.jpg"
    if dest.exists() and dest.stat().st_size > 400:
        return dest
    candidates = []
    if url:
        candidates.append(url)
    candidates.append(f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg")
    candidates.append(f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg")
    for candidate in candidates:
        try:
            req = urllib.request.Request(candidate, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read(1_000_000)
            if len(data) < 400:
                continue
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            return dest
        except (OSError, urllib.error.URLError, ValueError):
            continue
    return None


def square_texture(path, size):
    buf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size * 2, size * 2, True)
    width, height = buf.get_width(), buf.get_height()
    side = min(width, height)
    cropped = buf.new_subpixbuf((width - side) // 2, (height - side) // 2, side, side)
    if side != size:
        cropped = cropped.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    ok, data = cropped.save_to_bufferv("png", [], [])
    if not ok:
        raise RuntimeError("borító")
    return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))


class BoundScroll(Gtk.ScrolledWindow):
    """A lista ne nője túl az ablakot: a sorok görgethetők maradnak."""

    def __init__(self):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_propagate_natural_height(False)
        self.set_vexpand(True)

    def do_measure(self, orientation, for_size):
        minimum, natural, _base_min, _base_nat = Gtk.ScrolledWindow.do_measure(
            self, orientation, for_size
        )
        if orientation == Gtk.Orientation.VERTICAL:
            return (120, 280, -1, -1)
        return (minimum, natural, -1, -1)


class Player:
    def __init__(self, on_phase, on_error, on_eos, on_buffer):
        Gst.init(None)
        self.on_phase = on_phase
        self.on_error = on_error
        self.on_eos = on_eos
        self.on_buffer = on_buffer
        self.phase = "idle"
        self.playbin = Gst.ElementFactory.make("playbin", "rtube")
        if self.playbin is None:
            raise RuntimeError(tr("A GStreamer playbin nem elérhető."))
        video_sink = Gst.ElementFactory.make("fakesink", "vsink")
        if video_sink is not None:
            video_sink.set_property("sync", False)
            self.playbin.set_property("video-sink", video_sink)
        try:
            # audio + soft volume + buffering, video nélkül
            self.playbin.set_property("flags", (1 << 1) | (1 << 4) | (1 << 8))
        except (TypeError, ValueError):
            pass
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._on_message)

    def load(self, url):
        self.playbin.set_state(Gst.State.NULL)
        self.playbin.set_property("uri", url)
        self.playbin.set_state(Gst.State.PLAYING)

    def play(self):
        self.playbin.set_state(Gst.State.PLAYING)

    def pause(self):
        self.playbin.set_state(Gst.State.PAUSED)

    def seek(self, seconds):
        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(max(0, seconds) * Gst.SECOND),
        )

    def set_volume(self, percent):
        self.playbin.set_property("volume", max(0.0, min(100.0, percent)) / 100.0)

    def times(self):
        ok_pos, pos = self.playbin.query_position(Gst.Format.TIME)
        ok_dur, dur = self.playbin.query_duration(Gst.Format.TIME)
        pos_s = pos / Gst.SECOND if ok_pos else 0
        dur_s = dur / Gst.SECOND if ok_dur else 0
        return pos_s, dur_s

    def close(self):
        self.playbin.set_state(Gst.State.NULL)
        try:
            self.bus.remove_signal_watch()
        except (AttributeError, RuntimeError):
            pass

    def _on_message(self, _bus, msg):
        kind = msg.type
        if kind == Gst.MessageType.ERROR:
            err, _dbg = msg.parse_error()
            self.playbin.set_state(Gst.State.NULL)
            self.phase = "idle"
            self.on_error(err.message if err else tr("hiba"))
        elif kind == Gst.MessageType.EOS:
            self.phase = "ended"
            self.on_eos()
        elif kind == Gst.MessageType.BUFFERING:
            self.on_buffer(msg.parse_buffering())
        elif kind == Gst.MessageType.STATE_CHANGED and msg.src == self.playbin:
            _old, new, _pending = msg.parse_state_changed()
            if new == Gst.State.PLAYING:
                self.phase = "playing"
                self.on_phase("playing")
            elif new == Gst.State.PAUSED and self.phase != "ended":
                self.phase = "paused"
                self.on_phase("paused")


class Visualizer(Gtk.DrawingArea):
    """Kis cava spektrum a lejátszóba."""

    BARS = 40

    def __init__(self, winamp=False):
        super().__init__()
        self.winamp = winamp
        self.levels = [0] * self.BARS
        self.proc = None
        self.method = None
        self.stopped = False
        self.set_content_height(34 if winamp else 30)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        self._start()

    def _start(self):
        if not shutil.which("cava"):
            return
        threading.Thread(target=self._launch, daemon=True).start()

    def _launch(self):
        cfg = CONF / "cava.conf"
        for method in cava_inputs():
            try:
                CONF.mkdir(parents=True, exist_ok=True)
                cfg.write_text(
                    "[general]\n"
                    f"bars = {self.BARS}\n"
                    "framerate = 30\n"
                    "[input]\n"
                    f"method = {method}\n"
                    "source = auto\n"
                    "[output]\n"
                    "method = raw\n"
                    "raw_target = /dev/stdout\n"
                    "data_format = ascii\n"
                    "ascii_max_range = 100\n"
                    "bar_delimiter = 59\n"
                    "frame_delimiter = 10\n"
                )
                proc = subprocess.Popen(
                    ["cava", "-p", str(cfg)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
            except Exception:
                continue
            try:
                proc.wait(timeout=1.5)  # azonnal kilép, ha ez a bemenet nem megy
            except subprocess.TimeoutExpired:
                if self.stopped:
                    proc.terminate()
                    return
                self.proc = proc
                self.method = method
                self._reader()
                return

    def _reader(self):
        proc = self.proc
        for line in proc.stdout:
            vals = []
            for part in line.strip().split(";"):
                if part:
                    try:
                        vals.append(int(part))
                    except ValueError:
                        pass
            if vals:
                GLib.idle_add(self._update, vals)

    def _update(self, vals):
        self.levels = vals[: self.BARS]
        self.queue_draw()
        return False

    def _draw(self, _area, cr, width, height):
        n = max(len(self.levels), 1)
        gap = 2
        bw = max((width - gap * (n - 1)) / n, 1)
        if self.winamp:
            cr.set_source_rgb(0, 0, 0)
            cr.rectangle(0, 0, width, height)
            cr.fill()
        for i, lvl in enumerate(self.levels):
            h = max(height * lvl / 100.0, 1)
            x = i * (bw + gap)
            if self.winamp:
                # Winamp: zöldből sárgán át pirosba, kis "pixel" szegmensekkel
                seg = 3
                y = height
                while y > height - h:
                    frac = (height - y) / height
                    if frac < 0.5:
                        cr.set_source_rgb(frac * 2 * 0.9, 0.85, 0.0)
                    else:
                        cr.set_source_rgb(0.9, 0.85 * (1 - (frac - 0.5) * 2), 0.0)
                    cr.rectangle(x, y - seg + 1, bw, seg - 1)
                    cr.fill()
                    y -= seg
            else:
                cr.set_source_rgba(0.23, 0.53, 1.0, 0.85)
                cr.rectangle(x, height - h, bw, h)
                cr.fill()

    def stop(self):
        self.stopped = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass


class Rtube(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            # RTUBE_NON_UNIQUE=1: külön példány (teszteléshez, ha már fut egy Rtube)
            flags=Gio.ApplicationFlags.NON_UNIQUE
            if os.environ.get("RTUBE_NON_UNIQUE") == "1"
            else Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.win = None
        self.connect("activate", self.on_activate)

    def on_activate(self, _app):
        if self.win is not None:
            self.win.present()
            return
        migrate_conf()
        try:
            gi.require_version("GdkX11", "4.0")
            from gi.repository import GdkX11

            display = Gdk.Display.get_default()
            if isinstance(display, GdkX11.X11Display):
                GdkX11.X11Display.set_program_class(display, APP_ID)
        except (ImportError, ValueError, AttributeError, TypeError):
            pass
        Gtk.Window.set_default_icon_name(APP_ID)
        self.palette = load_palette()
        self.radius = load_radius()
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.procs = {"search": None, "resolve": None}
        self.proc_lock = threading.Lock()
        self.closing = False
        self.gen = 0
        self.play_gen = 0
        self.mode = "results"
        self.last_results = []
        self.current = None
        self.stream_url = None
        self.at_end = False
        self.fav_items = self._load_favs()
        self.fav_ids = {item["id"] for item in self.fav_items}
        self.volume = self._load_volume()
        self._search_src = 0
        self._seek_src = 0
        self._scrub = False
        self._ui = False
        self._build()
        self.player = Player(self.on_phase, self.on_error, self.on_eos, self.on_buffer)
        self.player.set_volume(self.volume)
        GLib.timeout_add(250, self.tick)
        self.win.present()
        threading.Thread(
            target=ensure_tools,
            args=(lambda msg: GLib.idle_add(self._tool_status, msg),),
            daemon=True,
        ).start()

    def _tool_status(self, msg):
        if not self.closing:
            self.set_status(msg)
        return False

    def _build(self):
        provider = Gtk.CssProvider()
        css = build_css(self.palette, self.radius)
        if SKIN == "winamp":
            css += WINAMP_CSS
        if MODERN:
            css += MODERN_CSS
            load_css(provider, css)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            self._build_modern()
            return
        load_css(provider, css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        self.win = Gtk.ApplicationWindow(application=self, title="Rtube")
        self.win.set_default_size(960, 680)
        self.win.set_size_request(720, 480)
        self.win.connect("close-request", self.on_close)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        brand = Gtk.Label(label="Rtube")
        brand.add_css_class("brand")
        brand.set_valign(Gtk.Align.CENTER)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(tr("YouTube keresés…"))
        self.entry.add_css_class("search")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self.search_now)
        self.entry.connect("changed", self.search_later)
        search_btn = Gtk.Button(label=tr("Keresés"))
        search_btn.add_css_class("accent")
        search_btn.connect("clicked", self.search_now)
        self.fav_btn = Gtk.Button(label=tr("Kedvencek"))
        self.fav_btn.connect("clicked", self.on_favs)
        top.append(brand)
        top.append(self.entry)
        top.append(search_btn)
        top.append(self.fav_btn)

        self.status = Gtk.Label(label=tr("Keress egy számra, vagy nyisd meg a kedvenceket."), xalign=0)
        self.status.add_css_class("dim")
        self.status.set_ellipsize(Pango.EllipsizeMode.END)

        list_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        list_card.add_css_class("panel")
        list_card.set_vexpand(True)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.connect("row-activated", self.on_row)
        scroll = BoundScroll()
        scroll.set_child(self.list)
        self.empty = Gtk.Label(label=tr("Keress egy számra."))
        self.empty.add_css_class("dim")
        self.empty.set_wrap(True)
        self.empty.set_vexpand(True)
        self.empty.set_valign(Gtk.Align.CENTER)
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.add_named(scroll, "list")
        self.stack.add_named(self.empty, "empty")
        self.stack.set_visible_child_name("empty")
        list_card.append(self.stack)

        player_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        player_card.add_css_class("panel")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        np_frame, self.np_pic = self._cover(96)
        meta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        meta.set_hexpand(True)
        meta.set_valign(Gtk.Align.CENTER)
        self.np_title = Gtk.Label(label=tr("Nincs lejátszás"), xalign=0)
        self.np_title.add_css_class("title")
        self.np_title.set_hexpand(True)
        self.np_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.np_sub = Gtk.Label(label=tr("Válassz egy számot"), xalign=0)
        self.np_sub.add_css_class("dim")
        self.np_sub.set_hexpand(True)
        self.np_sub.set_ellipsize(Pango.EllipsizeMode.END)
        meta.append(self.np_title)
        meta.append(self.np_sub)
        self.vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol.set_draw_value(False)
        self.vol.set_tooltip_text(tr("Hangerő"))
        self.vol.set_size_request(120, -1)
        self.vol.set_valign(Gtk.Align.CENTER)
        self._ui = True
        self.vol.set_value(self.volume)
        self._ui = False
        self.vol.connect("value-changed", self.on_volume)

        # ---- MPV GOMB HOZZÁADÁSA ----
        self.video_btn = Gtk.Button(label="🎬")
        self.video_btn.add_css_class("icon-btn")
        self.video_btn.set_tooltip_text(tr("Megnyitás videóként (mpv)"))
        self.video_btn.set_valign(Gtk.Align.CENTER)
        self.video_btn.set_sensitive(False)
        self.video_btn.connect("clicked", self.on_video)

        self.np_heart = Gtk.Button(label="♡")
        self.np_heart.add_css_class("icon-btn")
        self.np_heart.set_valign(Gtk.Align.CENTER)
        self.np_heart.connect("clicked", self.on_np_heart)
        
        self.play_btn = Gtk.Button(label="▶")
        self.play_btn.add_css_class("play")
        self.play_btn.add_css_class("player-btn")
        self.play_btn.set_valign(Gtk.Align.CENTER)
        self.play_btn.set_sensitive(False)
        self.play_btn.connect("clicked", self.on_play)
        
        row.append(np_frame)
        row.append(meta)
        row.append(self.vol)
        row.append(self.video_btn)
        row.append(self.np_heart)
        row.append(self.play_btn)

        seek_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pos_label = Gtk.Label(label="0:00")
        self.pos_label.add_css_class("dim")
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.connect("value-changed", self.on_seek)
        self.dur_label = Gtk.Label(label="0:00")
        self.dur_label.add_css_class("dim")
        seek_row.append(self.pos_label)
        seek_row.append(self.scale)
        seek_row.append(self.dur_label)

        player_card.append(row)
        self.viz = Visualizer(winamp=SKIN == "winamp")
        player_card.append(self.viz)
        player_card.append(seek_row)
        if SKIN == "winamp":
            # Winamp elrendezés: felül a lejátszó, alatta a kereső és a lista
            root.append(player_card)
            root.append(top)
            root.append(self.status)
            root.append(list_card)
        else:
            root.append(top)
            root.append(self.status)
            root.append(list_card)
            root.append(player_card)
        self.win.set_child(root)

    # ---- MODERN SKIN (RTUBE_SKIN=modern) ----
    def _icon_button(self, icon, text, css_classes):
        btn = Gtk.Button()
        for cls in css_classes:
            btn.add_css_class(cls)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        box.set_halign(Gtk.Align.CENTER)
        img = Gtk.Image.new_from_icon_name(icon)
        img.set_pixel_size(15)
        box.append(img)
        box.append(Gtk.Label(label=text))
        btn.set_child(box)
        return btn

    def _build_modern(self):
        self.heart_icons = ensure_heart_icons()
        self.viz = None
        self.win = Gtk.ApplicationWindow(application=self, title="Rtube")
        self.win.set_default_size(960, 680)
        self.win.set_size_request(760, 600)
        self.win.connect("close-request", self.on_close)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        root.set_margin_top(16)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)

        # Fejléc: logó + név, kereső, Találatok/Kedvencek kapcsoló
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        brand = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        brand.set_valign(Gtk.Align.CENTER)
        logo = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        logo.set_pixel_size(12)
        logo.add_css_class("logo")
        brand_label = Gtk.Label(label="Rtube")
        brand_label.add_css_class("brand")
        brand.append(logo)
        brand.append(brand_label)
        brand.set_margin_end(6)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(T("Keresés a YouTube-on…", "Search YouTube…"))
        self.entry.add_css_class("search")
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, "system-search-symbolic")
        self.entry.set_hexpand(True)
        self.entry.set_valign(Gtk.Align.CENTER)
        self.entry.connect("activate", self._on_modern_activate)
        self.entry.connect("changed", self.search_later)
        seg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        seg.add_css_class("seg")
        seg.set_valign(Gtk.Align.CENTER)
        self.results_btn = self._icon_button(
            "view-list-symbolic", T("Találatok", "Results"), ["active-view"]
        )
        self.results_btn.connect("clicked", lambda *_a: self.mode == "favs" and self.on_favs())
        heart_icon = "rtube-heart-outline-symbolic" if self.heart_icons else "non-starred-symbolic"
        self.fav_btn = self._icon_button(heart_icon, T("Kedvencek", "Favorites"), [])
        self.fav_btn.connect("clicked", lambda *_a: self.mode != "favs" and self.on_favs())
        seg.append(self.results_btn)
        seg.append(self.fav_btn)
        self.compact_btn = Gtk.Button()
        self.compact_btn.set_icon_name(
            "rtube-compact-symbolic" if self.heart_icons else "view-restore-symbolic"
        )
        self.compact_btn.add_css_class("compact-btn")
        self.compact_btn.set_valign(Gtk.Align.CENTER)
        self.compact_btn.set_tooltip_text(T("Kompakt nézet", "Compact view"))
        self.compact_btn.connect("clicked", lambda *_a: self._set_view("compact"))
        top.append(brand)
        top.append(self.entry)
        top.append(seg)
        top.append(self.compact_btn)
        self.m_brand_label = brand_label
        self.m_seg = seg

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        body.set_vexpand(True)

        # Bal oldal: lista kártya
        list_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        list_card.add_css_class("panel")
        list_card.set_hexpand(True)
        list_card.set_vexpand(True)
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head.set_margin_start(10)
        head.set_margin_end(10)
        head.set_margin_top(2)
        head.set_margin_bottom(4)
        self.list_title = Gtk.Label(label=T("Találatok", "Results"), xalign=0)
        self.list_title.add_css_class("list-head")
        self.list_title.set_hexpand(True)
        self.list_count = Gtk.Label(label="", xalign=1)
        self.list_count.add_css_class("time")
        head.append(self.list_title)
        head.append(self.list_count)
        list_card.append(head)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.connect("row-activated", self.on_row)
        scroll = BoundScroll()
        scroll.set_child(self.list)
        self.empty = Gtk.Label(label=T("Keress egy számra.", "Search for a song."))
        self.empty.add_css_class("dim")
        self.empty.set_wrap(True)
        self.empty.set_vexpand(True)
        self.empty.set_valign(Gtk.Align.CENTER)
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.add_named(scroll, "list")
        self.stack.add_named(self.empty, "empty")
        self.stack.set_visible_child_name("empty")
        list_card.append(self.stack)

        # Jobb oldal: most szól kártya (332 px)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("panel")
        card.add_css_class("np-card")
        card.set_size_request(332, -1)
        card.set_hexpand(False)
        np_label = Gtk.Label(label=T("MOST SZÓL", "NOW PLAYING"), xalign=0)
        np_label.add_css_class("np-label")
        np_label.set_hexpand(True)
        np_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        np_head.set_size_request(-1, 24)
        np_head.append(np_label)
        self.full_btn = self._icon_button("view-list-symbolic", T("Lista", "List"), ["np-head-btn"])
        self.full_btn.set_tooltip_text(T("Teljes nézet", "Full view"))
        self.full_btn.set_valign(Gtk.Align.CENTER)
        self.full_btn.connect("clicked", lambda *_a: self._set_view("full"))
        np_head.append(self.full_btn)
        np_frame, self.np_pic = self._cover(256)
        np_frame.add_css_class("np-cover")
        np_frame.set_margin_top(18)
        self.np_sub = Gtk.Label(label=T("Válassz egy számot", "Pick a song"))
        self.np_sub.add_css_class("np-artist")
        self.np_sub.set_ellipsize(Pango.EllipsizeMode.END)
        self.np_sub.set_max_width_chars(1)
        self.np_sub.set_hexpand(True)
        self.np_sub.set_margin_top(22)
        self.np_title = Gtk.Label(label=T("Nincs lejátszás", "Nothing playing"))
        self.np_title.add_css_class("np-title")
        self.np_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.np_title.set_max_width_chars(1)
        self.np_title.set_hexpand(True)
        self.np_title.set_margin_top(4)

        seek_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        seek_row.set_margin_top(16)
        self.pos_label = Gtk.Label(label="0:00")
        self.pos_label.add_css_class("time")
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.scale.set_draw_value(False)
        self.scale.set_hexpand(True)
        self.scale.add_css_class("seek")
        self.scale.connect("value-changed", self.on_seek)
        self.dur_label = Gtk.Label(label="0:00")
        self.dur_label.add_css_class("time")
        seek_row.append(self.pos_label)
        seek_row.append(self.scale)
        seek_row.append(self.dur_label)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls.set_margin_top(14)
        self.video_btn = Gtk.Button()
        self.video_btn.set_icon_name(
            "rtube-video-symbolic" if self.heart_icons else "camera-video-symbolic"
        )
        self.video_btn.add_css_class("np-icon")
        self.video_btn.set_tooltip_text(T("Megnyitás videóként (mpv)", "Open as video (mpv)"))
        self.video_btn.set_valign(Gtk.Align.CENTER)
        self.video_btn.set_sensitive(False)
        self.video_btn.connect("clicked", self.on_video)
        self.play_btn = Gtk.Button()
        self.play_btn.add_css_class("np-play")
        self.play_btn.set_valign(Gtk.Align.CENTER)
        self.play_btn.set_tooltip_text(T("Lejátszás / szünet", "Play / pause"))
        self.play_btn.set_sensitive(False)
        self.play_btn.connect("clicked", self.on_play)
        self._set_play_icon(False)
        self.np_heart = Gtk.Button()
        self.np_heart.add_css_class("np-icon")
        self.np_heart.set_valign(Gtk.Align.CENTER)
        self.np_heart.set_tooltip_text(T("Kedvencekhez adás", "Add to favorites"))
        self.np_heart.connect("clicked", self.on_np_heart)
        self._set_heart(self.np_heart, False)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.vol_icon = Gtk.Image.new_from_icon_name("audio-volume-high-symbolic")
        self.vol_icon.add_css_class("vol-icon")
        self.vol_icon.set_pixel_size(17)
        self.vol_icon.set_valign(Gtk.Align.CENTER)
        self.vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol.add_css_class("vol")
        self.vol.set_draw_value(False)
        self.vol.set_tooltip_text(T("Hangerő", "Volume"))
        self.vol.set_size_request(72, -1)
        self.vol.set_valign(Gtk.Align.CENTER)
        self._ui = True
        self.vol.set_value(self.volume)
        self._ui = False
        self._sync_vol_icon(self.volume)
        self.vol.connect("value-changed", self.on_volume)
        controls.append(self.video_btn)
        controls.append(self.play_btn)
        controls.append(self.np_heart)
        controls.append(spacer)
        controls.append(self.vol_icon)
        controls.append(self.vol)

        filler = Gtk.Box()
        filler.set_vexpand(True)
        self.status = Gtk.Label(
            label=T("Keress egy számra, vagy nyisd meg a kedvenceket.", "Search for a song, or open your favorites.")
        )
        self.status.add_css_class("status-line")
        self.status.set_ellipsize(Pango.EllipsizeMode.END)
        self.status.set_max_width_chars(1)
        self.status.set_hexpand(True)
        self.status.set_margin_top(12)

        card.append(np_head)
        card.append(np_frame)
        card.append(self.np_sub)
        card.append(self.np_title)
        card.append(seek_row)
        card.append(controls)
        card.append(filler)
        card.append(self.status)

        # Kompakt nézet: „Következő” sáv a kártya alatt
        self.upnext = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.upnext.add_css_class("panel")
        self.upnext.add_css_class("upnext")
        up_main = Gtk.Button()
        up_main.add_css_class("upnext-main")
        up_main.set_hexpand(True)
        up_main.set_tooltip_text(T("Következő lejátszása", "Play next"))
        up_main.connect("clicked", self._play_upnext)
        up_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        up_frame, self.up_pic = self._cover(40)
        up_texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        up_texts.set_valign(Gtk.Align.CENTER)
        up_texts.set_hexpand(True)
        up_label = Gtk.Label(label=T("KÖVETKEZŐ", "UP NEXT"), xalign=0)
        up_label.add_css_class("upnext-label")
        self.up_title = Gtk.Label(label="", xalign=0)
        self.up_title.add_css_class("upnext-title")
        self.up_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.up_title.set_max_width_chars(1)
        self.up_title.set_hexpand(True)
        up_texts.append(up_label)
        up_texts.append(self.up_title)
        up_box.append(up_frame)
        up_box.append(up_texts)
        up_main.set_child(up_box)
        up_btn = Gtk.Button()
        up_btn.set_icon_name("go-up-symbolic")
        up_btn.add_css_class("upnext-up")
        up_btn.set_valign(Gtk.Align.CENTER)
        up_btn.set_tooltip_text(T("Teljes nézet", "Full view"))
        up_btn.connect("clicked", lambda *_a: self._set_view("full"))
        self.upnext.append(up_main)
        self.upnext.append(up_btn)
        self.upnext_track = None

        body.append(list_card)
        body.append(card)
        root.append(top)
        root.append(body)
        root.append(self.upnext)
        self.win.set_child(root)
        self.m_root = root
        self.list_card = list_card
        self.np_card = card
        self.np_frame = np_frame
        self.np_filler = filler
        self.view = "full"
        self._full_size = (960, 680)
        self._set_view(self._load_view(), initial=True)

    # ---- MODERN: teljes / kompakt nézet ----
    def _set_view(self, view, initial=False):
        compact = view == "compact"
        if not initial and view == self.view:
            return
        if compact and not initial and self.win.get_width() > 0:
            self._full_size = (max(760, self.win.get_width()), max(600, self.win.get_height()))
        self.view = "compact" if compact else "full"
        self.list_card.set_visible(not compact)
        self.m_seg.set_visible(not compact)
        self.m_brand_label.set_visible(not compact)
        self.compact_btn.set_visible(not compact)
        self.full_btn.set_visible(compact)
        self.np_card.set_hexpand(compact)
        self.np_card.set_size_request(-1 if compact else 332, -1)
        # Csempézett (tiled) ablakban is keskeny, középre igazított oszlop maradjon
        self.m_root.set_halign(Gtk.Align.CENTER if compact else Gtk.Align.FILL)
        self.m_root.set_size_request(340 if compact else -1, -1)
        cover = 240 if compact else 256
        self.np_frame.set_size_request(cover, cover)
        self.np_pic.set_size_request(cover, cover)
        self._update_upnext()
        if compact:
            self.win.set_size_request(340, 560)
            self.win.set_default_size(380, 720)
        else:
            self.win.set_size_request(760, 600)
            self.win.set_default_size(*self._full_size)
        if not initial:
            self._save_state(modern_view=self.view)
            # Hyprland lebegő ablakoknál a set_default_size nem mindig elég
            GLib.idle_add(self._hypr_resize)

    def _hypr_resize(self):
        # Csak Hyprlandon (lebegő ablak): máshol a GTK set_default_size elég, csendben kihagyjuk
        if (
            self.closing
            or not os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
            or not shutil.which("hyprctl")
        ):
            return False
        w, h = (380, 720) if self.view == "compact" else self._full_size
        app_id = self.get_application_id()

        def work():
            try:
                out = subprocess.run(
                    ["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=3
                ).stdout
                pid = os.getpid()
                for c in json.loads(out or "[]"):
                    if c.get("pid") == pid and c.get("class") == app_id:
                        if c.get("floating") and tuple(c.get("size") or ()) != (w, h):
                            addr = c["address"]
                            # Hyprland 0.56 (Lua): dispatcher objektum; régebbi: string szintaxis
                            res = subprocess.run(
                                ["hyprctl", "dispatch",
                                 f'hl.dsp.window.resize({{ x = {w}, y = {h}, window = "address:{addr}" }})'],
                                capture_output=True, text=True, timeout=3,
                            )
                            if res.stdout.strip() != "ok":
                                subprocess.run(
                                    ["hyprctl", "dispatch", "resizewindowpixel",
                                     f"exact {w} {h},address:{addr}"],
                                    capture_output=True, timeout=3,
                                )
                        break
            except Exception:
                pass

        self.pool.submit(work)
        return False

    def _on_modern_activate(self, *_args):
        if self.view == "compact" and len(self.entry.get_text().strip()) >= 2:
            self._set_view("full")
        self.search_now()

    def _update_upnext(self):
        if not MODERN or not hasattr(self, "upnext"):
            return
        rows = []
        index = 0
        while (row := self.list.get_row_at_index(index)) is not None:
            rows.append(row.track)
            index += 1
        current_id = self.current["id"] if self.current else None
        nxt = None
        ids = [t["id"] for t in rows]
        if current_id in ids:
            pos = ids.index(current_id)
            if pos + 1 < len(rows):
                nxt = rows[pos + 1]
        else:
            nxt = next((t for t in rows if t["id"] != current_id), None)
        self.upnext_track = nxt
        if nxt is not None:
            channel = nxt.get("channel") or ""
            text = nxt.get("title") or nxt["id"]
            self.up_title.set_text(f"{text} – {channel}" if channel else text)
            if getattr(self.up_pic, "thumb_id", None) != nxt["id"]:
                self.queue_thumb(nxt, self.up_pic)
        self.upnext.set_visible(self.view == "compact" and nxt is not None)

    def _play_upnext(self, *_args):
        if self.upnext_track is not None:
            self.play(self.upnext_track)

    def _load_view(self):
        try:
            value = json.loads(STATE_PATH.read_text()).get("modern_view", "full")
        except (OSError, json.JSONDecodeError, AttributeError):
            return "full"
        return "compact" if value == "compact" else "full"

    def _set_play_icon(self, playing):
        if MODERN:
            own = getattr(self, "heart_icons", False)
            if playing:
                name = "rtube-pause-symbolic" if own else "media-playback-pause-symbolic"
            else:
                name = "rtube-play-symbolic" if own else "media-playback-start-symbolic"
            self.play_btn.set_icon_name(name)
        else:
            self.play_btn.set_label("⏸" if playing else "▶")

    def _set_heart(self, button, on):
        if MODERN and getattr(self, "heart_icons", False):
            button.set_icon_name(
                "rtube-heart-filled-symbolic" if on else "rtube-heart-outline-symbolic"
            )
        else:
            button.set_label("♥" if on else "♡")
        if on:
            button.add_css_class("fav")
        else:
            button.remove_css_class("fav")

    def _sync_seg(self):
        if not MODERN:
            return
        favs = self.mode == "favs"
        if favs:
            self.results_btn.remove_css_class("active-view")
            self.fav_btn.add_css_class("active-view")
        else:
            self.results_btn.add_css_class("active-view")
            self.fav_btn.remove_css_class("active-view")
        self.list_title.set_text(T("Kedvencek", "Favorites") if favs else T("Találatok", "Results"))

    def _sync_vol_icon(self, value):
        if not MODERN:
            return
        if value <= 0:
            name = "audio-volume-muted-symbolic"
        elif value < 34:
            name = "audio-volume-low-symbolic"
        elif value < 67:
            name = "audio-volume-medium-symbolic"
        else:
            name = "audio-volume-high-symbolic"
        self.vol_icon.set_from_icon_name(name)

    def _np_subtitle(self, track):
        if MODERN:
            return track.get("channel") or "YouTube"
        return subtitle(track)

    def _cover(self, size):
        frame = Gtk.Box()
        frame.add_css_class("cover-frame")
        frame.set_size_request(size, size)
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)
        frame.set_hexpand(False)
        frame.set_overflow(Gtk.Overflow.HIDDEN)
        pic = Gtk.Picture()
        pic.set_size_request(size, size)
        pic.set_hexpand(False)
        pic.set_vexpand(False)
        pic.set_content_fit(Gtk.ContentFit.COVER)
        pic.set_can_shrink(True)
        pic.thumb_size = size
        frame.append(pic)
        return frame, pic

    def set_status(self, text):
        self.status.set_text(text)

    def search_later(self, *_args):
        if self._search_src:
            GLib.source_remove(self._search_src)
        self._search_src = GLib.timeout_add(450, self._fire_search)

    def _fire_search(self):
        self._search_src = 0
        self.search_now()
        return False

    def search_now(self, *_args):
        if self._search_src:
            GLib.source_remove(self._search_src)
            self._search_src = 0
        query = self.entry.get_text().strip()
        if len(query) < 2:
            return False
        if TOOLS["busy"] and TOOLS["ytdlp"] is None:
            self.set_status(tr("A yt-dlp még töltődik…"))
            return False
        if not ytdlp_bin().is_file():
            self.set_status(tr("Hiányzik a yt-dlp."))
            return False
        self.mode = "results"
        self.fav_btn.remove_css_class("active-view")
        self._sync_seg()
        self.gen += 1
        gen = self.gen
        self.set_status(tr("Keresés…"))
        self.pool.submit(self._search_worker, query, gen)
        return False

    def _search_worker(self, query, gen):
        out, err, code = run_cmd(
            [
                str(ytdlp_bin()),
                *ytdlp_extra_args(),
                "--flat-playlist",
                "--dump-single-json",
                "--no-warnings",
                "--skip-download",
                f"ytsearch15:{query}",
            ],
            35,
            self.procs,
            "search",
            self.proc_lock,
        )
        tracks, message = [], None
        if code == 0 and out.strip():
            try:
                tracks = parse_tracks(json.loads(out))
            except json.JSONDecodeError:
                message = tr("A találatokat nem sikerült olvasni.")
        elif code is not None and code < 0 and not (err or "").strip():
            return
        else:
            message = friendly_error(err)
        GLib.idle_add(self._apply_search, gen, tracks, message)

    def _apply_search(self, gen, tracks, message):
        if self.closing or gen != self.gen:
            return False
        self.last_results = tracks
        if message and not tracks:
            self.render(tracks, tr("A keresés nem sikerült."))
            self.set_status(message)
        else:
            self.render(tracks, tr("Nincs találat."))
            self.set_status(tr("Nincs találat.") if not tracks else tr("{n} találat", n=len(tracks)))
        return False

    def on_favs(self, *_args):
        if self.mode == "favs":
            self.mode = "results"
            self.fav_btn.remove_css_class("active-view")
            self.render(self.last_results, tr("Keress egy számra."))
            self._sync_seg()
            return
        self.mode = "favs"
        self.fav_btn.add_css_class("active-view")
        self.render(self.fav_items, tr("Még nincs kedvenc. A szív menti a számot."))
        self._sync_seg()

    def render(self, tracks, empty_text):
        while (row := self.list.get_row_at_index(0)) is not None:
            self.list.remove(row)
        if not tracks:
            self.empty.set_text(empty_text)
            self.stack.set_visible_child_name("empty")
        else:
            for track in tracks:
                self.list.append(self.make_row(track))
            self.stack.set_visible_child_name("list")
        if MODERN:
            self.list_count.set_text(
                T(f"{len(tracks)} szám", f"{len(tracks)} songs") if tracks else ""
            )
        self.mark_playing()

    def make_row(self, track):
        row = Gtk.ListBoxRow()
        row.track = track
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        frame, pic = self._cover(44 if MODERN else 72)
        self.queue_thumb(track, pic)
        texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        texts.set_hexpand(True)
        texts.set_valign(Gtk.Align.CENTER)
        title = Gtk.Label(label=track["title"], xalign=0)
        title.add_css_class("title")
        title.set_hexpand(True)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        sub = Gtk.Label(label=subtitle(track), xalign=0)
        sub.add_css_class("dim")
        sub.set_hexpand(True)
        sub.set_ellipsize(Pango.EllipsizeMode.END)
        texts.append(title)
        texts.append(sub)
        heart = Gtk.Button()
        heart.add_css_class("heart")
        self._set_heart(heart, track["id"] in self.fav_ids)
        heart.set_valign(Gtk.Align.CENTER)
        heart.connect("clicked", lambda _b, item=track: self.toggle_fav(item))
        row.heart = heart
        box.append(frame)
        box.append(texts)
        if MODERN:
            sub.set_text(track.get("channel") or "YouTube")
            dur = Gtk.Label(label=fmt_time(track.get("duration")), xalign=1)
            dur.add_css_class("time")
            box.append(dur)
        box.append(heart)
        row.set_child(box)
        return row

    def on_row(self, _list, row):
        self.play(row.track)

    def queue_thumb(self, track, picture):
        video_id = track["id"]
        picture.thumb_id = video_id
        size = picture.thumb_size

        def work():
            path = fetch_thumb(video_id, track.get("thumb"))

            def apply():
                if self.closing or getattr(picture, "thumb_id", None) != video_id:
                    return False
                if picture.get_parent() is None:
                    return False
                if path is None:
                    return False
                try:
                    picture.set_paintable(square_texture(path, size))
                except (GLib.Error, OSError, RuntimeError):
                    pass
                return False

            GLib.idle_add(apply)

        self.pool.submit(work)

    def play(self, track):
        if TOOLS["busy"] and TOOLS["ytdlp"] is None:
            self.set_status(tr("A yt-dlp még töltődik…"))
            return
        if not ytdlp_bin().is_file():
            self.set_status(tr("Hiányzik a yt-dlp."))
            return
        self.current = {
            "id": track["id"],
            "title": track.get("title") or track["id"],
            "channel": track.get("channel") or "",
            "duration": track.get("duration"),
        }
        self.at_end = False
        self.stream_url = None
        self.play_btn.set_sensitive(True)
        self.video_btn.set_sensitive(True)
        self.np_title.set_text(self.current["title"])
        self.np_sub.set_text(self._np_subtitle(self.current))
        self.queue_thumb(self.current, self.np_pic)
        self.sync_hearts()
        self.mark_playing()
        self.set_status(tr("Hangfolyam betöltése…"))
        self._ui = True
        self.scale.set_range(0, 1)
        self.scale.set_value(0)
        self._ui = False
        self.pos_label.set_text("0:00")
        self.dur_label.set_text(fmt_time(self.current.get("duration")))
        self.play_gen += 1
        gen = self.play_gen
        self.pool.submit(self._resolve_worker, self.current["id"], gen)

    def _resolve_worker(self, video_id, gen):
        out, err, code = run_cmd(
            [
                str(ytdlp_bin()),
                *ytdlp_extra_args(),
                "-f",
                AUDIO_FORMAT,
                "-g",
                "--no-playlist",
                "--no-warnings",
                f"https://www.youtube.com/watch?v={video_id}",
            ],
            40,
            self.procs,
            "resolve",
            self.proc_lock,
        )
        url = next((line.strip() for line in out.splitlines() if line.startswith("http")), "")
        if code is not None and code < 0 and not (err or "").strip():
            return
        message = None if code == 0 and url else friendly_error(err)
        GLib.idle_add(self._apply_stream, gen, url, message)

    def _apply_stream(self, gen, url, message):
        if self.closing or gen != self.play_gen:
            return False
        if message or not url:
            self.set_status(message or tr("Nincs hangfolyam."))
            return False
        self.stream_url = url
        self.player.set_volume(self.vol.get_value())
        self.player.load(url)
        return False

    def on_play(self, *_args):
        if self.current is None:
            return
        if self.at_end and self.stream_url:
            self.at_end = False
            self.player.set_volume(self.vol.get_value())
            self.player.load(self.stream_url)
            return
        if self.player.phase == "playing":
            self.player.pause()
        elif self.player.phase == "paused":
            self.player.play()
        else:
            self.play(self.current)

    def on_phase(self, phase):
        if self.closing:
            return
        self._set_play_icon(phase == "playing")
        if phase == "playing" and not self.at_end:
            self.set_status(tr("Szól"))
        elif phase == "paused":
            self.set_status(tr("Szünet"))

    def on_error(self, message):
        if self.closing:
            return
        self._set_play_icon(False)
        self.status.set_tooltip_text(message or "")
        self.set_status(tr("Lejátszás sikertelen."))

    def on_eos(self):
        if self.closing:
            return
        self.at_end = True
        self._set_play_icon(False)
        self.set_status(tr("Vége"))

    def on_buffer(self, percent):
        if self.closing or self.player.phase != "playing":
            return
        if percent < 100:
            self.set_status(tr("Pufferelés {percent}%", percent=percent))
        else:
            self.set_status(tr("Szól"))

    def on_seek(self, scale):
        if self._ui:
            return
        self._scrub = True
        if self._seek_src:
            GLib.source_remove(self._seek_src)
        self._seek_src = GLib.timeout_add(160, self._commit_seek)

    def _commit_seek(self):
        self._seek_src = 0
        self._scrub = False
        if self.player.phase in ("playing", "paused"):
            self.at_end = False
            self.player.seek(self.scale.get_value())
        return False

    def on_volume(self, scale):
        if self._ui:
            return
        value = scale.get_value()
        self.player.set_volume(value)
        self._save_volume(value)
        self._sync_vol_icon(value)

    # ---- KÖZVETLEN MPV MEGHÍVÁS ----
    def on_video(self, *_args):
        if self.current is None:
            return
        
        video_id = self.current["id"]
        
        # Leállítjuk az Rtube lejátszóját
        if self.player.phase == "playing":
            self.player.pause()
            
        self.set_status(tr("mpv indítása..."))
        
        # Odaadom neki a yt-dlp elérhetőségét és a YouTube linket
        yt_path = str(ytdlp_bin())
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            # Az mpv most már maga oldja meg a letöltést
            cmd = ["mpv", f"--script-opts=ytdl_hook-ytdl_path={yt_path}"]
            js = TOOLS.get("js")
            if js:
                cmd.append(f"--ytdl-raw-options-append=js-runtimes={js[0]}:{js[1]}")
            subprocess.Popen(
                cmd + [video_url], 
                start_new_session=True
            )
            self.set_status(tr("mpv elindítva."))
        except FileNotFoundError:
            self.set_status(tr("Hiba: Az mpv nincs telepítve."))

    def tick(self):
        if self.closing:
            return False
        if self._scrub or self.player.phase not in ("playing", "paused", "ended"):
            return True
        pos, dur = self.player.times()
        shown = self.current.get("duration") if self.current else None
        if dur <= 0 and shown:
            dur = shown
        self._ui = True
        if dur > 0:
            self.scale.set_range(0, dur)
            self.scale.set_value(min(pos, dur))
        self._ui = False
        self.pos_label.set_text(fmt_time(pos))
        if dur > 0:
            self.dur_label.set_text(fmt_time(dur))
        return True

    def toggle_fav(self, track):
        video_id = track["id"]
        if video_id in self.fav_ids:
            self.fav_items = [item for item in self.fav_items if item["id"] != video_id]
            self.fav_ids.remove(video_id)
        else:
            self.fav_items.insert(
                0,
                {
                    "id": video_id,
                    "title": track.get("title") or video_id,
                    "channel": track.get("channel") or "",
                    "duration": track.get("duration"),
                },
            )
            self.fav_ids.add(video_id)
        self._save_favs()
        if self.mode == "favs":
            self.render(self.fav_items, tr("Még nincs kedvenc. A szív menti a számot."))
        self.sync_hearts()

    def on_np_heart(self, *_args):
        if self.current is not None:
            self.toggle_fav(self.current)

    def sync_hearts(self):
        index = 0
        while (row := self.list.get_row_at_index(index)) is not None:
            on = row.track["id"] in self.fav_ids
            self._set_heart(row.heart, on)
            index += 1
        on_current = self.current is not None and self.current["id"] in self.fav_ids
        self._set_heart(self.np_heart, on_current)

    def mark_playing(self):
        current_id = self.current["id"] if self.current else None
        index = 0
        while (row := self.list.get_row_at_index(index)) is not None:
            if row.track["id"] == current_id:
                row.add_css_class("playing")
            else:
                row.remove_css_class("playing")
            index += 1
        self._update_upnext()

    def _load_favs(self):
        try:
            data = json.loads(FAV_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        items = []
        for entry in data:
            if isinstance(entry, dict) and entry.get("id"):
                items.append(
                    {
                        "id": entry["id"],
                        "title": entry.get("title") or entry["id"],
                        "channel": entry.get("channel") or "",
                        "duration": norm_duration(entry.get("duration")),
                    }
                )
        return items

    def _save_favs(self):
        CONF.mkdir(parents=True, exist_ok=True)
        tmp = FAV_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.fav_items, ensure_ascii=False, indent=2))
        tmp.replace(FAV_PATH)

    def _load_volume(self):
        try:
            value = float(json.loads(STATE_PATH.read_text()).get("volume", 80))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return 80.0
        return max(0.0, min(100.0, value))

    def _save_volume(self, value):
        self._save_state(volume=round(value))

    def _save_state(self, **values):
        CONF.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(STATE_PATH.read_text())
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
        data.update(values)
        tmp = STATE_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data))
        tmp.replace(STATE_PATH)

    def on_close(self, *_args):
        self.closing = True
        try:
            if getattr(self, "viz", None) is not None:
                self.viz.stop()
        except Exception:
            pass
        for proc in self.procs.values():
            stop_proc(proc)
        try:
            self.player.close()
        except Exception:
            pass
        self.pool.shutdown(wait=False, cancel_futures=True)
        return False


def check_tools():
    """rtube --check-tools: kiírja, mit választ (yt-dlp, JS futtatókörnyezet, cava bemenet)."""
    ensure_tools(print, allow_download="--no-download" not in sys.argv)
    print(f"yt-dlp: {TOOLS['ytdlp']} ({TOOLS.get('ytdlp_version')})")
    print(f"yt-dlp extra args: {' '.join(ytdlp_extra_args()) or '-'}")
    print(f"cava: {shutil.which('cava') or '-'} version={cava_version()} inputs={cava_inputs()}")
    return 0


def main():
    if SKIN in ("winamp", "modern"):
        os.environ["RTUBE_SKIN"] = SKIN
    if "--check-tools" in sys.argv:
        sys.exit(check_tools())
    sys.exit(Rtube().run([a for a in sys.argv if a not in ("--winamp", "--modern")]))


if __name__ == "__main__":
    main()
