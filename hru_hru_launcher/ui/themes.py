# hru_hru_launcher/ui/themes.py
from PySide6.QtGui import QColor

def lighten_color(hex_color, amount=0.15):
    try:
        color = QColor(hex_color)
        h, s, l, a = color.getHslF()
        l = min(1.0, l + amount)
        return QColor.fromHslF(h, s, l, a).name()
    except:
        return hex_color

def darken_color(hex_color, amount=0.08):
    try:
        color = QColor(hex_color)
        h, s, l, a = color.getHslF()
        l = max(0.0, l - amount)
        return QColor.fromHslF(h, s, l, a).name()
    except:
        return hex_color

def hex_to_rgba(hex_color, alpha=0.15):
    try:
        color = QColor(hex_color)
        r, g, b = color.red(), color.green(), color.blue()
        return f"rgba({r},{g},{b},{alpha})"
    except:
        return hex_color

# ──────────────────────────────────────────────────────────────────────────────
# PREMIUM DARK THEME — version 3.0
# Inspired by Modrinth App, Prism Launcher, and modern desktop design
# ──────────────────────────────────────────────────────────────────────────────
def get_dark_theme(accent_color="#1DB954"):
    ah   = lighten_color(accent_color, 0.08)   # accent hover
    ad   = darken_color(accent_color, 0.06)     # accent dark/press
    ag   = hex_to_rgba(accent_color, 0.28)      # accent glow
    as_  = hex_to_rgba(accent_color, 0.12)      # accent subtle bg
    ab   = hex_to_rgba(accent_color, 0.18)      # accent border

    BG      = "#0c0c12"
    SURFACE = "#121218"
    CARD    = "#18181f"
    CARD2   = "#1e1e28"
    BORDER  = "rgba(255,255,255,0.07)"
    BORDER2 = "rgba(255,255,255,0.12)"
    TEXT    = "#e8e8f0"
    TEXT_DIM= "#6b6b80"
    TEXT_MID= "#a0a0b8"

    return f"""
/* ═══════════════════════════════════════════════════════════
   ROOT WINDOW
══════════════════════════════════════════════════════════ */
QMainWindow, QDialog {{
    background: {BG};
}}

#container {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {SURFACE},
        stop:0.5 #111119,
        stop:1 {BG}
    );
    border: 1px solid {BORDER};
    border-radius: 18px;
}}

/* ═══════════════════════════════════════════════════════════
   TITLE BAR
══════════════════════════════════════════════════════════ */
#titleBar {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {CARD2},
        stop:1 #161620
    );
    border-bottom: 1px solid {BORDER};
    border-top-left-radius: 18px;
    border-top-right-radius: 18px;
}}

#titleLabel {{
    color: {TEXT};
    font-weight: bold;
    letter-spacing: 1px;
}}

/* Window buttons */
#closeButton {{
    background: #e53e3e;
    color: transparent;
    border: none;
    border-radius: 16px;
    font-size: 11pt;
    font-weight: bold;
}}
#closeButton:hover {{
    background: #fc5252;
    color: white;
}}
#minimizeButton {{
    background: rgba(255,255,255,0.10);
    color: transparent;
    border: none;
    border-radius: 16px;
    font-size: 11pt;
    font-weight: bold;
}}
#minimizeButton:hover {{
    background: rgba(255,255,255,0.18);
    color: {TEXT};
}}

/* ═══════════════════════════════════════════════════════════
   LEFT PANEL
══════════════════════════════════════════════════════════ */
#mainPanel {{
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 {CARD},
        stop:1 rgba(18,18,26,0.95)
    );
    border-right: 1px solid {BORDER};
    border-radius: 0px;
}}

#sectionLabel {{
    color: {TEXT_DIM};
    font-size: 8pt;
    font-weight: bold;
    letter-spacing: 2px;
    text-transform: uppercase;
}}

/* ═══════════════════════════════════════════════════════════
   PILL VERSION BUTTONS
══════════════════════════════════════════════════════════ */
#pillButton {{
    background: rgba(255,255,255,0.05);
    color: {TEXT_DIM};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 7px 18px;
    font-weight: bold;
    font-size: 9pt;
    min-width: 70px;
}}
#pillButton:hover {{
    background: rgba(255,255,255,0.09);
    color: {TEXT_MID};
    border-color: rgba(255,255,255,0.14);
}}
#pillButton:checked {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent_color}, stop:1 {ah}
    );
    color: #060608;
    border: none;
}}

/* ═══════════════════════════════════════════════════════════
   GLOBAL LABELS
══════════════════════════════════════════════════════════ */
QLabel {{
    color: {TEXT_MID};
    background: transparent;
}}
QRadioButton, QCheckBox {{
    color: {TEXT_MID};
    background: transparent;
    spacing: 8px;
}}

/* ═══════════════════════════════════════════════════════════
   INPUTS
══════════════════════════════════════════════════════════ */
QComboBox, QLineEdit {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 10px 14px;
    color: {TEXT};
    font-size: 10pt;
    selection-background-color: {as_};
}}
QComboBox:hover, QLineEdit:hover {{
    border-color: rgba(255,255,255,0.16);
    background: rgba(255,255,255,0.06);
}}
QLineEdit:focus {{
    border: 1.5px solid {accent_color};
    background: rgba(255,255,255,0.06);
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
    subcontrol-origin: padding;
    subcontrol-position: right center;
}}
QComboBox QAbstractItemView {{
    background: #1a1a25;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 10px;
    color: {TEXT};
    selection-background-color: {as_};
    padding: 4px;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    padding: 8px 12px;
    border-radius: 8px;
    min-height: 28px;
}}
QComboBox QAbstractItemView::item:selected {{
    background: {as_};
    color: {accent_color};
}}

/* ═══════════════════════════════════════════════════════════
   BUTTONS (generic)
══════════════════════════════════════════════════════════ */
QPushButton {{
    background: {accent_color};
    color: #080810;
    border: none;
    border-radius: 10px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 10pt;
    outline: none;
}}
QPushButton:hover {{
    background: {ah};
}}
QPushButton:pressed {{
    background: {ad};
}}
QPushButton:disabled {{
    background: rgba(255,255,255,0.06);
    color: rgba(255,255,255,0.22);
}}

/* ═══════════════════════════════════════════════════════════
   LAUNCH BUTTON — hero element
══════════════════════════════════════════════════════════ */
#launchButton {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent_color},
        stop:1 {ah}
    );
    color: #060608;
    border-radius: 12px;
    font-size: 12pt;
    font-weight: bold;
    letter-spacing: 3px;
    border: none;
}}
#launchButton:hover {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {ah},
        stop:1 {lighten_color(accent_color, 0.16)}
    );
}}
#launchButton:pressed {{
    background: {ad};
    letter-spacing: 2px;
}}
#launchButton:disabled {{
    background: rgba(255,255,255,0.07);
    color: rgba(255,255,255,0.25);
}}

/* ═══════════════════════════════════════════════════════════
   CANCEL BUTTON
══════════════════════════════════════════════════════════ */
#cancelButton {{
    background: rgba(220,50,50,0.80);
    color: white;
    border-radius: 10px;
    border: 1px solid rgba(255,80,80,0.30);
}}
#cancelButton:hover {{
    background: rgba(240,60,60,0.95);
}}

/* ═══════════════════════════════════════════════════════════
   PROGRESS BAR
══════════════════════════════════════════════════════════ */
QProgressBar {{
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    background: rgba(255,255,255,0.04);
    color: {TEXT};
    font-weight: bold;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {accent_color},
        stop:1 {ah}
    );
    border-radius: 9px;
}}

/* ═══════════════════════════════════════════════════════════
   TAB WIDGET
══════════════════════════════════════════════════════════ */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 14px;
    background: rgba(255,255,255,0.015);
    top: -1px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 10px 20px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: bold;
    font-size: 9pt;
}}
QTabBar::tab:selected {{
    color: {accent_color};
    border-bottom: 2px solid {accent_color};
    background: {as_};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}
QTabBar::tab:hover:!selected {{
    background: rgba(255,255,255,0.04);
    color: {TEXT_MID};
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

/* ── Mods sub-tabs ── */
#modsSubTabs::pane {{
    border: none;
    background: transparent;
}}
#modsSubTabs QTabBar::tab {{
    background: rgba(255,255,255,0.04);
    color: {TEXT_DIM};
    padding: 7px 22px;
    border-radius: 20px;
    margin-right: 6px;
    border: 1px solid rgba(255,255,255,0.06);
    border-bottom: none;
    font-size: 9pt;
    font-weight: bold;
}}
#modsSubTabs QTabBar::tab:selected {{
    background: {accent_color};
    color: #060608;
    border: none;
}}
#modsSubTabs QTabBar::tab:hover:!selected {{
    background: rgba(255,255,255,0.08);
    color: {TEXT};
}}

/* ═══════════════════════════════════════════════════════════
   SCROLLBAR
══════════════════════════════════════════════════════════ */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 5px;
    margin: 6px 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.12);
    min-height: 28px;
    border-radius: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {hex_to_rgba(accent_color, 0.60)};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 5px;
    margin: 2px 6px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.12);
    min-width: 28px;
    border-radius: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {hex_to_rgba(accent_color, 0.60)};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ═══════════════════════════════════════════════════════════
   CHECKBOXES / RADIO
══════════════════════════════════════════════════════════ */
QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid rgba(255,255,255,0.15);
    background: rgba(255,255,255,0.04);
}}
QCheckBox::indicator {{ border-radius: 5px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {accent_color};
    border-color: {accent_color};
    image: url(""); /* checkmark via background */
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {accent_color};
}}

/* ═══════════════════════════════════════════════════════════
   SLIDER
══════════════════════════════════════════════════════════ */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: rgba(255,255,255,0.08);
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {accent_color}, stop:1 {ah});
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT};
    border: 2px solid {accent_color};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {accent_color};
    border-color: {ah};
}}

/* ═══════════════════════════════════════════════════════════
   CONSOLE / TEXT EDIT
══════════════════════════════════════════════════════════ */
QTextEdit {{
    background: #06060e;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    color: #50fa7b;
    padding: 12px;
    font-family: 'Consolas', 'Cascadia Code', 'Courier New', monospace;
    font-size: 9pt;
    selection-background-color: {as_};
}}

/* ═══════════════════════════════════════════════════════════
   MOD SEARCH INPUT
══════════════════════════════════════════════════════════ */
#modSearchInput {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 22px;
    padding: 9px 20px;
    color: {TEXT};
    font-size: 10pt;
}}
#modSearchInput:focus {{
    border: 1.5px solid {accent_color};
    background: rgba(255,255,255,0.06);
}}

/* ═══════════════════════════════════════════════════════════
   MOD LIST
══════════════════════════════════════════════════════════ */
#modList {{
    background: transparent;
    border: none;
    outline: none;
}}
#modList::item {{
    background: transparent;
    border: none;
}}
#modList::item:selected {{
    background: transparent;
}}

/* ═══════════════════════════════════════════════════════════
   SPECIALTY LABELS
══════════════════════════════════════════════════════════ */
#errorLabel {{
    color: #f87171;
    font-weight: bold;
    font-size: 9pt;
}}
#versionStatusLabel {{
    color: #34d399;
    font-size: 8pt;
}}
#totalSizeLabel {{
    color: #a78bfa;
    font-size: 9pt;
}}
#wipLabel {{
    color: rgba(255,255,255,0.25);
    font-size: 14pt;
}}

/* ═══════════════════════════════════════════════════════════
   SPECIALTY BUTTONS
══════════════════════════════════════════════════════════ */
#openModsFolderButton, #openModpacksFolderButton {{
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    color: {TEXT_MID};
    padding: 7px 14px;
    font-size: 9pt;
}}
#openModsFolderButton:hover, #openModpacksFolderButton:hover {{
    background: rgba(255,255,255,0.10);
    color: {TEXT};
}}

#deleteSelectedButton {{
    background: rgba(239,68,68,0.75);
    color: white;
    border: none;
    border-radius: 9px;
    padding: 7px 16px;
    font-weight: bold;
    font-size: 9pt;
}}
#deleteSelectedButton:hover {{
    background: rgba(248,79,57,0.95);
}}
#deleteSelectedButton:disabled {{
    background: rgba(255,255,255,0.05);
    color: rgba(255,255,255,0.18);
}}

#colorPreview {{
    border-radius: 8px;
    border: 2px solid rgba(255,255,255,0.12);
}}

QPushButton#advancedSettingsButton {{
    background: rgba(255,255,255,0.06);
    color: {TEXT_DIM};
    border: 1px solid rgba(255,255,255,0.09);
    font-size: 9pt;
}}
QPushButton#advancedSettingsButton:hover {{
    background: rgba(255,255,255,0.10);
    color: {TEXT};
}}

/* ═══════════════════════════════════════════════════════════
   SIZE GRIP
══════════════════════════════════════════════════════════ */
QSizeGrip {{
    background: transparent;
    image: none;
    width: 14px;
    height: 14px;
}}

/* ═══════════════════════════════════════════════════════════
   PAGINATION BUTTONS  ‹ ›
══════════════════════════════════════════════════════════ */
#paginationButton {{
    background: rgba(255,255,255,0.06);
    color: {TEXT_MID};
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    font-size: 14pt;
    font-weight: bold;
    padding: 0px;
}}
#paginationButton:hover {{
    background: rgba(255,255,255,0.12);
    color: {TEXT};
    border-color: rgba(255,255,255,0.16);
}}
#paginationButton:disabled {{
    background: rgba(255,255,255,0.03);
    color: rgba(255,255,255,0.15);
    border-color: rgba(255,255,255,0.04);
}}

/* ═══════════════════════════════════════════════════════════
   WINDOW CONTROL BUTTONS
══════════════════════════════════════════════════════════ */
#closeButton {{
    background: #e53e3e;
    color: white;
    border: none;
    border-radius: 16px;
    font-size: 10pt;
    font-weight: bold;
}}
#closeButton:hover {{
    background: #fc5252;
}}
#minimizeButton {{
    background: rgba(255,255,255,0.10);
    color: {TEXT_MID};
    border: none;
    border-radius: 16px;
    font-size: 10pt;
    font-weight: bold;
}}
#minimizeButton:hover {{
    background: rgba(255,255,255,0.18);
    color: {TEXT};
}}
"""