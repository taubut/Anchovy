#!/usr/bin/env python3
import sys, os, re, json, subprocess
from pathlib import Path
import urllib.parse
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QRectF, QTimer, QFileSystemWatcher, QThread, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QFont, QFontMetrics, QIcon, QPixmap

# ── Layout ───────────────────────────────────────────────────────────────────
GAP      = 14
TOP_H    = 184
ROW_H    = 44
MAX_ROWS = 6
WIN_W    = 354
DATA_DIR = Path.home() / ".local/share/anchovy"

def compact_h():   return TOP_H
def expanded_h(n): return TOP_H + GAP + 32 + min(n, MAX_ROWS) * ROW_H + 8

# ── Themes ───────────────────────────────────────────────────────────────────
THEMES = {
    "Default":             {"bg": "#1e1e26", "accent": "#6490ff"},
    "Dracula":             {"bg": "#282a36", "accent": "#bd93f9"},
    "Catppuccin Mocha":    {"bg": "#1e1e2e", "accent": "#cba6f7"},
    "Catppuccin Latte":    {"bg": "#eff1f5", "accent": "#8839ef"},
    "Nord":                {"bg": "#2e3440", "accent": "#88c0d0"},
    "Nord Light":          {"bg": "#eceff4", "accent": "#5e81ac"},
    "Gruvbox Dark":        {"bg": "#282828", "accent": "#fabd2f"},
    "Gruvbox Light":       {"bg": "#fbf1c7", "accent": "#d65d0e"},
    "Tokyo Night":         {"bg": "#1a1b26", "accent": "#7aa2f7"},
    "Rose Pine":           {"bg": "#191724", "accent": "#c4a7e7"},
    "Rose Pine Dawn":      {"bg": "#faf4ed", "accent": "#907aa9"},
    "Solarized Dark":      {"bg": "#002b36", "accent": "#268bd2"},
    "Solarized Light":     {"bg": "#fdf6e3", "accent": "#268bd2"},
    "Everforest Dark":     {"bg": "#2d353b", "accent": "#a7c080"},
    "Everforest Light":    {"bg": "#fdf6e3", "accent": "#8da101"},
    "Kanagawa":            {"bg": "#1f1f28", "accent": "#7e9cd8"},
    "One Dark":            {"bg": "#282c34", "accent": "#61afef"},
    "One Light":           {"bg": "#fafafa", "accent": "#4078f2"},
    "Ayu Dark":            {"bg": "#0d1017", "accent": "#e6b450"},
    "Ayu Light":           {"bg": "#f8f9fa", "accent": "#ff9940"},
    "Material Dark":       {"bg": "#212121", "accent": "#82aaff"},
    "Material Light":      {"bg": "#fafafa", "accent": "#6182b8"},
    "GitHub Light":        {"bg": "#ffffff", "accent": "#0969da"},
}

