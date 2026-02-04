# BEC_ThemePack_AllInOne.py
# Drop into: All in One 1.0.0/BetterEditPMF/BEC_ThemePack_AllInOne.py
#
# Install (PowerShell):
#   cd "C:\Users\lrazy\Documents\All in One 1.0.0\BetterEditPMF"
#   python BEC_ThemePack_AllInOne.py --install
#
# Use in AI1 terminal:
#   plugins
#   theme list
#   theme apply bec-style
#   theme editor
#
# Notes:
# - Some UI text like "WinXP-ish ..." is in AI1 core. This plugin tries to patch it at runtime by scanning labels.
# - Icon on taskbar can be cached by Windows. This plugin applies it repeatedly early; for 100% reliability, also set icon in core.

from __future__ import annotations

import os
import json
import time
from typing import Dict, Optional, Any

from PySide6 import QtCore, QtGui, QtWidgets

PMF_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(PMF_DIR, ".."))
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")

DATA_DIR = os.path.join(PMF_DIR, "data")
THEMES_DIR = os.path.join(PMF_DIR, "themes")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(THEMES_DIR, exist_ok=True)

ICON_DEFAULT = os.path.join(PMF_DIR, "BECai1icon.png")
STATE_JSON = os.path.join(DATA_DIR, "bec_theme_state.json")

LOADER_PATH = os.path.join(PLUGINS_DIR, "BetterEditPMF_BECThemePack_loader.py")

PLUGIN_NAME = "BEC ThemePack"
AUTHOR = "BEC-Studios"

# ---------------------- built-in themes ----------------------
def _qss_bec_style() -> str:
    # macOS-26-ish but "BEC-Style"
    return r"""
* { font-family: "Inter","Segoe UI","Helvetica Neue",Arial; font-size: 10.5pt; }
QWidget { color: #ECECEC; background: #0E0F12; }
QMainWindow, QDialog { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #171924, stop:1 #0E0F12); }

QFrame, QGroupBox {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  background: rgba(255,255,255,0.06);
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 14px;
  padding: 9px 12px;
  background: rgba(255,255,255,0.07);
  selection-background-color: rgba(90,160,255,0.45);
}

QPushButton {
  border: 1px solid rgba(255,255,255,0.16);
  border-radius: 14px;
  padding: 9px 12px;
  background: rgba(255,255,255,0.08);
}
QPushButton:hover { background: rgba(255,255,255,0.13); }
QPushButton:pressed { background: rgba(255,255,255,0.18); }

QTabWidget::pane {
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 18px;
  background: rgba(255,255,255,0.04);
}
QTabBar::tab {
  padding: 9px 14px;
  border-radius: 14px;
  margin: 7px 7px 0 0;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
}
QTabBar::tab:selected { background: rgba(255,255,255,0.14); }

QScrollBar:vertical { background: transparent; width: 12px; margin: 10px 5px 10px 5px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.18); border-radius: 6px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.28); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: transparent; }
"""

def _qss_aero_light() -> str:
    # Win7 Aero Light
    return r"""
* { font-family: "Segoe UI"; font-size: 10.5pt; }
QWidget { color: #101418; background: #EAF3FF; }
QMainWindow, QDialog { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #F7FBFF, stop:1 #D9ECFF); }

QFrame, QGroupBox {
  border: 1px solid rgba(40,120,200,0.35);
  border-radius: 16px;
  background: rgba(255,255,255,0.78);
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(40,120,200,0.35);
  border-radius: 14px;
  padding: 9px 12px;
}

QPushButton {
  background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(255,255,255,0.98), stop:1 rgba(200,230,255,0.88));
  border: 1px solid rgba(40,120,200,0.35);
  border-radius: 14px;
  padding: 9px 12px;
}
QPushButton:hover { background: rgba(220,245,255,0.96); }
QPushButton:pressed { background: rgba(195,228,255,0.95); }

QTabWidget::pane {
  border: 1px solid rgba(40,120,200,0.30);
  border-radius: 16px;
  background: rgba(255,255,255,0.70);
}
QTabBar::tab {
  padding: 9px 14px;
  border-radius: 14px;
  margin: 7px 7px 0 0;
  background: rgba(255,255,255,0.72);
  border: 1px solid rgba(40,120,200,0.25);
}
QTabBar::tab:selected { background: rgba(220,245,255,0.96); }
"""

