#!/usr/bin/env python3
"""Anchovy Settings"""
import json, subprocess, sys, platform
from pathlib import Path

from PyQt6.QtCore import Qt, QRectF, PYQT_VERSION_STR
from PyQt6.QtGui import (QKeySequence, QShortcut, QPainter, QColor, QFont,
                          QFontDatabase, QPainterPath, QBrush, QPen)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                              QLineEdit, QVBoxLayout, QHBoxLayout, QScrollArea,
                              QFrame, QFileDialog)

DATA_DIR    = Path.home() / ".local/share/anchovy"
CONFIG_FILE = DATA_DIR / "config.json"
LEARN_FILE  = DATA_DIR / "learned.json"

DARK_THEMES = {
    "Default":              {"accent": "#64A0FF", "bg": "#1e1e26"},
    "Dracula":              {"accent": "#bd93f9", "bg": "#282a36"},
    "Catppuccin Mocha":     {"accent": "#cba6f7", "bg": "#1e1e2e"},
    "Catppuccin Macchiato": {"accent": "#c6a0f6", "bg": "#24273a"},
    "Catppuccin Frappé":    {"accent": "#ca9ee6", "bg": "#303446"},
    "Nord":                 {"accent": "#88c0d0", "bg": "#2e3440"},
    "Gruvbox Dark":         {"accent": "#fabd2f", "bg": "#282828"},
    "Solarized Dark":       {"accent": "#268bd2", "bg": "#002b36"},
    "Tokyo Night":          {"accent": "#7aa2f7", "bg": "#1a1b26"},
    "Rose Pine":            {"accent": "#c4a7e7", "bg": "#191724"},
    "Rose Pine Moon":       {"accent": "#c4a7e7", "bg": "#232136"},
    "Everforest Dark":      {"accent": "#a7c080", "bg": "#2d353b"},
    "Kanagawa":             {"accent": "#7e9cd8", "bg": "#1f1f28"},
    "One Dark":             {"accent": "#61afef", "bg": "#282c34"},
    "Ayu Dark":             {"accent": "#ffb454", "bg": "#0b0e14"},
    "Material Dark":        {"accent": "#82aaff", "bg": "#212121"},
}
LIGHT_THEMES = {
    "Catppuccin Latte": {"accent": "#8839ef", "bg": "#eff1f5"},
    "Nord Light":       {"accent": "#5e81ac", "bg": "#eceff4"},
    "Gruvbox Light":    {"accent": "#d65d0e", "bg": "#fbf1c7"},
    "Solarized Light":  {"accent": "#268bd2", "bg": "#fdf6e3"},
    "Rose Pine Dawn":   {"accent": "#907aa9", "bg": "#faf4ed"},
    "Everforest Light": {"accent": "#8da101", "bg": "#fdf6e3"},
    "Ayu Light":        {"accent": "#ff9940", "bg": "#fafafa"},
    "Material Light":   {"accent": "#6182b8", "bg": "#fafafa"},
    "One Light":        {"accent": "#4078f2", "bg": "#fafafa"},
    "GitHub Light":     {"accent": "#0969da", "bg": "#ffffff"},
}
THEMES = {**DARK_THEMES, **LIGHT_THEMES}

DEFAULT_CONFIG = {
    "theme": "Default", "font_family": "sans-serif",
    "font_size": 11, "font_weight": "Normal",
    "max_results": 6, "fuzzy_threshold": 45,
    "show_frequent_on_empty": True,
    "web_search_enabled": True,
    "web_search_engine": "https://duckduckgo.com/?q={query}",
    "animations_enabled": True, "animation_speed": 150,
    "sound_enabled": False, "rounded_icons": True,
    "aliases": {
        "yt":  "xdg-open 'https://www.youtube.com/results?search_query={query}'",
        "gh":  "xdg-open 'https://github.com/search?q={query}'",
    },
}
WEIGHT_MAP = {"Light": QFont.Weight.Light, "Normal": QFont.Weight.Normal,
              "DemiBold": QFont.Weight.DemiBold, "Bold": QFont.Weight.Bold}
SUGGESTED_FONTS = ["sans-serif","JetBrains Mono","Fira Code","Cascadia Code",
                   "Source Code Pro","IBM Plex Sans","IBM Plex Mono","Inter",
                   "Roboto","Noto Sans","Ubuntu","Cantarell","Iosevka","Hack","Monospace"]

def load_config():
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg: cfg[k] = v
        return cfg
    except: return dict(DEFAULT_CONFIG)

def save_config(cfg):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def load_learned():
    try: return json.loads(LEARN_FILE.read_text())
    except: return {}