def hex_to_qcolor(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return QColor(r, g, b)

def build_palette(theme_name):
    t   = THEMES.get(theme_name, THEMES["Default"])
    bg  = hex_to_qcolor(t["bg"])
    acc = hex_to_qcolor(t["accent"])
    luma = 0.299*bg.red() + 0.587*bg.green() + 0.114*bg.blue()
    light = luma > 140

    BG      = QColor(bg.red(), bg.green(), bg.blue(), 235)
    BORDER  = QColor(255,255,255,170) if light else QColor(255,255,255,30)
    CARD_L  = QColor(acc.red(), acc.green(), acc.blue(), 60) if not light \
              else QColor(acc.red(), acc.green(), acc.blue(), 40)
    CARD_R  = QColor(255,255,255,30) if not light else QColor(255,255,255,160)
    TEXT    = QColor(30,30,50)   if light else QColor(225,225,240)
    DIM     = QColor(100,110,140) if light else QColor(140,140,160)
    SEL     = QColor(acc.red(), acc.green(), acc.blue(), 80)
    RES_BG  = QColor(bg.red(), bg.green(), bg.blue(), 242)
    ICONS_DIR = Path(__file__).parent / "icons"
    variant   = "teal" if light else "dark"
    ICON_PATH = str(ICONS_DIR / variant / f"anchovy-{variant}-{{size}}.png")
    return dict(BG=BG, BORDER=BORDER, CARD_L=CARD_L, CARD_R=CARD_R,
                TEXT=TEXT, DIM=DIM, SEL=SEL, RES_BG=RES_BG, ACC=acc,
                ICON_PATH=ICON_PATH)

# ── Config ───────────────────────────────────────────────────────────────────
_SEARCH_URLS = {
    "google":     "https://www.google.com/search?q={query}",
    "bing":       "https://www.bing.com/search?q={query}",
    "duckduckgo": "https://duckduckgo.com/?q={query}",
    "yahoo":      "https://search.yahoo.com/search?p={query}",
    "ecosia":     "https://www.ecosia.org/search?q={query}",
    "brave":      "https://search.brave.com/search?q={query}",
    "startpage":  "https://www.startpage.com/sp/search?q={query}",
    "kagi":       "https://kagi.com/search?q={query}",
}
_cached_search_url = None  # reset on each launch

def _name_to_url(name):
    name = name.lower()
    for key, url in _SEARCH_URLS.items():
        if key in name:
            return url
    return None

def get_default_search_url():
    global _cached_search_url
    if _cached_search_url:
        return _cached_search_url

    fallback = "https://duckduckgo.com/?q={query}"
    try:
        browser = subprocess.check_output(
            ["xdg-settings", "get", "default-web-browser"],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode().strip().lower()
    except Exception:
        browser = ""

    # qutebrowser — check config files directly regardless of what xdg-settings says
    autoconfig = Path.home() / ".config/qutebrowser/autoconfig.yml"
    config_py  = Path.home() / ".config/qutebrowser/config.py"
    if "qutebrowser" in browser or autoconfig.exists() or config_py.exists():
        if autoconfig.exists():
            text = autoconfig.read_text(errors="ignore")
            m = re.search(r'DEFAULT:\s*([^\n]+)', text)
            if m:
                url = m.group(1).strip().strip("'\"").replace("{}", "{query}")
                if url.startswith("http"):
                    _cached_search_url = url
                    return url
        if config_py.exists():
            text = config_py.read_text(errors="ignore")
            m = re.search(r"""['"]DEFAULT['"]\s*:\s*['"]([^'"]+)['"]""", text)
            if m:
                url = m.group(1).replace("{}", "{query}")
                if url.startswith("http"):
                    _cached_search_url = url
                    return url

    # Chrome-based: read Default/Preferences JSON for engine short_name
    chrome_dirs = {
        "google-chrome":  ".config/google-chrome",
        "chromium":       ".config/chromium",
        "brave":          ".config/BraveSoftware/Brave-Browser",
        "microsoft-edge": ".config/microsoft-edge",
    }
    for key, rel in chrome_dirs.items():
        if key in browser:
            prefs = Path.home() / rel / "Default/Preferences"
            if prefs.exists():
                try:
                    data  = json.loads(prefs.read_text(errors="ignore"))
                    name  = (data.get("default_search_provider_data", {})
                                 .get("template_url_data", {})
                                 .get("short_name", ""))
                    url = _name_to_url(name)
                    if url:
                        _cached_search_url = url
                        return url
                except Exception:
                    pass

    # Firefox: read engine name from prefs.js
    if "firefox" in browser:
        ff_dir = Path.home() / ".mozilla/firefox"
        profile = None
        ini = ff_dir / "profiles.ini"
        if ini.exists():
            sec = {}
            for line in ini.read_text(errors="ignore").splitlines():
                if line.startswith("["):
                    sec = {}
                elif "=" in line:
                    k, v = line.split("=", 1)
                    sec[k.strip()] = v.strip()
                    if sec.get("Default") == "1" and "Path" in sec:
                        profile = ff_dir / sec["Path"]
        if not profile:
            for d in ff_dir.iterdir():
                if d.is_dir() and "default" in d.name:
                    profile = d
                    break
        if profile:
            prefs_js = profile / "prefs.js"
            if prefs_js.exists():
                text = prefs_js.read_text(errors="ignore")
                m = re.search(
                    r'user_pref\("browser\.search\.defaultenginename",\s*"([^"]+)"\)',
                    text)
                if m:
                    url = _name_to_url(m.group(1))
                    if url:
                        _cached_search_url = url
                        return url

    _cached_search_url = fallback
    return fallback

DEFAULTS = {
    "theme":              "Default",
    "max_results":        6,
    "fuzzy_threshold":    45,
    "web_search_enabled": True,
    "web_search_engine":  "",  # empty = auto-detect from default browser
    "show_frequent_on_empty": True,
    "aliases": {
        "yt":  "xdg-open 'https://www.youtube.com/results?search_query={query}'",
        "gh":  "xdg-open 'https://github.com/search?q={query}'",
        "gg":  "xdg-open 'https://www.google.com/search?q={query}'",
    },
}

def load_config():
    cfg = dict(DEFAULTS)
    cfg["aliases"] = dict(DEFAULTS["aliases"])  # deep copy aliases
    cfg_file = DATA_DIR / "config.json"
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text())
            aliases = data.pop("aliases", {})
            cfg.update(data)
            cfg["aliases"].update(aliases)  # merge, don't replace
        except Exception:
            pass
    return cfg

# ── Learning ─────────────────────────────────────────────────────────────────
def load_learned():
    f = DATA_DIR / "learned.json"
    if f.exists():
        try: return json.loads(f.read_text())
        except Exception: pass
    return {}

def save_learned(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "learned.json").write_text(json.dumps(data, indent=2))

def record_pick(query, app_name, learned):
    q = query.lower().strip()
    if not q: return
    learned.setdefault(q, {})
    learned[q][app_name] = learned[q].get(app_name, 0) + 1
    save_learned(learned)

def get_boost(query, app_name, learned):
    q = query.lower().strip()
    count = learned.get(q, {}).get(app_name, 0)
    if count == 0: return 0
    return min(100, int(50 + 50 * (1 - 1 / (1 + count))))

def get_frequent(apps, learned, limit=6):
    totals = {}
    for picks in learned.values():
        for name, count in picks.items():
            totals[name] = totals.get(name, 0) + count
    ranked = sorted(totals.items(), key=lambda x: -x[1])
    results = []
    name_map = {a["name"]: a for a in apps}
    for name, _ in ranked[:limit]:
        if name in name_map:
            results.append(name_map[name])
    return results

# ── Desktop files ─────────────────────────────────────────────────────────────
def parse_desktop_files():
    apps, seen = [], set()
    field_re = re.compile(r"%[a-zA-Z]")
    for d in ["/usr/share/applications",
              str(Path.home() / ".local/share/applications")]:
        p = Path(d)
        if not p.exists(): continue
        for f in sorted(p.glob("*.desktop")):
            if f.name in seen: continue
            seen.add(f.name)
            name = exec_ = icon = ""
            no_display = False
            in_entry = False
            try:
                for line in f.read_text(errors="ignore").splitlines():
                    if line.startswith("["):
                        in_entry = (line == "[Desktop Entry]")
                        continue
                    if not in_entry: continue
                    if line.startswith("Name=") and not name:   name  = line[5:]
                    elif line.startswith("Exec="):              exec_ = field_re.sub("", line[5:]).strip()
                    elif line.startswith("Icon="):              icon  = line[5:]
                    elif line.startswith("NoDisplay=true"):     no_display = True
            except Exception: continue
            if name and exec_ and not no_display:
                apps.append({"name": name, "exec": exec_, "icon": icon, "path": str(f)})
    return sorted(apps, key=lambda a: a["name"].lower())

# ── File indexer ─────────────────────────────────────────────────────────────
VIDEO_EXT  = {".mp4",".mkv",".webm",".avi",".mov",".flv",".wmv",".m4v",".mpg",".mpeg"}
AUDIO_EXT  = {".mp3",".flac",".ogg",".wav",".m4a",".opus",".aac",".wma"}
IMAGE_EXT  = {".jpg",".jpeg",".png",".gif",".webp",".svg",".bmp",".tiff",".avif"}
DOC_EXT    = {".pdf",".txt",".md",".doc",".docx",".odt",".xls",".xlsx",".csv"}
SKIP_DIRS  = {".git",".cache",".mozilla",".config","node_modules",
              "__pycache__",".local","snap","proc","sys","dev"}

def file_type(path):
    ext = Path(path).suffix.lower()
    if ext in VIDEO_EXT: return "video"
    if ext in AUDIO_EXT: return "audio"
    if ext in IMAGE_EXT: return "image"
    if ext in DOC_EXT:   return "doc"
    if Path(path).is_dir(): return "folder"
    return "file"

def file_icon(ftype):
    return {"video": "video-x-generic", "audio": "audio-x-generic",
            "image": "image-x-generic", "doc": "text-x-generic",
            "folder": "folder"}.get(ftype, "text-x-generic")

class FileIndexer(QThread):
    done = pyqtSignal(list)

    def __init__(self, root=None, max_depth=6, max_files=50000):
        super().__init__()
        self._root      = root or Path.home()
        self._max_depth = max_depth
        self._max_files = max_files

    def run(self):
        index = []
        try:
            self._walk(self._root, 0, index)
        except Exception:
            pass
        self.done.emit(index)

    def _walk(self, p, depth, index):
        if depth > self._max_depth or len(index) >= self._max_files:
            return
        try:
            entries = list(p.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                if entry.name in SKIP_DIRS:
                    continue
                ftype = "folder"
                index.append({"name": entry.name, "path": str(entry),
                               "ftype": ftype, "_file": True})
                self._walk(entry, depth + 1, index)
            else:
                ftype = file_type(str(entry))
                index.append({"name": entry.name, "path": str(entry),
                               "ftype": ftype, "_file": True})

# ── Calculator ────────────────────────────────────────────────────────────────
import math as _math

def calc_eval(expr):
    """Safe math evaluator. Returns result string or None on error."""
    expr = expr.strip().replace("^", "**")
    allowed = set("0123456789 +-*/.()%,_eE")
    safe_names = {k: getattr(_math, k) for k in dir(_math) if not k.startswith("_")}
    safe_names.update({"pi": _math.pi, "e": _math.e, "abs": abs, "round": round})
    try:
        result = eval(expr, {"__builtins__": {}}, safe_names)  # noqa: S307
        if isinstance(result, float) and result == int(result):
            return str(int(result))
        return str(round(result, 10)).rstrip("0").rstrip(".")
    except Exception:
        return None

# ── Alias service icons ───────────────────────────────────────────────────────
def detect_service(result):
    cmd = result.get("exec", "")
    if "youtube.com" in cmd:  return "youtube"
    if "google.com"  in cmd:  return "google"
    return None

def paint_youtube(p, cx, cy):
    """YouTube logo: red rounded rect + white play triangle."""
    rw, rh = 76, 54
    path = QPainterPath()
    path.addRoundedRect(cx - rw//2, cy - rh//2 - 8, rw, rh, 10, 10)
    p.fillPath(path, QColor("#FF0000"))
    tri = QPainterPath()
    tw, th = 20, 24
    tri.moveTo(cx - tw//2,     cy - th//2 - 8)
    tri.lineTo(cx - tw//2,     cy + th//2 - 8)
    tri.lineTo(cx + tw,        cy - 8)
    tri.closeSubpath()
    p.fillPath(tri, QColor("white"))

def paint_google(p, cx, cy):
    """Google G: multicolor text-clipped quadrants."""
    font = QFont("sans-serif", 56, QFont.Weight.Bold)
    fm   = QFontMetrics(font)
    gw   = fm.horizontalAdvance("G")
    gh   = fm.ascent()
    gx   = cx - gw // 2
    gy   = cy + gh // 2 - 6
    text_path = QPainterPath()
    text_path.addText(gx, gy, font, "G")
    p.save()
    p.setClipPath(text_path)
    p.fillRect(cx - 50, cy - 50, 50, 50, QColor("#4285F4"))  # top-left  blue
    p.fillRect(cx,      cy - 50, 50, 50, QColor("#EA4335"))  # top-right red
    p.fillRect(cx,      cy,      50, 50, QColor("#FBBC04"))  # bot-right yellow
    p.fillRect(cx - 50, cy,      50, 50, QColor("#34A853"))  # bot-left  green
    p.restore()

# ── Music / MPD ───────────────────────────────────────────────────────────────
_mpd_music_dir = None

def get_mpd_music_dir():
    global _mpd_music_dir
    if _mpd_music_dir:
        return _mpd_music_dir
    for cfg_path in [Path.home() / ".config/mpd/mpd.conf", Path("/etc/mpd.conf")]:
        if cfg_path.exists():
            for line in cfg_path.read_text(errors="ignore").splitlines():
                s = line.strip()
                if s.startswith("music_directory"):
                    val = s.split(None, 1)[1].strip().strip('"').strip("'")
                    _mpd_music_dir = Path(val.replace("~", str(Path.home())))
                    return _mpd_music_dir
    _mpd_music_dir = Path.home() / "Music"
    return _mpd_music_dir

def find_album_art(abs_path):
    d = Path(abs_path).parent
    for name in ["cover.jpg", "cover.png", "folder.jpg", "folder.png",
                 "artwork.jpg", "artwork.png", "front.jpg", "front.png"]:
        f = d / name
        if f.exists():
            return str(f)
    for ext in (".jpg", ".jpeg", ".png"):
        imgs = list(d.glob(f"*{ext}"))
        if imgs:
            return str(sorted(imgs)[0])
    return None

def search_music(query, max_r=8):
    try:
        fmt = "%file%\t%title%\t%artist%\t%album%"
        out = subprocess.check_output(
            ["mpc", "search", "--format", fmt, "any", query],
            stderr=subprocess.DEVNULL, timeout=3
        ).decode(errors="ignore")
    except Exception:
        return []
    music_dir = get_mpd_music_dir()
    results = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        rel    = parts[0]
        title  = parts[1] if len(parts) > 1 and parts[1] else Path(rel).stem
        artist = parts[2] if len(parts) > 2 else ""
        album  = parts[3] if len(parts) > 3 else ""
        abs_p  = str(music_dir / rel)
        art    = find_album_art(abs_p)
        results.append({
            "name":     title,
            "artist":   artist,
            "album":    album,
            "path":     rel,
            "abs_path": abs_p,
            "art":      art,
            "_music":   True,
        })
    return results[:max_r]

FILE_MODE_FILTERS = {
    "v": {"video"},
    "a": {"audio"},
    "i": {"image"},
}

def parse_file_mode(text):
    """Parse /v, /a, /i sub-modes. Returns (ftype_filter, query, icon, label)."""
    rest = text[1:]  # strip leading /
    if rest and rest[0] in FILE_MODE_FILTERS:
        key = rest[0]
        q   = rest[1:].lstrip()  # optional space after mode letter
        icons  = {"v": "video-x-generic", "a": "audio-x-generic", "i": "image-x-generic"}
        labels = {"v": "videos",          "a": "audio",           "i": "images"}
        return FILE_MODE_FILTERS[key], q, icons[key], labels[key]
    return None, rest.strip(), "folder", "files"

def search_files(query, index, max_r=8, ftype_filter=None):
    q = query.lower()
    results = []
    for f in index:
        if ftype_filter and f["ftype"] not in ftype_filter:
            continue
        if q:
            score = fuzzy_score(q, f["name"])
            if score >= 40:
                results.append((score, f))
        else:
            results.append((50, f))
    results.sort(key=lambda x: -x[0])
    return [f for _, f in results[:max_r]]

def actions_for(result):
    """Return context-aware actions for a result."""
    if result.get("_calc"):
        return [{"id": "copy_result", "name": "Copy",   "icon": "edit-copy"}]
    if result.get("_alias") or result.get("_web"):
        return [{"id": "run_alias",   "name": "Open",   "icon": "system-search"}]
    if result.get("_music"):
        return [{"id": "music_play", "name": "Play Now",  "icon": "media-playback-start"},
                {"id": "music_add",  "name": "Add Queue", "icon": "list-add"},
                {"id": "music_next", "name": "Play Next", "icon": "media-skip-forward"}]
    if result.get("_file"):
        ftype = result.get("ftype","file")
        if ftype == "video":
            return [{"id":"play",      "name":"Play",      "icon":"media-playback-start"},
                    {"id":"open",      "name":"Open",      "icon":"document-open"},
                    {"id":"copy_path", "name":"Copy Path", "icon":"edit-copy"},
                    {"id":"reveal",    "name":"Reveal",    "icon":"folder-open"}]
        if ftype == "audio":
            return [{"id":"play",      "name":"Play",      "icon":"media-playback-start"},
                    {"id":"open",      "name":"Open",      "icon":"document-open"},
                    {"id":"copy_path", "name":"Copy Path", "icon":"edit-copy"}]
        if ftype == "image":
            return [{"id":"open",      "name":"View",      "icon":"image-x-generic"},
                    {"id":"copy_path", "name":"Copy Path", "icon":"edit-copy"},
                    {"id":"reveal",    "name":"Reveal",    "icon":"folder-open"}]
        if ftype == "folder":
            return [{"id":"open",      "name":"Open",      "icon":"folder-open"},
                    {"id":"terminal",  "name":"Terminal",  "icon":"utilities-terminal"},
                    {"id":"copy_path", "name":"Copy Path", "icon":"edit-copy"}]
        return [{"id":"open",      "name":"Open",      "icon":"document-open"},
                {"id":"copy_path", "name":"Copy Path", "icon":"edit-copy"},
                {"id":"reveal",    "name":"Reveal",    "icon":"folder-open"}]
    # App
    return [{"id":"open",      "name":"Open",      "icon":"document-open"},
            {"id":"reveal",    "name":"Reveal",    "icon":"folder-open"},
            {"id":"copy_path", "name":"Copy Path", "icon":"edit-copy"},
            {"id":"copy_name", "name":"Copy Name", "icon":"edit-copy-path"},
            {"id":"terminal",  "name":"Terminal",  "icon":"utilities-terminal"}]

# ── Search ────────────────────────────────────────────────────────────────────
def fuzzy_score(query, text):
    """Simple but effective: substring match + word-start bonus."""
    q, t = query.lower(), text.lower()
    if q == t:        return 100
    if t.startswith(q): return 90
    if q in t:        return 70
    # word boundary match
    words = re.split(r"[\s\-_.]", t)
    for w in words:
        if w.startswith(q): return 65
    # acronym match
    initials = "".join(w[0] for w in words if w)
    if initials.startswith(q): return 60
    # partial match anywhere
    if any(q in w for w in words): return 50
    return 0

def search(query, apps, learned, cfg, file_index=None):
    q = query.strip()
    if not q:
        if cfg.get("show_frequent_on_empty"):
            return get_frequent(apps, learned, cfg.get("max_results", 6))
        return []

    # Calculator mode — query starts with /+
    if q.startswith("/+"):
        expr = q[2:].strip()
        result = calc_eval(expr) if expr else None
        if result is not None:
            return [{"name": result, "expr": expr, "_calc": True,
                     "icon": "accessories-calculator", "path": ""}]
        return []

    # File/music search mode — query starts with /
    if q.startswith("/") and file_index is not None:
        ftype_filter, file_q, _, _ = parse_file_mode(q)
        # /a uses MPD library search (metadata: title, artist, album)
        if ftype_filter == {"audio"}:
            return search_music(file_q)
        return search_files(file_q, file_index, cfg.get("max_results", 8), ftype_filter)

    # Alias check
    aliases = cfg.get("aliases", {})
    parts = q.split(None, 1)
    key = parts[0].lower()
    if key in aliases:
        arg = parts[1] if len(parts) > 1 else ""
        template = aliases[key]
        # URL-encode the query if it's being substituted into a URL
        sub = urllib.parse.quote_plus(arg) if "http" in template else arg
        cmd = template.replace("{query}", sub)
        return [{"name": f"→ {q}", "exec": cmd, "icon": "system-search",
                 "path": "", "_alias": True}]

    threshold = cfg.get("fuzzy_threshold", 45)
    max_r     = cfg.get("max_results", 6)
    results   = []
    for app in apps:
        score = fuzzy_score(q, app["name"])
        if score >= threshold:
            score += get_boost(q, app["name"], learned)
            results.append((score, app))
    results.sort(key=lambda x: -x[0])
    out = [a for _, a in results[:max_r]]

    # Web search fallback at the bottom
    if cfg.get("web_search_enabled") and out is not None:
        engine = cfg.get("web_search_engine") or get_default_search_url()
        quoted = urllib.parse.quote_plus(q)
        url = engine.replace("{query}", quoted).replace("{}", quoted)
        out.append({"name": f'Search "{q}"', "exec": f"xdg-open '{url}'",
                    "icon": "system-search", "path": "", "_web": True})
    return out

def get_icon(name, size=28):
    if not name: return QPixmap()
    ic = QIcon.fromTheme(name)
    return ic.pixmap(size, size) if not ic.isNull() else QPixmap()

def round_pixmap(pm, radius=10):
    """Clip a QPixmap to a rounded rectangle."""
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    ptr = QPainter(out)
    ptr.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, pm.width(), pm.height()), radius, radius)
    ptr.setClipPath(path)
    ptr.drawPixmap(0, 0, pm)
    ptr.end()
    return out


# ── Main window ───────────────────────────────────────────────────────────────
class Anchovy(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(WIN_W)

        self._cfg        = load_config()
        self._learned    = load_learned()
        self._apps       = parse_desktop_files()
        self._pal        = build_palette(self._cfg.get("theme", "Default"))
        self._file_index = []
        self._update_window_icon()

        self._text     = ""
        self._results  = []
        self._sel      = 0
        self._action   = 0
        self._expanded = False
        self._cursor   = True

        self._actions   = actions_for({})  # default app actions
        self._art_cache = {}               # album art pixmap cache
        self._alias_key = None             # set when in alias input mode

        # Start background file indexer
        self._indexer = FileIndexer()
        self._indexer.done.connect(self._on_index_done)
        self._indexer.start()

        self._set_height(compact_h())
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - WIN_W) // 2,
                  (screen.height() - compact_h()) // 3)

        t = QTimer(self)
        t.setInterval(530)
        t.timeout.connect(self._blink)
        t.start()

        # Hot reload — watch config.json for changes from settings window
        cfg_file = str(DATA_DIR / "config.json")
        self._watcher = QFileSystemWatcher([cfg_file])
        self._watcher.fileChanged.connect(self._reload_config)

    def _on_index_done(self, index):
        self._file_index = index
        # If already in file search mode, refresh results
        if self._text.startswith("/"):
            self._do_search()

    def _update_window_icon(self):
        path = self._pal["ICON_PATH"].format(size=64)
        if Path(path).exists():
            self.setWindowIcon(QIcon(path))

    def _reload_config(self):
        self._cfg = load_config()
        self._pal = build_palette(self._cfg.get("theme", "Default"))
        self._update_window_icon()
        # Re-add watcher (some editors replace the file, breaking the watch)
        cfg_file = str(DATA_DIR / "config.json")
        if cfg_file not in self._watcher.files():
            self._watcher.addPath(cfg_file)
        self.update()

    def _open_settings(self):
        settings = Path(__file__).parent / "anchovy_settings.py"
        subprocess.Popen([sys.executable, str(settings)], start_new_session=True)

    def _set_height(self, h):
        self.setFixedHeight(h)

    def _blink(self):
        self._cursor = not self._cursor
        self.update()

    def _do_search(self):
        self._results = search(self._text, self._apps, self._learned,
                               self._cfg, self._file_index)
        self._sel    = 0
        self._action = 0
        self._actions = actions_for(self._results[0]) if self._results else actions_for({})

        # Detect alias input mode: known alias key + space typed
        parts = self._text.split(None, 1)
        key   = parts[0].lower() if parts else ""
        aliases = self._cfg.get("aliases", {})
        self._alias_key = (key if key in aliases and
                           len(self._text) > len(key) and
                           self._text[len(key)] == " " else None)

        # Auto-expand
        if self._alias_key is not None:
            self._expanded = True
            self._set_height(TOP_H + GAP + 60)
        elif self._text.startswith("/") and self._results:
            self._expanded = True
            self._set_height(expanded_h(len(self._results)))
        elif not self._text.startswith("/"):
            self._expanded = False
            self._set_height(compact_h())
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        mod = event.modifiers()

        if key == Qt.Key.Key_Escape:
            QApplication.quit()
        elif key == Qt.Key.Key_Comma and mod & Qt.KeyboardModifier.ControlModifier:
            self._open_settings()
            return
        elif key == Qt.Key.Key_Return:
            self._launch()
        elif key == Qt.Key.Key_Backspace:
            if mod & Qt.KeyboardModifier.ControlModifier:
                # Ctrl+Backspace clears whole word
                self._text = re.sub(r'\S+\s*$', '', self._text)
            else:
                self._text = self._text[:-1]
            self._do_search()
        elif key == Qt.Key.Key_Right or key == Qt.Key.Key_Tab:
            if self._results:
                self._action = (self._action + 1) % len(self._actions)
                self.update()
        elif key == Qt.Key.Key_Left:
            if self._results:
                self._action = (self._action - 1) % len(self._actions)
                self.update()
        elif key == Qt.Key.Key_Down:
            if self._results and not self._expanded:
                self._expanded = True
                self._set_height(expanded_h(len(self._results)))
            elif self._expanded:
                self._sel = min(self._sel + 1, len(self._results) - 1)
                self._actions = actions_for(self._results[self._sel])
                self._action  = 0
            self.update()
        elif key == Qt.Key.Key_Up:
            if self._expanded:
                if self._sel == 0:
                    self._expanded = False
                    self._set_height(compact_h())
                else:
                    self._sel -= 1
                    self._actions = actions_for(self._results[self._sel])
                    self._action  = 0
            self.update()
        elif event.text() and event.text().isprintable():
            self._text += event.text()
            self._do_search()

    def _launch(self):
        if not self._results:
            QApplication.quit()
            return

        result = self._results[self._sel]
        act    = self._actions[self._action]["id"]
        path   = result.get("path", "")
        name   = result["name"]
        is_file = result.get("_file", False)

        def popen(*args, **kw):
            subprocess.Popen(*args, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)

        def find_terminal():
            for t in ["konsole","kitty","alacritty","gnome-terminal","xterm"]:
                if subprocess.call(["which",t], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL) == 0:
                    return t
            return None

        if act == "copy_result":
            QApplication.clipboard().setText(result["name"])
            return
        elif act == "run_alias":
            cmd = result["exec"]
            url_m = re.search(r"https?://[^\s'\"]+", cmd)
            if url_m:
                popen(["xdg-open", url_m.group(0)])
            else:
                popen(cmd, shell=True)
        elif act == "music_play":
            popen(["sh", "-c", f"mpc clear && mpc add '{result['path']}' && mpc play"])
        elif act == "music_add":
            popen(["mpc", "add", result["path"]])
            return
        elif act == "music_next":
            popen(["mpc", "insert", result["path"]])
            return
        elif act == "play":
            popen(["mpv", path])
        elif act == "open":
            if is_file:
                popen(["xdg-open", path])
            else:
                record_pick(self._text, name, self._learned)
                popen(result["exec"], shell=True)
        elif act == "reveal":
            target = path if is_file else path
            parent = str(Path(path).parent) if is_file else path
            popen(["dolphin", "--select", target] if path else ["dolphin", parent])
        elif act == "copy_path":
            QApplication.clipboard().setText(path)
            return
        elif act == "copy_name":
            QApplication.clipboard().setText(name)
            return
        elif act == "terminal":
            folder = path if (is_file and Path(path).is_dir()) else str(Path(path).parent)
            term = find_terminal()
            if term:
                popen([term, "--workdir", folder])

        QApplication.quit()

    # ── Paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        c = self._pal
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Top box
        top = QPainterPath()
        top.addRoundedRect(0, 0, WIN_W, TOP_H, 18, 18)
        p.fillPath(top, c["BG"])
        p.setPen(c["BORDER"])
        p.drawPath(top)

        # Left card
        lc = QPainterPath()
        lc.addRoundedRect(12, 12, 160, 160, 12, 12)
        p.fillPath(lc, c["CARD_L"] if self._results else c["CARD_R"])

        # Right card
        rc = QPainterPath()
        rc.addRoundedRect(182, 12, 160, 160, 12, 12)
        p.fillPath(rc, c["CARD_R"])

        # Left card content
        tf = QFont("sans-serif", 11, QFont.Weight.DemiBold)
        p.setFont(tf)
        fm = p.fontMetrics()

        if self._alias_key is not None:
            # Alias input mode — show service icon centered on left card
            aliases  = self._cfg.get("aliases", {})
            cmd      = aliases.get(self._alias_key, "")
            service  = detect_service({"exec": cmd})
            cx, cy   = 92, 86
            if service == "youtube":
                paint_youtube(p, cx, cy)
            elif service == "google":
                paint_google(p, cx, cy)
            else:
                pm = get_icon("system-search", 64)
                if not pm.isNull():
                    p.drawPixmap(cx - pm.width()//2, cy - pm.height()//2, pm)

        elif self._text.startswith("/+"):
            # Calculator mode — big result on card
            pm = get_icon("accessories-calculator", 48)
            if not pm.isNull():
                p.drawPixmap(12 + (160 - pm.width()) // 2, 38, pm)
            expr = self._text[2:].strip()
            result_str = calc_eval(expr) if expr else ""
            p.setFont(QFont("sans-serif", 16, QFont.Weight.Bold))
            p.setPen(c["TEXT"])
            rfm = p.fontMetrics()
            rel = rfm.elidedText(result_str or "…", Qt.TextElideMode.ElideRight, 148)
            rw  = rfm.horizontalAdvance(rel)
            p.drawText(12 + (160 - rw) // 2, 130, rel)
            p.setFont(QFont("sans-serif", 9))
            p.setPen(c["DIM"])
            efm = p.fontMetrics()
            eel = efm.elidedText(expr, Qt.TextElideMode.ElideLeft, 148)
            ew  = efm.horizontalAdvance(eel)
            p.drawText(12 + (160 - ew) // 2, 150, eel)

        elif self._text.startswith("/"):
            # File search mode — centered icon + typed text below, like app mode
            _, display_q, mode_icon, _ = parse_file_mode(self._text)
            icon_name = mode_icon
            pm = get_icon(icon_name, 64)
            if not pm.isNull():
                ix = 12 + (160 - pm.width()) // 2
                iy = 12 + (160 - pm.height()) // 2 - 10
                p.drawPixmap(ix, iy, pm)
                ty = iy + pm.height() + 14
            else:
                ty = 140

            # Typed text with blinking cursor, strip mode prefix
            display = display_q
            while fm.horizontalAdvance(display) > 136 and len(display) > 1:
                display = display[1:]
            dw = fm.horizontalAdvance(display)
            dx = 12 + (160 - dw) // 2
            p.setPen(c["TEXT"])
            p.drawText(dx, ty, display)
            if self._cursor:
                p.drawLine(dx + dw + 2, ty - 13, dx + dw + 2, ty + 2)

        elif not self._text and not self._results:
            p.setPen(c["DIM"])
            p.drawText(QRect(12, 12, 160, 160), Qt.AlignmentFlag.AlignCenter, "Type…")

        elif self._results:
            app = self._results[self._sel]
            icon_name = file_icon(app["ftype"]) if app.get("_file") else app.get("icon","")
            pm = get_icon(icon_name, 72)
            if not pm.isNull():
                ix = 12 + (160 - pm.width()) // 2
                iy = 12 + (160 - pm.height()) // 2 - 10
                p.drawPixmap(ix, iy, pm)

            name = app["name"]
            max_name_w = 148
            typed_len = len(self._text) if name.lower().startswith(self._text.lower()) else 0
            typed_part = name[:typed_len]
            rest_part  = name[typed_len:]
            # Elide the full name to fit, preserving typed/rest split
            full_elided = fm.elidedText(name, Qt.TextElideMode.ElideRight, max_name_w)
            if full_elided != name:
                # Truncated — draw elided string, underline only typed portion
                typed_part = full_elided[:typed_len]
                rest_part  = full_elided[typed_len:]
            name_w = fm.horizontalAdvance(full_elided)
            nx = 12 + (160 - name_w) // 2
            ny = (iy + pm.height() + 14) if not pm.isNull() else 140

            p.setPen(c["TEXT"])
            p.drawText(nx, ny, typed_part)
            tw = fm.horizontalAdvance(typed_part)
            if typed_part:
                p.drawLine(nx, ny + 2, nx + tw, ny + 2)
            p.drawText(nx + tw, ny, rest_part)
        else:
            p.setPen(c["DIM"])
            p.drawText(QRect(12, 12, 160, 160), Qt.AlignmentFlag.AlignCenter, self._text)

        # Right card content
        if self._results:
            act = self._actions[self._action]
            sel_result = self._results[self._sel]
            art_path = sel_result.get("art") if sel_result.get("_music") else None

            if art_path:
                if art_path not in self._art_cache:
                    raw = QPixmap(art_path)
                    if not raw.isNull():
                        raw = raw.scaled(140, 140,
                                         Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation)
                        self._art_cache[art_path] = round_pixmap(raw, 12)
                    else:
                        self._art_cache[art_path] = QPixmap()
                art_pm = self._art_cache[art_path]
                if not art_pm.isNull():
                    p.drawPixmap(182 + (160 - art_pm.width()) // 2,
                                 12 + (160 - art_pm.height()) // 2, art_pm)
                p.setFont(QFont("sans-serif", 10))
                p.setPen(c["TEXT"])
                p.drawText(QRect(182, 156, 160, 16), Qt.AlignmentFlag.AlignCenter, act["name"])
            else:
                service = detect_service(sel_result) if sel_result.get("_alias") else None
                cx, cy  = 262, 82

                if service == "youtube":
                    paint_youtube(p, cx, cy)
                elif service == "google":
                    paint_google(p, cx, cy)
                else:
                    apm = get_icon(act["icon"], 64)
                    if not apm.isNull():
                        p.drawPixmap(cx - apm.width() // 2, cy - apm.height() // 2, apm)

                # Action name — same vertical position as app name on left card
                nfont = QFont("sans-serif", 11, QFont.Weight.DemiBold)
                p.setFont(nfont)
                p.setPen(c["TEXT"])
                nfm = p.fontMetrics()
                # left card name sits at iy + icon_h + 14; mirror that here
                icon_h = 64
                iy_r   = cy - icon_h // 2
                ny_r   = iy_r + icon_h + 14
                nw     = nfm.horizontalAdvance(act["name"])
                p.drawText(cx - nw // 2, ny_r, act["name"])

                # Subtle dots — kept inside card (card bottom = 172)
                if len(self._actions) > 1:
                    total   = len(self._actions)
                    dot_r   = 2
                    spacing = 8
                    start_x = cx - (total - 1) * spacing // 2
                    dot_y   = ny_r + 10
                    for i in range(total):
                        col = c["ACC"] if i == self._action else \
                              QColor(c["ACC"].red(), c["ACC"].green(), c["ACC"].blue(), 60)
                        p.setBrush(col)
                        p.setPen(Qt.PenStyle.NoPen)
                        p.drawEllipse(start_x + i * spacing - dot_r, dot_y, dot_r*2, dot_r*2)

        # Bottom box
        if not self._expanded:
            return

        boty = TOP_H + GAP
        bh   = self.height() - boty
        bot  = QPainterPath()
        bot.addRoundedRect(0, boty, WIN_W, bh, 18, 18)
        p.fillPath(bot, c["RES_BG"])
        p.setPen(c["BORDER"])
        p.drawPath(bot)

        # ── Alias input bar ──────────────────────────────────────────────────
        if self._alias_key is not None:
            parts   = self._text.split(None, 1)
            query   = parts[1] if len(parts) > 1 else ""
            # search icon
            spm = get_icon("system-search", 22)
            if not spm.isNull():
                p.drawPixmap(16, boty + (bh - 22) // 2, spm)
            p.setFont(QFont("sans-serif", 12))
            p.setPen(c["TEXT"] if query else c["DIM"])
            fm2  = p.fontMetrics()
            disp = query if query else f"Search {self._alias_key}…"
            # scroll long text from right
            while fm2.horizontalAdvance(disp) > WIN_W - 56 and len(disp) > 1:
                disp = disp[1:]
            dw  = fm2.horizontalAdvance(disp)
            ty2 = boty + bh // 2 + fm2.ascent() // 2 - 2
            p.drawText(46, ty2, disp)
            if query and self._cursor:
                p.setPen(c["TEXT"])
                p.drawLine(46 + dw + 2, ty2 - fm2.ascent(), 46 + dw + 2, ty2 + 2)
            return

        if not self._results:
            return

        # Header
        p.setFont(QFont("sans-serif", 9))
        p.setPen(c["DIM"])
        if not self._text:
            label = "Frequently used"
        elif self._text.startswith("/+"):
            label = "Calculator"
        elif self._text.startswith("/"):
            _, _, _, mode_label = parse_file_mode(self._text)
            label = f"{len(self._results)} {mode_label}"
        else:
            label = f"{len(self._results)} results"
        p.drawText(QRect(14, boty, WIN_W - 28, 32),
                   Qt.AlignmentFlag.AlignVCenter, label)

        # Rows
        visible = min(len(self._results), MAX_ROWS)
        for i in range(visible):
            app = self._results[i]
            ry  = boty + 32 + i * ROW_H

            if i == self._sel:
                sel = QPainterPath()
                sel.addRoundedRect(QRectF(4, ry + 2, WIN_W - 8, ROW_H - 4), 8, 8)
                p.fillPath(sel, c["SEL"])

            icon_name = file_icon(app["ftype"]) if app.get("_file") else app.get("icon","")
            pm = get_icon(icon_name, 28)
            if not pm.isNull():
                p.drawPixmap(14, ry + (ROW_H - 28) // 2, pm)

            name_font = QFont("sans-serif", 10, QFont.Weight.DemiBold)
            p.setFont(name_font)
            p.setPen(c["TEXT"])
            name_fm = p.fontMetrics()
            name_str = name_fm.elidedText(app["name"], Qt.TextElideMode.ElideRight, WIN_W - 66)
            p.drawText(QRect(52, ry + 4, WIN_W - 60, 20),
                       Qt.AlignmentFlag.AlignVCenter, name_str)

            sub_font = QFont("sans-serif", 8)
            p.setFont(sub_font)
            p.setPen(c["DIM"])
            if app.get("_music"):
                parts = [app.get("artist", ""), app.get("album", "")]
                sub = "  ·  ".join(x for x in parts if x)
            elif app.get("_file"):
                sub = str(Path(app["path"]).parent).replace(str(Path.home()), "~")
            else:
                sub = app.get("path", "")
            sub_fm = p.fontMetrics()
            sub_str = sub_fm.elidedText(sub, Qt.TextElideMode.ElideMiddle, WIN_W - 66)
            p.drawText(QRect(52, ry + 22, WIN_W - 60, 18),
                       Qt.AlignmentFlag.AlignVCenter, sub_str)


app = QApplication(sys.argv)

# ── Single instance guard ─────────────────────────────────────────────────────
PID_FILE = DATA_DIR / "anchovy.pid"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Check if another instance is already running
if PID_FILE.exists():
    try:
        existing_pid = int(PID_FILE.read_text().strip())
        os.kill(existing_pid, 0)  # signal 0 = just check if process exists
        # Still running — quit silently
        sys.exit(0)
    except (ProcessLookupError, ValueError):
        pass  # stale PID file, continue

# Write our PID
PID_FILE.write_text(str(os.getpid()))
import atexit
atexit.register(lambda: PID_FILE.unlink(missing_ok=True))

win = Anchovy()
win.show()
sys.exit(app.exec())