def _qss_aero_dark() -> str:
    # Win7 Aero Dark
    return r"""
* { font-family: "Segoe UI"; font-size: 10.5pt; }
QWidget { color: #ECECEC; background: #0B0F14; }
QMainWindow, QDialog { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #162637, stop:1 #0B0F14); }

QFrame, QGroupBox {
  border: 1px solid rgba(120,190,255,0.25);
  border-radius: 16px;
  background: rgba(255,255,255,0.06);
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(120,190,255,0.25);
  border-radius: 14px;
  padding: 9px 12px;
}

QPushButton {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(120,190,255,0.25);
  border-radius: 14px;
  padding: 9px 12px;
}
QPushButton:hover { background: rgba(255,255,255,0.14); }
QPushButton:pressed { background: rgba(255,255,255,0.18); }

QTabWidget::pane { border: 1px solid rgba(120,190,255,0.18); border-radius: 16px; background: rgba(255,255,255,0.04); }
QTabBar::tab { padding: 9px 14px; margin: 7px 7px 0 0; border-radius: 14px; background: rgba(255,255,255,0.06); border: 1px solid rgba(120,190,255,0.18); }
QTabBar::tab:selected { background: rgba(255,255,255,0.16); }
"""

def _qss_midnight() -> str:
    return r"""
* { font-family: "Segoe UI"; font-size: 10.5pt; }
QWidget { color: #E8E8E8; background: #0D0E12; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox { background:#141620; border:1px solid #2A2F45; border-radius: 12px; padding: 9px 12px; }
QPushButton { background:#171A27; border:1px solid #2A2F45; border-radius: 12px; padding: 9px 12px; }
QPushButton:hover { background:#1E2234; }
QTabWidget::pane { border: 1px solid #2A2F45; border-radius: 16px; }
QTabBar::tab { background:#141620; border:1px solid #2A2F45; border-radius: 12px; padding: 9px 14px; margin: 7px 7px 0 0; }
QTabBar::tab:selected { background:#1E2234; }
"""

def _qss_snow() -> str:
    return r"""
* { font-family: "Segoe UI"; font-size: 10.5pt; }
QWidget { color: #121212; background: #F5F7FB; }
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox { background:#FFFFFF; border:1px solid #D6DAE6; border-radius: 12px; padding: 9px 12px; }
QPushButton { background:#FFFFFF; border:1px solid #D6DAE6; border-radius: 12px; padding: 9px 12px; }
QPushButton:hover { background:#EFF2FA; }
QTabWidget::pane { border: 1px solid #D6DAE6; border-radius: 16px; background:#FFFFFF; }
QTabBar::tab { background:#FFFFFF; border:1px solid #D6DAE6; border-radius: 12px; padding: 9px 14px; margin: 7px 7px 0 0; }
QTabBar::tab:selected { background:#EAF0FF; }
"""

THEMES: Dict[str, Dict[str, str]] = {
    "bec-style": {"label": "BEC-Style (macOS-26)", "qss": _qss_bec_style()},
    "win7-aero-light": {"label": "Win7 Aero Light", "qss": _qss_aero_light()},
    "win7-aero-dark": {"label": "Win7 Aero Dark", "qss": _qss_aero_dark()},
    "midnight": {"label": "Midnight", "qss": _qss_midnight()},
    "snow": {"label": "Snow (Light)", "qss": _qss_snow()},
}