def save_learned(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LEARN_FILE.write_text(json.dumps(data, indent=2))

def get_theme_colors(cfg):
    t = THEMES.get(cfg.get("theme","Default"), THEMES["Default"])
    return QColor(t["accent"]), QColor(t["bg"])

def get_colors(cfg):
    accent, bg = get_theme_colors(cfg)
    luma = 0.299*bg.red() + 0.587*bg.green() + 0.114*bg.blue()
    text = QColor(40,40,50) if luma>140 else QColor(230,230,240)
    dim  = QColor(100,100,115) if luma>140 else QColor(140,140,158)
    hl   = QColor(accent.red(), accent.green(), accent.blue(), 40)
    return accent, bg, text, dim, hl

def get_available_fonts():
    installed = set(QFontDatabase.families())
    return [f for f in SUGGESTED_FONTS
            if f in ("sans-serif","Monospace") or f in installed]


# ── Custom widgets ─────────────────────────────────────────────────────────────
class NavTab(QWidget):
    def __init__(self, label, on_click, accent, text, highlight, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self._label = label; self._on_click = on_click
        self._accent = accent; self._text = text; self._highlight = highlight
        self._active = False; self._hovered = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def set_active(self, a): self._active = a; self.update()
    def mousePressEvent(self, e): self._on_click(self._label)
    def enterEvent(self, e): self._hovered = True;  self.update()
    def leaveEvent(self, e): self._hovered = False; self.update()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        if self._active:
            path = QPainterPath(); path.addRoundedRect(r.adjusted(2,1,-2,-1), 6,6)
            p.fillPath(path, QBrush(self._highlight))
        elif self._hovered:
            path = QPainterPath(); path.addRoundedRect(r.adjusted(2,1,-2,-1), 6,6)
            p.fillPath(path, QBrush(QColor(255,255,255,8)))
        p.setPen(QPen(self._accent if self._active else self._text))
        p.setFont(QFont("sans-serif",11, QFont.Weight.DemiBold if self._active else QFont.Weight.Normal))
        p.drawText(r.adjusted(14,0,0,0), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter, self._label)
        p.end()


class LearnedRow(QWidget):
    def __init__(self, query, app_name, count, on_delete, accent, text, dim, parent=None):
        super().__init__(parent)
        self.setFixedHeight(46)
        self._query=query; self._app_name=app_name; self._count=count
        self._on_delete=on_delete; self._accent=accent; self._text=text; self._dim=dim
        self._hovered=False; self._del_hovered=False
        self.setMouseTracking(True)

    def _del_rect(self): return QRectF(self.width()-36, 11, 24, 24)

    def mouseMoveEvent(self, e):
        self._del_hovered = self._del_rect().contains(e.position())
        self._hovered = True
        self.setCursor(Qt.CursorShape.PointingHandCursor if self._del_hovered else Qt.CursorShape.ArrowCursor)
        self.update()

    def leaveEvent(self, e): self._hovered=False; self._del_hovered=False; self.update()

    def mousePressEvent(self, e):
        if self._del_hovered: self._on_delete(self._query, self._app_name)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            path = QPainterPath()
            path.addRoundedRect(QRectF(0,0,self.width(),self.height()).adjusted(2,1,-2,-1), 6,6)
            p.fillPath(path, QBrush(QColor(255,255,255,10)))
        p.setPen(QPen(self._accent)); p.setFont(QFont("monospace",10,QFont.Weight.Bold))
        p.drawText(QRectF(12,0,120,self.height()), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter, self._query)
        p.setPen(QPen(self._dim)); p.setFont(QFont("sans-serif",10))
        p.drawText(QRectF(135,0,20,self.height()), Qt.AlignmentFlag.AlignCenter, "→")
        p.setPen(QPen(self._text))
        p.drawText(QRectF(160,0,self.width()-260,self.height()), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter, self._app_name)
        p.setPen(QPen(self._dim)); p.setFont(QFont("sans-serif",9))
        p.drawText(QRectF(self.width()-105,0,60,self.height()), Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,
                   f"{self._count} use{'s' if self._count!=1 else ''}")
        dr = self._del_rect()
        if self._del_hovered:
            dp = QPainterPath(); dp.addRoundedRect(dr,4,4)
            p.fillPath(dp, QBrush(QColor(255,80,80,60)))
        p.setPen(QPen(QColor(255,100,100) if self._del_hovered else self._dim, 1.5))
        cx,cy = dr.center().x(), dr.center().y()
        p.drawLine(int(cx-4),int(cy-4),int(cx+4),int(cy+4))
        p.drawLine(int(cx+4),int(cy-4),int(cx-4),int(cy+4))
        p.end()


# ── Settings window ────────────────────────────────────────────────────────────
class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anchovy — Settings")
        self.setMinimumSize(750, 550); self.resize(750, 550)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self.close)
        self.cfg = load_config()
        self._current_tab = "Theme"
        self._refresh_colors()
        self.setStyleSheet(f"QMainWindow {{ background-color: {self._bg.name()}; }}")
        self._build_ui()

    def _refresh_colors(self):
        self._accent, self._bg, self._text, self._dim, self._highlight = get_colors(self.cfg)

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(24,24,24,24); root.setSpacing(0)

        sidebar = QVBoxLayout(); sidebar.setSpacing(4); sidebar.setContentsMargins(0,4,20,8)
        title = QLabel("Settings")
        title.setFont(QFont("sans-serif",15,QFont.Weight.Bold))
        title.setStyleSheet(f"color:{self._text.name()};padding-left:14px;padding-bottom:12px;")
        sidebar.addWidget(title)

        self._tabs = {}
        for name in ["Theme","Font","Search","Matching","Appearance","Aliases","Hotkey","Learning","About"]:
            tab = NavTab(name, self._switch_tab, self._accent, self._text, self._highlight)
            tab.set_active(name == self._current_tab)
            sidebar.addWidget(tab); self._tabs[name] = tab

        sidebar.addStretch(); root.addLayout(sidebar)

        divider = QFrame(); divider.setFixedWidth(1)
        divider.setStyleSheet("background:rgba(255,255,255,0.08);")
        root.addWidget(divider)

        self._content = QVBoxLayout()
        self._content.setContentsMargins(24,4,8,8); self._content.setSpacing(14)
        root.addLayout(self._content, stretch=1)
        self._show_tab(self._current_tab)

    def _switch_tab(self, name):
        self._current_tab = name
        for n,t in self._tabs.items(): t.set_active(n==name)
        self._show_tab(name)

    def _clear(self):
        def nuke(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
                elif item.layout(): nuke(item.layout())
        nuke(self._content)

    def _show_tab(self, name):
        self._clear()
        {"Theme":self._tab_theme,"Font":self._tab_font,"Search":self._tab_search,
         "Matching":self._tab_matching,"Appearance":self._tab_appearance,
         "Aliases":self._tab_aliases,"Hotkey":self._tab_hotkey,
         "Learning":self._tab_learning,"About":self._tab_about}[name]()

    def _heading(self, text):
        l=QLabel(text); l.setFont(QFont("sans-serif",14,QFont.Weight.Bold))
        l.setStyleSheet(f"color:{self._text.name()};"); self._content.addWidget(l)

    def _sub(self, text):
        l=QLabel(text); l.setFont(QFont("sans-serif",10))
        l.setStyleSheet(f"color:{self._dim.name()};"); l.setWordWrap(True)
        self._content.addWidget(l)

    def _plus_minus(self, value, on_change):
        row=QHBoxLayout(); row.setSpacing(8)
        minus=QLabel(" - "); minus.setFont(QFont("sans-serif",14,QFont.Weight.Bold))
        minus.setStyleSheet(f"color:{self._text.name()};background:rgba(255,255,255,0.06);border-radius:4px;padding:0 6px;")
        minus.setCursor(Qt.CursorShape.PointingHandCursor)
        val_lbl=QLabel(str(value)); val_lbl.setFont(QFont("monospace",12,QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color:{self._accent.name()};"); val_lbl.setFixedWidth(36)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus=QLabel(" + "); plus.setFont(QFont("sans-serif",14,QFont.Weight.Bold))
        plus.setStyleSheet(f"color:{self._text.name()};background:rgba(255,255,255,0.06);border-radius:4px;padding:0 6px;")
        plus.setCursor(Qt.CursorShape.PointingHandCursor)
        minus.mousePressEvent = lambda e: on_change(-1, val_lbl)
        plus.mousePressEvent  = lambda e: on_change( 1, val_lbl)
        row.addWidget(minus); row.addWidget(val_lbl); row.addWidget(plus); row.addStretch()
        self._content.addLayout(row); return val_lbl

    def _input_style(self):
        return (f"color:{self._text.name()};background:rgba(255,255,255,0.06);"
                f"border:1px solid rgba(255,255,255,0.10);border-radius:6px;padding:4px 8px;font-size:10pt;")

    def _toggle_style(self, on):
        return (f"color:{self._accent.name() if on else self._dim.name()};"
                f"background:rgba(255,255,255,{'0.08' if on else '0.03'});border-radius:4px;padding:2px;")

    def _font_btn_style(self, active):
        return (f"color:{self._accent.name() if active else self._text.name()};"
                f"background:rgba(255,255,255,{'0.10' if active else '0.04'});"
                f"border:1px solid rgba(255,255,255,{'0.20' if active else '0.06'});"
                f"border-radius:6px;padding:4px 10px;")

    def _scroll_area(self):
        sa=QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.Shape.NoFrame)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sa.setStyleSheet("QScrollArea{background:transparent;}QScrollBar:vertical{background:transparent;width:6px;}"
                         "QScrollBar::handle:vertical{background:rgba(255,255,255,0.15);border-radius:3px;min-height:20px;}"
                         "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        return sa

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _tab_theme(self):
        self._heading("Accent Theme"); self._sub("Choose a color palette for Anchovy.")
        self._content.addSpacing(4)
        self._theme_rows = []; current = self.cfg.get("theme","Default")

        container = QWidget(); vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0,0,0,0); vbox.setSpacing(2)

        for section_name, section_themes in [("Dark",DARK_THEMES),("Light",LIGHT_THEMES)]:
            lbl = QLabel(section_name); lbl.setFont(QFont("sans-serif",10,QFont.Weight.DemiBold))
            lbl.setStyleSheet(f"color:{self._dim.name()};padding:8px 0 4px 4px;")
            vbox.addWidget(lbl)
            for name, data in section_themes.items():
                row = self._make_theme_row(name, data, name==current)
                vbox.addWidget(row); self._theme_rows.append((name, row))
        vbox.addStretch()

        scroll = self._scroll_area(); scroll.setWidget(container)
        self._theme_scroll = scroll
        self._content.addWidget(scroll, stretch=1)

    def _make_theme_row(self, name, data, active):
        row = QWidget(); row.setFixedHeight(44)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(row); layout.setContentsMargins(6,3,10,3); layout.setSpacing(12)

        preview = QWidget(); preview.setFixedSize(48,32)
        preview.setStyleSheet(f"background:{data['bg']};border-radius:6px;border:1px solid rgba(128,128,128,0.2);")
        bar = QWidget(preview); bar.setGeometry(0,0,6,32)
        bar.setStyleSheet(f"background:{data['accent']};border-radius:3px 0 0 3px;")
        ac = QColor(data['accent'])
        for y_off in [10,18]:
            line = QWidget(preview); line.setGeometry(12,y_off,20,3)
            line.setStyleSheet(f"background:rgba({ac.red()},{ac.green()},{ac.blue()},0.5);border-radius:1px;")
        layout.addWidget(preview)

        lbl = QLabel(name)
        lbl.setFont(QFont("sans-serif",10,QFont.Weight.DemiBold if active else QFont.Weight.Normal))
        lbl.setStyleSheet(f"color:{self._accent.name() if active else self._text.name()};")
        layout.addWidget(lbl, stretch=1)

        if active:
            check = QLabel("✓"); check.setFont(QFont("sans-serif",12,QFont.Weight.Bold))
            check.setStyleSheet(f"color:{self._accent.name()};"); layout.addWidget(check)
            row.setStyleSheet(f"background:rgba({self._accent.red()},{self._accent.green()},{self._accent.blue()},0.10);border-radius:8px;")

        row.mousePressEvent = lambda e, n=name: self._pick_theme(n)
        return row

    def _pick_theme(self, name):
        scroll_pos = self._theme_scroll.verticalScrollBar().value() if hasattr(self,'_theme_scroll') else 0
        self.cfg["theme"] = name; save_config(self.cfg)
        self._refresh_colors()
        self.setStyleSheet(f"QMainWindow{{background-color:{self._bg.name()};}}")
        self.centralWidget().deleteLater(); self._build_ui()
        if hasattr(self,'_theme_scroll'):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._theme_scroll.verticalScrollBar().setValue(scroll_pos))

    # ── Font ──────────────────────────────────────────────────────────────────
    def _tab_font(self):
        self._heading("Font"); self._sub("Customize the launcher font.")
        self._content.addSpacing(8)
        lbl=QLabel("Family"); lbl.setFont(QFont("sans-serif",12,QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color:{self._text.name()};"); self._content.addWidget(lbl)

        available=get_available_fonts(); current=self.cfg.get("font_family","sans-serif")
        self._font_btns=[]; grid=None
        for i, fname in enumerate(available):
            if i%3==0:
                grid=QHBoxLayout(); grid.setSpacing(6)
                grid.setAlignment(Qt.AlignmentFlag.AlignLeft); self._content.addLayout(grid)
            btn=QLabel(fname); btn.setFixedHeight(32); btn.setFont(QFont(fname,10))
            btn.setStyleSheet(self._font_btn_style(fname==current))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.mousePressEvent=lambda e,f=fname: self._pick_font(f)
            grid.addWidget(btn); self._font_btns.append((fname,btn))

        self._content.addSpacing(12)
        lbl2=QLabel("Size"); lbl2.setFont(QFont("sans-serif",12,QFont.Weight.DemiBold))
        lbl2.setStyleSheet(f"color:{self._text.name()};"); self._content.addWidget(lbl2)
        self._plus_minus(self.cfg.get("font_size",11), self._adj_font_size)

        self._content.addSpacing(12)
        lbl3=QLabel("Weight"); lbl3.setFont(QFont("sans-serif",12,QFont.Weight.DemiBold))
        lbl3.setStyleSheet(f"color:{self._text.name()};"); self._content.addWidget(lbl3)
        row=QHBoxLayout(); row.setSpacing(6); row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cur_w=self.cfg.get("font_weight","Normal"); self._weight_btns=[]
        for wn in ["Light","Normal","DemiBold","Bold"]:
            btn=QLabel(wn); btn.setFixedHeight(32); btn.setFont(QFont("sans-serif",10,WEIGHT_MAP[wn]))
            btn.setStyleSheet(self._font_btn_style(wn==cur_w))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.mousePressEvent=lambda e,w=wn: self._pick_weight(w)
            row.addWidget(btn); self._weight_btns.append((wn,btn))
        self._content.addLayout(row)

        self._content.addSpacing(16)
        pl=QLabel("Preview"); pl.setFont(QFont("sans-serif",10))
        pl.setStyleSheet(f"color:{self._dim.name()};"); self._content.addWidget(pl)
        fam=self.cfg.get("font_family","sans-serif"); sz=self.cfg.get("font_size",11)
        wt=WEIGHT_MAP.get(self.cfg.get("font_weight","Normal"), QFont.Weight.Normal)
        self._preview=QLabel("The quick brown fox jumps over the lazy dog")
        self._preview.setFont(QFont(fam,sz,wt)); self._preview.setWordWrap(True)
        self._preview.setStyleSheet(f"color:{self._text.name()};background:rgba(255,255,255,0.05);border-radius:8px;padding:12px;")
        self._content.addWidget(self._preview); self._content.addStretch()

    def _pick_font(self, name):
        self.cfg["font_family"]=name; save_config(self.cfg)
        for fn,btn in self._font_btns: btn.setStyleSheet(self._font_btn_style(fn==name))
        self._update_preview()

    def _adj_font_size(self, delta, lbl):
        v=max(8,min(18,self.cfg.get("font_size",11)+delta))
        self.cfg["font_size"]=v; save_config(self.cfg); lbl.setText(str(v)); self._update_preview()

    def _pick_weight(self, name):
        self.cfg["font_weight"]=name; save_config(self.cfg)
        for wn,btn in self._weight_btns: btn.setStyleSheet(self._font_btn_style(wn==name))
        self._update_preview()

    def _update_preview(self):
        if hasattr(self,"_preview"):
            fam=self.cfg.get("font_family","sans-serif"); sz=self.cfg.get("font_size",11)
            wt=WEIGHT_MAP.get(self.cfg.get("font_weight","Normal"),QFont.Weight.Normal)
            self._preview.setFont(QFont(fam,sz,wt))

    # ── Search ────────────────────────────────────────────────────────────────
    def _tab_search(self):
        self._heading("Search Sources"); self._sub("Choose what Anchovy searches through.")
        for sid,slbl,sdesc in [("apps","Applications","Search installed .desktop apps"),
                                ("files","Files","Fuzzy search files and folders"),
                                ("clipboard","Clipboard","Search clipboard history"),
                                ("windows","Windows","Search and switch open windows")]:
            row=QHBoxLayout(); row.setSpacing(10)
            sources=self.cfg.get("search_sources",["apps"]); on=sid in sources
            check=QLabel("ON" if on else "OFF"); check.setFixedWidth(36)
            check.setFont(QFont("monospace",9,QFont.Weight.Bold))
            check.setStyleSheet(self._toggle_style(on))
            check.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check.setCursor(Qt.CursorShape.PointingHandCursor)
            check.mousePressEvent=lambda e,s=sid,c=check: self._toggle_src(s,c)
            row.addWidget(check)
            tc=QVBoxLayout(); tc.setSpacing(0)
            nl=QLabel(slbl); nl.setFont(QFont("sans-serif",10,QFont.Weight.DemiBold))
            nl.setStyleSheet(f"color:{self._text.name()};")
            dl=QLabel(sdesc); dl.setFont(QFont("sans-serif",8))
            dl.setStyleSheet(f"color:{self._dim.name()};")
            tc.addWidget(nl); tc.addWidget(dl); row.addLayout(tc,stretch=1)
            self._content.addLayout(row)
        self._content.addSpacing(20)
        ml=QLabel("Max Results"); ml.setFont(QFont("sans-serif",12,QFont.Weight.DemiBold))
        ml.setStyleSheet(f"color:{self._text.name()};"); self._content.addWidget(ml)
        self._plus_minus(self.cfg.get("max_results",6), self._adj_max)
        self._content.addStretch()

    def _toggle_src(self, sid, check):
        sources=self.cfg.get("search_sources",["apps"])
        if sid in sources:
            if len(sources)>1: sources.remove(sid)
        else: sources.append(sid)
        self.cfg["search_sources"]=sources; save_config(self.cfg)
        on=sid in sources; check.setText("ON" if on else "OFF")
        check.setStyleSheet(self._toggle_style(on))

    def _adj_max(self, delta, lbl):
        v=max(3,min(15,self.cfg.get("max_results",6)+delta))
        self.cfg["max_results"]=v; save_config(self.cfg); lbl.setText(str(v))

    # ── Matching ──────────────────────────────────────────────────────────────
    def _tab_matching(self):
        self._heading("Fuzzy Threshold")
        self._sub("Lower = more results (looser matching).\nHigher = fewer, more precise results.")
        self._plus_minus(self.cfg.get("fuzzy_threshold",45), self._adj_thresh)
        sc=QHBoxLayout()
        lo=QLabel("Loose"); lo.setFont(QFont("sans-serif",8)); lo.setStyleSheet(f"color:{self._dim.name()};")
        hi=QLabel("Strict"); hi.setFont(QFont("sans-serif",8)); hi.setStyleSheet(f"color:{self._dim.name()};")
        sc.addWidget(lo); sc.addStretch(); sc.addWidget(hi); self._content.addLayout(sc)
        self._content.addStretch()

    def _adj_thresh(self, delta, lbl):
        v=max(20,min(80,self.cfg.get("fuzzy_threshold",45)+delta*5))
        self.cfg["fuzzy_threshold"]=v; save_config(self.cfg); lbl.setText(str(v))

    # ── Appearance ────────────────────────────────────────────────────────────
    def _tab_appearance(self):
        self._heading("Appearance & Behavior"); self._sub("Toggle visual and audio features.")
        self._content.addSpacing(8)
        self._appearance_checks={}
        for key,label,desc in [
            ("animations_enabled","Animations","Fade in/out when showing and hiding"),
            ("sound_enabled","Sound Effects","Play a sound when launching an app"),
            ("rounded_icons","Rounded Icons","Clip app icons to rounded corners"),
            ("show_frequent_on_empty","Frequent Apps","Show most-used apps when search is empty"),
            ("web_search_enabled","Web Search Fallback","Offer web search when few results match"),
        ]:
            on=self.cfg.get(key,True); row=QHBoxLayout(); row.setSpacing(10)
            check=QLabel("ON" if on else "OFF"); check.setFixedWidth(36)
            check.setFont(QFont("monospace",9,QFont.Weight.Bold))
            check.setStyleSheet(self._toggle_style(on))
            check.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check.setCursor(Qt.CursorShape.PointingHandCursor)
            check.mousePressEvent=lambda e,k=key,c=check: self._toggle_bool(k,c)
            row.addWidget(check)
            tc=QVBoxLayout(); tc.setSpacing(0)
            nl=QLabel(label); nl.setFont(QFont("sans-serif",10,QFont.Weight.DemiBold))
            nl.setStyleSheet(f"color:{self._text.name()};")
            dl=QLabel(desc); dl.setFont(QFont("sans-serif",8))
            dl.setStyleSheet(f"color:{self._dim.name()};")
            tc.addWidget(nl); tc.addWidget(dl); row.addLayout(tc,stretch=1)
            self._content.addLayout(row); self._appearance_checks[key]=check
        self._content.addSpacing(16)
        lbl=QLabel("Animation Speed (ms)"); lbl.setFont(QFont("sans-serif",12,QFont.Weight.DemiBold))
        lbl.setStyleSheet(f"color:{self._text.name()};"); self._content.addWidget(lbl)
        self._plus_minus(self.cfg.get("animation_speed",150), self._adj_anim_speed)
        self._content.addStretch()

    def _toggle_bool(self, key, check):
        self.cfg[key]=not self.cfg.get(key,True); save_config(self.cfg)
        on=self.cfg[key]; check.setText("ON" if on else "OFF")
        check.setStyleSheet(self._toggle_style(on))

    def _adj_anim_speed(self, delta, lbl):
        v=max(0,min(500,self.cfg.get("animation_speed",150)+delta*25))
        self.cfg["animation_speed"]=v; save_config(self.cfg); lbl.setText(str(v))

    # ── Aliases ───────────────────────────────────────────────────────────────
    def _tab_aliases(self):
        self._heading("Custom Aliases")
        self._sub('Define shortcut commands. Use {query} for arguments.\nExample: "yt" → opens YouTube search.')
        self._content.addSpacing(4)

        self._alias_container=QWidget()
        self._alias_layout=QVBoxLayout(self._alias_container)
        self._alias_layout.setContentsMargins(0,0,0,0); self._alias_layout.setSpacing(2)
        self._alias_scroll=self._scroll_area(); self._alias_scroll.setWidget(self._alias_container)
        self._alias_empty=QLabel("No aliases defined.")
        self._alias_empty.setFont(QFont("sans-serif",10))
        self._alias_empty.setStyleSheet(f"color:{self._dim.name()};")
        self._alias_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._alias_empty.setVisible(False)
        self._content.addWidget(self._alias_scroll, stretch=1)
        self._content.addWidget(self._alias_empty)
        self._refresh_aliases()

        self._content.addSpacing(8)
        add_row=QHBoxLayout(); add_row.setSpacing(6)
        self._new_key=QLineEdit(); self._new_key.setPlaceholderText("key")
        self._new_key.setFixedWidth(80); self._new_key.setFixedHeight(30)
        self._new_key.setStyleSheet(self._input_style())
        self._new_cmd=QLineEdit(); self._new_cmd.setPlaceholderText("command (use {query} for args)")
        self._new_cmd.setFixedHeight(30); self._new_cmd.setStyleSheet(self._input_style())
        add_btn=QLabel(" + Add "); add_btn.setFixedHeight(30)
        add_btn.setFont(QFont("sans-serif",10,QFont.Weight.Bold))
        add_btn.setStyleSheet(f"color:{self._accent.name()};background:rgba(255,255,255,0.08);border-radius:6px;padding:4px 8px;")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.mousePressEvent=lambda e: self._add_alias()
        add_row.addWidget(self._new_key); add_row.addWidget(self._new_cmd,stretch=1); add_row.addWidget(add_btn)
        self._content.addLayout(add_row)

    def _refresh_aliases(self):
        while self._alias_layout.count():
            item=self._alias_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        aliases=self.cfg.get("aliases",{})
        if not aliases:
            self._alias_empty.setVisible(True); self._alias_scroll.setVisible(False); return
        self._alias_empty.setVisible(False); self._alias_scroll.setVisible(True)
        for key,cmd in aliases.items():
            row=QWidget(); row.setFixedHeight(40)
            rl=QHBoxLayout(row); rl.setContentsMargins(6,2,6,2); rl.setSpacing(8)
            kl=QLabel(key); kl.setFont(QFont("monospace",10,QFont.Weight.Bold))
            kl.setStyleSheet(f"color:{self._accent.name()};"); kl.setFixedWidth(60)
            arrow=QLabel("→"); arrow.setStyleSheet(f"color:{self._dim.name()};")
            cl=QLabel(cmd); cl.setFont(QFont("sans-serif",9))
            cl.setStyleSheet(f"color:{self._text.name()};")
            dl=QLabel("x"); dl.setFont(QFont("sans-serif",10,QFont.Weight.Bold))
            dl.setStyleSheet(f"color:{self._dim.name()};"); dl.setCursor(Qt.CursorShape.PointingHandCursor)
            dl.mousePressEvent=lambda e,k=key: self._del_alias(k)
            rl.addWidget(kl); rl.addWidget(arrow); rl.addWidget(cl,stretch=1); rl.addWidget(dl)
            self._alias_layout.addWidget(row)
        self._alias_layout.addStretch()

    def _add_alias(self):
        key=self._new_key.text().strip(); cmd=self._new_cmd.text().strip()
        if not key or not cmd: return
        aliases=self.cfg.get("aliases",{}); aliases[key]=cmd
        self.cfg["aliases"]=aliases; save_config(self.cfg)
        self._new_key.clear(); self._new_cmd.clear(); self._refresh_aliases()

    def _del_alias(self, key):
        aliases=self.cfg.get("aliases",{}); aliases.pop(key,None)
        self.cfg["aliases"]=aliases; save_config(self.cfg); self._refresh_aliases()

    # ── Hotkey ────────────────────────────────────────────────────────────────
    def _tab_hotkey(self):
        self._heading("Global Hotkey")
        self._sub("Set a keyboard shortcut to toggle Anchovy from anywhere.")
        self._content.addSpacing(12)
        cur=self._read_current_hotkey()
        self._hotkey_label=QLabel(cur if cur else "Not set")
        self._hotkey_label.setFont(QFont("monospace",14,QFont.Weight.Bold))
        self._hotkey_label.setStyleSheet(f"color:{self._accent.name()};background:rgba(255,255,255,0.05);border-radius:8px;padding:14px;")
        self._hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.addWidget(self._hotkey_label)
        self._content.addSpacing(16); self._sub("Choose a shortcut:"); self._content.addSpacing(4)
        grid=QHBoxLayout(); grid.setSpacing(8)
        for combo in ["Meta+Space","Meta+D","Meta+R","Alt+Space"]:
            btn=QLabel(f"  {combo}  "); btn.setFixedHeight(34)
            btn.setFont(QFont("monospace",10,QFont.Weight.DemiBold))
            active=cur==combo
            btn.setStyleSheet(f"color:{self._accent.name() if active else self._text.name()};"
                              f"background:rgba(255,255,255,{'0.12' if active else '0.05'});"
                              f"border:1px solid rgba(255,255,255,{'0.20' if active else '0.08'});"
                              f"border-radius:6px;padding:4px 10px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.mousePressEvent=lambda e,c=combo: self._set_hotkey(c)
            grid.addWidget(btn)
        grid.addStretch(); self._content.addLayout(grid)
        self._content.addSpacing(12); self._sub("Or type a custom combo (e.g. Ctrl+Alt+A):")
        custom_row=QHBoxLayout(); custom_row.setSpacing(8)
        self._hotkey_input=QLineEdit(); self._hotkey_input.setPlaceholderText("Meta+Space")
        self._hotkey_input.setFixedHeight(34); self._hotkey_input.setStyleSheet(self._input_style())
        apply_btn=QLabel("  Apply  "); apply_btn.setFixedHeight(34)
        apply_btn.setFont(QFont("sans-serif",10,QFont.Weight.Bold))
        apply_btn.setStyleSheet(f"color:{self._accent.name()};background:rgba(255,255,255,0.08);border-radius:6px;padding:4px 12px;")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.mousePressEvent=lambda e: self._set_hotkey(self._hotkey_input.text().strip())
        custom_row.addWidget(self._hotkey_input,stretch=1); custom_row.addWidget(apply_btn)
        self._content.addLayout(custom_row); self._content.addSpacing(16)
        remove_btn=QLabel("  Remove Shortcut  "); remove_btn.setFixedHeight(32)
        remove_btn.setFont(QFont("sans-serif",10))
        remove_btn.setStyleSheet("color:#ff6464;background:rgba(255,100,100,0.08);border-radius:6px;padding:4px 12px;")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.mousePressEvent=lambda e: self._remove_hotkey()
        self._content.addWidget(remove_btn); self._content.addSpacing(16)
        self._hotkey_status=QLabel(""); self._hotkey_status.setFont(QFont("sans-serif",9))
        self._hotkey_status.setStyleSheet(f"color:{self._dim.name()};"); self._hotkey_status.setWordWrap(True)
        self._content.addWidget(self._hotkey_status); self._content.addStretch()

    def _read_current_hotkey(self):
        try:
            rc=Path.home()/".config"/"kglobalshortcutsrc"
            if not rc.is_file(): return ""
            in_section=False
            for line in rc.read_text().splitlines():
                if line.strip()=="[anchovy-toggle.desktop]": in_section=True; continue
                if in_section and line.startswith("["): break
                if in_section and line.startswith("_launch="):
                    parts=line.split("=",1)[1].split(","); shortcut=parts[0].strip()
                    if shortcut and shortcut!="none": return shortcut
        except: pass
        return ""

    def _set_hotkey(self, combo):
        if not combo: return
        script=str(Path(__file__).parent/"anchovy-toggle.sh")
        try:
            subprocess.run(["kwriteconfig6","--file","kglobalshortcutsrc","--group","anchovy-toggle.desktop","--key","_k_friendly_name","Anchovy Toggle"],check=True)
            subprocess.run(["kwriteconfig6","--file","kglobalshortcutsrc","--group","anchovy-toggle.desktop","--key","_launch",f"{combo},{combo},Anchovy Toggle"],check=True)
            desktop_path=Path.home()/".local"/"share"/"kglobalaccel"/"anchovy-toggle.desktop"
            desktop_path.parent.mkdir(parents=True,exist_ok=True)
            desktop_path.write_text(f"[Desktop Entry]\nType=Application\nName=Anchovy Toggle\nExec={script}\nX-KDE-GlobalAccel-CommandShortcut=true\nStartupNotify=false\nNoDisplay=true\n")
            subprocess.run(["dbus-send","--type=signal","--dest=org.kde.KGlobalAccel","/kglobalaccel","org.kde.KGlobalAccel.yourShortcutsChanged"],capture_output=True)
            self.cfg["hotkey"]=combo; save_config(self.cfg)
            self._hotkey_label.setText(combo)
            self._hotkey_status.setText(f"Shortcut set to {combo}.")
            self._hotkey_status.setStyleSheet(f"color:{self._accent.name()};")
        except Exception as ex:
            self._hotkey_status.setText(f"Error: {ex}"); self._hotkey_status.setStyleSheet("color:#ff6464;")

    def _remove_hotkey(self):
        try:
            subprocess.run(["kwriteconfig6","--file","kglobalshortcutsrc","--group","anchovy-toggle.desktop","--key","_launch","none,none,Anchovy Toggle"],check=True)
            dp=Path.home()/".local"/"share"/"kglobalaccel"/"anchovy-toggle.desktop"
            if dp.is_file(): dp.unlink()
            self.cfg["hotkey"]=""; save_config(self.cfg)
            self._hotkey_label.setText("Not set")
            self._hotkey_status.setText("Shortcut removed."); self._hotkey_status.setStyleSheet(f"color:{self._dim.name()};")
        except Exception as ex:
            self._hotkey_status.setText(f"Error: {ex}"); self._hotkey_status.setStyleSheet("color:#ff6464;")

    # ── Learning ──────────────────────────────────────────────────────────────
    def _tab_learning(self):
        tr=QHBoxLayout(); self._heading("Learned Associations"); tr.addStretch()
        cb=QLabel("Clear All"); cb.setFont(QFont("sans-serif",10))
        cb.setStyleSheet(f"color:{QColor(255,100,100).name()};"); cb.setCursor(Qt.CursorShape.PointingHandCursor)
        cb.mousePressEvent=lambda e: self._clear_learned()
        tr.addWidget(cb); self._content.addLayout(tr)
        self._sub("Anchovy learns which app you mean for each query.")
        self._learn_container=QWidget()
        self._learn_layout=QVBoxLayout(self._learn_container)
        self._learn_layout.setContentsMargins(0,0,0,0); self._learn_layout.setSpacing(2)
        self._learn_scroll=self._scroll_area(); self._learn_scroll.setWidget(self._learn_container)
        self._content.addWidget(self._learn_scroll, stretch=1)
        self._learn_empty=QLabel("No learned associations yet.\nJust use Anchovy and it learns!")
        self._learn_empty.setFont(QFont("sans-serif",10)); self._learn_empty.setStyleSheet(f"color:{self._dim.name()};")
        self._learn_empty.setAlignment(Qt.AlignmentFlag.AlignCenter); self._learn_empty.setVisible(False)
        self._content.addWidget(self._learn_empty); self._refresh_learned()

    def _refresh_learned(self):
        while self._learn_layout.count():
            item=self._learn_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        data=load_learned()
        rows=sorted([(q,a,c) for q,apps in data.items() for a,c in apps.items()],key=lambda r:r[2],reverse=True)
        if not rows:
            self._learn_empty.setVisible(True); self._learn_scroll.setVisible(False); return
        self._learn_empty.setVisible(False); self._learn_scroll.setVisible(True)
        for q,a,c in rows:
            self._learn_layout.addWidget(LearnedRow(q,a,c,self._del_learned,self._accent,self._text,self._dim))
        self._learn_layout.addStretch()

    def _del_learned(self, q, a):
        data=load_learned()
        if q in data: data[q].pop(a,None)
        if q in data and not data[q]: del data[q]
        save_learned(data); self._refresh_learned()

    def _clear_learned(self):
        save_learned({}); self._refresh_learned()

    # ── About ─────────────────────────────────────────────────────────────────
    def _tab_about(self):
        self._content.addSpacing(20)
        name_lbl=QLabel("Anchovy"); name_lbl.setFont(QFont("sans-serif",18,QFont.Weight.Bold))
        name_lbl.setStyleSheet(f"color:{self._text.name()};"); name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.addWidget(name_lbl)
        tag=QLabel("Universal app launcher · Wayland-first")
        tag.setFont(QFont("sans-serif",10)); tag.setStyleSheet(f"color:{self._dim.name()};")
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter); self._content.addWidget(tag)
        self._content.addSpacing(20)
        for label,value in [("Python",platform.python_version()),("PyQt6",PYQT_VERSION_STR),("Platform",platform.system()+" "+platform.release())]:
            row=QHBoxLayout()
            ll=QLabel(label); ll.setFont(QFont("sans-serif",10)); ll.setStyleSheet(f"color:{self._dim.name()};")
            vl=QLabel(value); vl.setFont(QFont("monospace",10,QFont.Weight.Bold)); vl.setStyleSheet(f"color:{self._text.name()};")
            row.addWidget(ll); row.addStretch(); row.addWidget(vl); self._content.addLayout(row)
        self._content.addSpacing(24)
        btn_row=QHBoxLayout(); btn_row.setSpacing(10)
        for label,action in [("Import",self._import_settings),("Export",self._export_settings),("Reset",self._reset_settings)]:
            btn=QLabel(f"  {label}  "); btn.setFixedHeight(32)
            btn.setFont(QFont("sans-serif",10,QFont.Weight.DemiBold))
            is_reset=label=="Reset"
            btn.setStyleSheet(f"color:{'#ff6464' if is_reset else self._accent.name()};"
                              f"background:rgba({'255,100,100' if is_reset else '255,255,255'},0.08);"
                              f"border-radius:6px;padding:4px 12px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.mousePressEvent=lambda e,a=action: a()
            btn_row.addWidget(btn)
        btn_row.addStretch(); self._content.addLayout(btn_row); self._content.addStretch()

    def _import_settings(self):
        path,_=QFileDialog.getOpenFileName(self,"Import Settings","","JSON (*.json)")
        if path:
            try:
                data=json.loads(Path(path).read_text())
                for k,v in DEFAULT_CONFIG.items():
                    if k not in data: data[k]=v
                self.cfg=data; save_config(self.cfg); self._refresh_colors()
                self.setStyleSheet(f"QMainWindow{{background-color:{self._bg.name()};}}")
                self.centralWidget().deleteLater(); self._build_ui()
            except: pass

    def _export_settings(self):
        path,_=QFileDialog.getSaveFileName(self,"Export Settings","anchovy-settings.json","JSON (*.json)")
        if path: Path(path).write_text(json.dumps(self.cfg,indent=2))

    def _reset_settings(self):
        self.cfg=dict(DEFAULT_CONFIG); save_config(self.cfg); self._refresh_colors()
        self.setStyleSheet(f"QMainWindow{{background-color:{self._bg.name()};}}")
        self.centralWidget().deleteLater(); self._build_ui()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SettingsWindow()
    win.show()
    sys.exit(app.exec())