# ---------------------- state ----------------------
def _load_state() -> dict:
    if not os.path.isfile(STATE_JSON):
        return {}
    try:
        with open(STATE_JSON, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save_state(d: dict) -> None:
    try:
        with open(STATE_JSON, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ---------------------- safe host wrappers ----------------------
def _safe_register_command(host, **kwargs) -> bool:
    try:
        host.register_command(**kwargs)
        return True
    except Exception as e:
        # prevents "Command exists: hello" and similar from killing plugin reload
        if "Command exists" in str(e):
            return False
        raise

def _safe_register_action(host, *args, **kwargs) -> bool:
    try:
        host.register_action(*args, **kwargs)
        return True
    except Exception:
        return False

# ---------------------- performance / apply helpers ----------------------
def _boost_flags(app: QtWidgets.QApplication) -> None:
    # safe anti-stutter flags
    try:
        app.setEffectEnabled(QtCore.Qt.UIEffect.UI_AnimateMenu, False)
        app.setEffectEnabled(QtCore.Qt.UIEffect.UI_AnimateCombo, False)
        app.setEffectEnabled(QtCore.Qt.UIEffect.UI_AnimateTooltip, False)
    except Exception:
        pass

def _apply_icon(app: QtWidgets.QApplication, icon_path: str) -> bool:
    if not icon_path or not os.path.isfile(icon_path):
        return False
    ico = QtGui.QIcon(icon_path)
    app.setWindowIcon(ico)
    for w in app.topLevelWidgets():
        try:
            w.setWindowIcon(ico)
        except Exception:
            pass
    return True

def _apply_stylesheet(app: QtWidgets.QApplication, qss: str) -> None:
    tops = list(app.topLevelWidgets())
    for w in tops:
        try: w.setUpdatesEnabled(False)
        except Exception: pass
    try:
        app.setStyle("Fusion")
        app.setStyleSheet(qss)
    finally:
        for w in tops:
            try:
                w.setUpdatesEnabled(True)
                w.update()
            except Exception:
                pass

def _try_patch_header_text(app: QtWidgets.QApplication) -> None:
    # Removes "-ish" / "WinXP-ish" visible label by scanning labels & replacing known strings.
    # Also tries to move subtitle into the title input placeholder ("text in der box").
    for w in app.topLevelWidgets():
        for lab in w.findChildren(QtWidgets.QLabel):
            t = (lab.text() or "").strip()
            low = t.lower()
            if "winxp-ish" in low or "theme-ish" in low or low.endswith("-ish"):
                new = t
                new = new.replace("WinXP-ish", "BEC-Style")
                new = new.replace("winxp-ish", "BEC-Style")
                new = new.replace("Theme-ish", "")
                new = new.replace("theme-ish", "")
                new = new.replace("-ish", "")
                new = " ".join(new.split()).strip("• -")
                # hide if it becomes empty
                if not new:
                    lab.hide()
                else:
                    lab.setText(new)

        # "Text soll in der Box sein": find a QLineEdit near top and set placeholder with subtitle
        # heuristic: first QLineEdit that is wide
        edits = [e for e in w.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
        if edits:
            # pick the widest
            edits.sort(key=lambda e: e.width(), reverse=True)
            title_edit = edits[0]
            # if placeholder empty, set a modern line
            ph = title_edit.placeholderText().strip()
            if not ph:
                title_edit.setPlaceholderText("All in 1 • BEC-Style • Terminal • Plugins")
            # optional: if there is a label that looks like subtitle, hide it and migrate into placeholder
            for lab in w.findChildren(QtWidgets.QLabel):
                t = (lab.text() or "").strip()
                if ("terminal" in t.lower() and "plugins" in t.lower()) or ("v" in t.lower() and "plugins" in t.lower()):
                    # move into placeholder, then hide label
                    title_edit.setPlaceholderText(t.replace("WinXP-ish", "BEC-Style").replace("-ish", ""))
                    lab.hide()
                    break

# ---------------------- custom theme (json -> qss) ----------------------
def _qss_from_custom(cfg: dict) -> str:
    # simple generator; editor writes these configs
    bg = cfg.get("bg", "#0E0F12")
    fg = cfg.get("fg", "#ECECEC")
    accent = cfg.get("accent", "#5AA0FF")
    radius = int(cfg.get("radius", 14))
    font = cfg.get("font", "Segoe UI")
    bgimg = cfg.get("bg_image", "")

    bgimg_qss = ""
    if bgimg and os.path.isfile(bgimg):
        bgimg_qss = f"QMainWindow {{ background-image: url('{bgimg.replace('\\','/')}'); background-position:center; background-repeat:no-repeat; }}\n"

    return f"""
* {{ font-family: "{font}"; font-size: 10.5pt; }}
QWidget {{ color: {fg}; background: {bg}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
  border: 1px solid rgba(255,255,255,0.16);
  border-radius: {radius}px;
  padding: 9px 12px;
  background: rgba(255,255,255,0.07);
  selection-background-color: {accent};
}}
QPushButton {{
  border: 1px solid rgba(255,255,255,0.16);
  border-radius: {radius}px;
  padding: 9px 12px;
  background: rgba(255,255,255,0.08);
}}
QPushButton:hover {{ background: rgba(255,255,255,0.13); }}
QTabWidget::pane {{
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: {radius+4}px;
  background: rgba(255,255,255,0.04);
}}
QTabBar::tab {{
  padding: 9px 14px;
  border-radius: {radius}px;
  margin: 7px 7px 0 0;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
}}
QTabBar::tab:selected {{ background: rgba(255,255,255,0.14); }}
{bgimg_qss}
"""

# ---------------------- Theme Editor UI ----------------------
class ThemeEditor(QtWidgets.QDialog):
    def __init__(self, app: QtWidgets.QApplication, parent=None):
        super().__init__(parent)
        self._app = app
        self.setWindowTitle("BEC Theme Editor (Ultra)")
        self.resize(1060, 720)

        self.cfg = {
            "bg": "#0E0F12",
            "fg": "#ECECEC",
            "accent": "#5AA0FF",
            "radius": 14,
            "font": "Segoe UI",
            "bg_image": "",
            "icon": ICON_DEFAULT if os.path.isfile(ICON_DEFAULT) else "",
        }

        self.cmb_presets = QtWidgets.QComboBox()
        self.cmb_presets.addItem("Built-in: BEC-Style (macOS-26)", "bec-style")
        self.cmb_presets.addItem("Built-in: Win7 Aero Light", "win7-aero-light")
        self.cmb_presets.addItem("Built-in: Win7 Aero Dark", "win7-aero-dark")
        self.cmb_presets.addItem("Built-in: Midnight", "midnight")
        self.cmb_presets.addItem("Built-in: Snow (Light)", "snow")
        self.cmb_presets.addItem("Custom Generator (this editor)", "__custom__")

        self.btn_apply = QtWidgets.QPushButton("Apply Live")
        self.btn_save_theme = QtWidgets.QPushButton("Save Preset (JSON)")
        self.btn_load_theme = QtWidgets.QPushButton("Load Preset (JSON)")
        self.btn_export_qss = QtWidgets.QPushButton("Export QSS")

        # color controls
        self.btn_bg = QtWidgets.QPushButton("Background Color")
        self.btn_fg = QtWidgets.QPushButton("Text Color")
        self.btn_ac = QtWidgets.QPushButton("Accent Color")

        self.spin_radius = QtWidgets.QSpinBox()
        self.spin_radius.setRange(6, 28)
        self.spin_radius.setValue(self.cfg["radius"])

        self.btn_font = QtWidgets.QPushButton("Font…")
        self.btn_bgimg = QtWidgets.QPushButton("Background Image… (optional)")
        self.btn_icon = QtWidgets.QPushButton("Custom Icon… (png)")

        # live qss box
        self.qss_view = QtWidgets.QPlainTextEdit()
        self.qss_view.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.qss_view.setPlaceholderText("Generated QSS preview…")

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Preset:"))
        top.addWidget(self.cmb_presets, 1)
        top.addWidget(self.btn_apply)
        top.addWidget(self.btn_save_theme)
        top.addWidget(self.btn_load_theme)
        top.addWidget(self.btn_export_qss)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(self.btn_bg, 0, 0)
        grid.addWidget(self.btn_fg, 0, 1)
        grid.addWidget(self.btn_ac, 0, 2)
        grid.addWidget(QtWidgets.QLabel("Corner radius:"), 1, 0)
        grid.addWidget(self.spin_radius, 1, 1)
        grid.addWidget(self.btn_font, 1, 2)
        grid.addWidget(self.btn_bgimg, 2, 0, 1, 2)
        grid.addWidget(self.btn_icon, 2, 2)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(grid)
        lay.addWidget(self.qss_view, 1)

        self.cmb_presets.currentIndexChanged.connect(self._preset_changed)
        self.btn_apply.clicked.connect(self._apply)
        self.btn_bg.clicked.connect(lambda: self._pick_color("bg"))
        self.btn_fg.clicked.connect(lambda: self._pick_color("fg"))
        self.btn_ac.clicked.connect(lambda: self._pick_color("accent"))
        self.spin_radius.valueChanged.connect(self._update_qss)
        self.btn_font.clicked.connect(self._pick_font)
        self.btn_bgimg.clicked.connect(self._pick_bgimg)
        self.btn_icon.clicked.connect(self._pick_icon)
        self.btn_save_theme.clicked.connect(self._save_json)
        self.btn_load_theme.clicked.connect(self._load_json)
        self.btn_export_qss.clicked.connect(self._export_qss)

        self._preset_changed()

    def _preset_changed(self):
        key = self.cmb_presets.currentData()
        if key in THEMES:
            qss = THEMES[key]["qss"]
            self.qss_view.setPlainText(qss)
        else:
            self._update_qss()

    def _update_qss(self):
        self.cfg["radius"] = int(self.spin_radius.value())
        qss = _qss_from_custom(self.cfg)
        self.qss_view.setPlainText(qss)

    def _pick_color(self, which: str):
        cur = QtGui.QColor(self.cfg.get(which, "#ffffff"))
        col = QtWidgets.QColorDialog.getColor(cur, self, f"Pick {which}")
        if col.isValid():
            self.cfg[which] = col.name()
            self._update_qss()

    def _pick_font(self):
        ok, font = QtWidgets.QFontDialog.getFont(self.font(), self, "Pick Font")
        if ok:
            self.cfg["font"] = font.family()
            self._update_qss()

    def _pick_bgimg(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Pick background image", PMF_DIR, "Images (*.png *.jpg *.jpeg *.webp)")
        if fn:
            self.cfg["bg_image"] = fn
            self._update_qss()

    def _pick_icon(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Pick icon (png)", PMF_DIR, "PNG (*.png)")
        if fn:
            self.cfg["icon"] = fn

    def _apply(self):
        key = self.cmb_presets.currentData()
        if key in THEMES:
            qss = THEMES[key]["qss"]
        else:
            qss = self.qss_view.toPlainText()

        _apply_stylesheet(self._app, qss)

        # icon
        icon_path = self.cfg.get("icon") or ICON_DEFAULT
        _apply_icon(self._app, icon_path)

        # patch header text
        _try_patch_header_text(self._app)

        # persist
        if key in THEMES:
            _save_state({"type": "builtin", "name": key, "icon": icon_path})
        else:
            _save_state({"type": "customgen", "config": self.cfg, "icon": icon_path})

    def _save_json(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save preset (json)", THEMES_DIR, "JSON (*.json)")
        if not fn:
            return
        data = {"type": "bec_preset", "config": self.cfg, "qss": self.qss_view.toPlainText()}
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_json(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load preset (json)", THEMES_DIR, "JSON (*.json)")
        if not fn:
            return
        try:
            with open(fn, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = data.get("config", {})
            if isinstance(cfg, dict):
                self.cfg.update(cfg)
                self.spin_radius.setValue(int(self.cfg.get("radius", 14)))
                qss = data.get("qss") or _qss_from_custom(self.cfg)
                self.qss_view.setPlainText(qss)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Load error", str(e))

    def _export_qss(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export QSS", THEMES_DIR, "QSS (*.qss)")
        if not fn:
            return
        with open(fn, "w", encoding="utf-8") as f:
            f.write(self.qss_view.toPlainText())

# ---------------------- runtime patch timer (early icon + text fixes) ----------------------
class _EarlyPatch(QtCore.QObject):
    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app
        self.start = time.time()
        self._tick = QtCore.QTimer(self)
        self._tick.setInterval(250)
        self._tick.timeout.connect(self._run)
        self._tick.start()

    def _run(self):
        # run for first ~6 seconds; helps beat Windows icon caching / late window creation
        try:
            st = _load_state()
            icon = st.get("icon") or ICON_DEFAULT
            _apply_icon(self.app, icon)
            _try_patch_header_text(self.app)
        except Exception:
            pass
        if time.time() - self.start > 6.0:
            self._tick.stop()

# ---------------------- plugin entry: register(host) ----------------------
def register(host):
    app = QtWidgets.QApplication.instance()
    if not app:
        return

    _boost_flags(app)

    # apply last state
    st = _load_state()
    icon_path = st.get("icon") or ICON_DEFAULT
    _apply_icon(app, icon_path)

    try:
        if st.get("type") == "builtin" and st.get("name") in THEMES:
            _apply_stylesheet(app, THEMES[st["name"]]["qss"])
        elif st.get("type") == "customgen" and isinstance(st.get("config"), dict):
            cfg = st["config"]
            _apply_stylesheet(app, _qss_from_custom(cfg))
    except Exception:
        pass

    # early patcher (icon + text)
    _EarlyPatch(app)

    def theme_cmd(ctx, argv):
        if not argv or argv[0].lower() in ("help", "-h", "/?"):
            items = "\n".join([f"{k:18}  {THEMES[k]['label']}" for k in THEMES])
            return (
                "theme list\n"
                "theme apply <key>\n"
                "theme editor\n"
                "theme icon <path_to_png>\n"
                "\nBuilt-in:\n" + items
            )

        sub = argv[0].lower()

        if sub == "list":
            return "\n".join([f"{k:18}  {THEMES[k]['label']}" for k in THEMES])

        if sub == "apply":
            if len(argv) < 2:
                return "Usage: theme apply <key>"
            key = argv[1].lower()
            if key not in THEMES:
                return "Unknown key. theme list"
            _apply_stylesheet(app, THEMES[key]["qss"])
            _apply_icon(app, icon_path)
            _try_patch_header_text(app)
            _save_state({"type": "builtin", "name": key, "icon": icon_path})
            return f"OK: {THEMES[key]['label']}"

        if sub == "editor":
            ThemeEditor(app).exec()
            return "Editor closed."

        if sub == "icon":
            if len(argv) < 2:
                return "Usage: theme icon <path_to_png>"
            p = " ".join(argv[1:]).strip('"')
            ok = _apply_icon(app, p)
            if ok:
                st = _load_state()
                st["icon"] = p
                _save_state(st)
                return "OK icon set."
            return "Icon not found."

        return "Unknown. theme help"

    _safe_register_command(
        host,
        name="theme",
        help="BEC-Style (macOS-26), Win7 Aero Light/Dark, Ultra Editor, icon + runtime UI patches",
        usage="theme help",
        handler=theme_cmd,
        aliases=["themes", "becstyle"],
        category="ui",
    )

    # quick tool buttons (if supported)
    def _btn(key: str):
        def go():
            _apply_stylesheet(app, THEMES[key]["qss"])
            _try_patch_header_text(app)
            st = _load_state()
            _save_state({"type": "builtin", "name": key, "icon": st.get("icon") or ICON_DEFAULT})
        return go

    _safe_register_action(host, "Theme: BEC-Style", "BEC-Style (macOS-26)", _btn("bec-style"))
    _safe_register_action(host, "Theme: Win7 Aero Light", "Win7 Aero Light", _btn("win7-aero-light"))
    _safe_register_action(host, "Theme: Win7 Aero Dark", "Win7 Aero Dark", _btn("win7-aero-dark"))
    _safe_register_action(host, "Theme: Editor", "Open BEC Theme Editor", lambda: ThemeEditor(app).exec())

# ---------------------- installer ----------------------
def _install_loader() -> None:
    os.makedirs(PLUGINS_DIR, exist_ok=True)
    rel = os.path.basename(__file__)
    loader = f"""# Auto-generated loader (BEC-Studios)
import os, sys
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PMF = os.path.join(BASE, "BetterEditPMF")
if PMF not in sys.path:
    sys.path.insert(0, PMF)
from {os.path.splitext(rel)[0]} import register
"""
    with open(LOADER_PATH, "w", encoding="utf-8") as f:
        f.write(loader)

def main():
    import sys
    if "--install" in sys.argv:
        _install_loader()
        print("[OK] Loader installed:", LOADER_PATH)
        print("Start AI1 -> in AI1 terminal: plugins")
        return 0
    print("Run with --install to install loader.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
