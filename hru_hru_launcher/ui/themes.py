from PySide6.QtGui import QColor

def lighten_color(hex_color, amount=0.15):
    try:
        color = QColor(hex_color)
        h, s, l, a = color.getHslF()
        l = min(1.0, l + amount) 
        return QColor.fromHslF(h, s, l, a).name()
    except:
        return hex_color

def get_dark_theme(accent_color="#1DB954"):
    accent_hover_color = lighten_color(accent_color, 0.1)

    return f"""
        #container {{
            background-color: #121212;
            border-radius: 15px; 
            border: 1px solid {accent_color};
        }}
        #titleBar {{
            background-color: #181818;
            border-top-left-radius: 14px; 
            border-top-right-radius: 14px;
            border-bottom: 1px solid #282828;
        }}
        #titleLabel {{ 
            color: #FFFFFF; 
            font-weight: bold; 
        }}
        #mainPanel {{
            background-color: rgba(24, 24, 24, 0.8); 
            border-radius: 10px;
            border: 1px solid #282828;
        }}
        #sectionLabel {{ 
            color: {accent_color}; 
            font-weight: bold; 
        }}
        QLabel, QRadioButton, QCheckBox {{ 
            color: #B3B3B3; 
        }}
        QComboBox, QLineEdit {{
            background-color: #282828; 
            border: 2px solid #333333;
            border-radius: 8px; 
            padding: 10px; 
            color: #FFFFFF;
        }}
        QComboBox:hover, QLineEdit:hover {{ 
            border: 2px solid #444444; 
        }}
        QLineEdit:focus {{ 
            border: 2px solid {accent_color}; 
        }}
        QPushButton {{
            background-color: {accent_color};
            color: #121212; 
            border: none; 
            border-radius: 8px; 
            padding: 12px; 
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {accent_hover_color};
        }}
        #colorPickerButton {{
             padding: 5px;
        }}
        #closeButton, #minimizeButton {{ 
            font-size: 12pt; 
            font-weight: bold; 
            border-radius: 15px; 
        }}
        #closeButton {{ 
            background-color: #E23D28; 
            color: white;
        }}
        #closeButton:hover {{ 
            background-color: #F84F39; 
        }}
        #minimizeButton {{ 
            background-color: #F8B339; 
            color: white;
        }}
        #minimizeButton:hover {{ 
            background-color: #FFC14E; 
        }}
        QProgressBar {{
            border: 2px solid #282828; 
            border-radius: 8px; 
            text-align: center;
            background-color: #181818; 
            color: white; 
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background-color: {accent_color};
            border-radius: 6px;
        }}
        #modList {{
            background-color: #1A1C20;
            border: 1px solid #282828;
            border-radius: 8px;
        }}
        QScrollBar:vertical {{
            border: none;
            background: #181818;
            width: 12px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #343840;
            min-height: 25px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {accent_color};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            border: none;
            background: none;
        }}
        #errorLabel {{ 
            color: #E23D28; 
            font-weight: bold; 
        }}
        QTabWidget::pane {{
            border: 1px solid #282828; 
            border-radius: 8px;
            background-color: #181818; 
            margin-top: -1px;
        }}
        QTabBar::tab {{
            background-color: #181818; 
            color: #B3B3B3; 
            padding: 10px 15px;
            margin-right: 2px; 
            border-top-left-radius: 5px; 
            border-top-right-radius: 5px;
            border: 1px solid #282828; 
            border-bottom: none;
        }}
        QTabBar::tab:selected {{ 
            background-color: #282828; 
            color: #FFFFFF; 
        }}
        QTabBar::tab:hover {{ 
            background-color: #222222; 
            color: #FFFFFF;
        }}
        QCheckBox, QRadioButton {{ 
            spacing: 8px; 
        }}
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 18px; 
            height: 18px; 
            border: 2px solid #333333;
            background-color: #121212;
        }}
        QCheckBox::indicator {{ 
            border-radius: 3px; 
        }}
        QRadioButton::indicator {{ 
            border-radius: 9px; 
        }}
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ 
            background-color: {accent_color}; 
            border: 2px solid {accent_color}; 
        }}
        QSlider::groove:horizontal {{
            border: 1px solid #282828; 
            height: 4px;
            background-color: #333333; 
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background-color: #FFFFFF; 
            border: 2px solid {accent_color}; 
            width: 18px;
            margin: -8px 0; 
            border-radius: 9px;
        }}
        QTextEdit {{
            background-color: #0A0A0A; 
            border: 1px solid #282828;
            border-radius: 8px; 
            color: #00FF41; 
            padding: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
        }}
        #advancedButton {{ 
            background-color: #333333; 
        }}
        #advancedButton:checked {{ 
            background-color: #444444; 
        }}
        #advancedFrame {{
            background-color: rgba(24, 24, 24, 0.5);
            border: 1px solid #282828;
            border-radius: 5px; 
            padding: 10px;
        }}
    """

def get_light_theme():
    return """
        #container {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #f0f5fa, stop:1 #dce6f0);
            border-radius: 15px; border: 1px solid rgba(100, 150, 200, 0.5);
        }
        #titleBar {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #e6f0fa, stop:1 #d2e1f0);
            border-top-left-radius: 15px; border-top-right-radius: 15px;
            border-bottom: 1px solid rgba(100, 150, 200, 0.5);
        }
        #titleLabel { color: #1a365d; font-weight: bold; }
        #mainPanel {
            background: rgba(250, 255, 255, 0.8); border-radius: 10px;
            border: 1px solid rgba(100, 150, 200, 0.3);
        }
        #sectionLabel { color: #2b6cb0; font-weight: bold; }
        QLabel, QRadioButton, QCheckBox { color: #2d3748; }
        QComboBox, QLineEdit {
            background: rgba(255, 255, 255, 0.9); border: 2px solid rgba(100, 150, 200, 0.4);
            border-radius: 8px; padding: 10px; color: #2d3748;
        }
        QComboBox:hover, QLineEdit:hover { border: 2px solid rgba(100, 150, 200, 0.7); }
        QLineEdit:focus { border: 2px solid #2b6cb0; }
        QPushButton {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #38b2ac, stop:1 #2b6cb0);
            color: white; border: none; border-radius: 8px; padding: 12px; font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                stop:0 #4fd1c5, stop:1 #3182ce);
        }
        #closeButton, #minimizeButton { font-size: 12pt; font-weight: bold; border-radius: 15px; color: white;}
        #closeButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #f56565, stop:1 #e53e3e); }
        #closeButton:hover { background: #e53e3e; }
        #minimizeButton { background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #f6ad55, stop:1 #ed8936); }
        #minimizeButton:hover { background: #ed8936; }
        QProgressBar {
            border: 2px solid rgba(100, 150, 200, 0.4); border-radius: 8px; text-align: center;
            background: rgba(255, 255, 255, 0.9); color: #2d3748; font-weight: bold;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                stop:0 #2b6cb0, stop:1 #38b2ac);
            border-radius: 6px;
        }
        #errorLabel { color: #e53e3e; font-weight: bold; }
        QTabWidget::pane {
            border: 1px solid rgba(100, 150, 200, 0.4); border-radius: 8px;
            background: rgba(250, 255, 255, 0.8); margin-top: -1px;
        }
        QTabBar::tab {
            background: rgba(255, 255, 255, 0.9); color: #2d3748; padding: 10px 15px;
            margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px;
            border: 1px solid rgba(100, 150, 200, 0.4); border-bottom: none;
        }
        QTabBar::tab:selected { background: #dce6f0; color: #1a365d; }
        QTabBar::tab:hover { background: #e2e8f0; }
        QTextEdit {
            background: #e2e8f0; border: 1px solid #cbd5e0;
            border-radius: 8px; color: #2d3748; padding: 10px;
        }
        #advancedButton { background: #a0aec0; }
        #advancedButton:checked { background: #718096; }
        #advancedFrame {
            background: rgba(230, 240, 250, 0.5);
            border: 1px solid rgba(100, 150, 200, 0.2);
            border-radius: 5px; padding: 10px;
        }
    """

def get_neon_theme():
    return """
        #container {
            background: #0d0d0d;
            border-radius: 15px; border: 2px solid #00ffff;
            box-shadow: 0 0 20px #00ffff;
        }
        #titleBar {
            background: #1a1a1a;
            border-top-left-radius: 13px; border-top-right-radius: 13px;
            border-bottom: 2px solid #00ffff;
        }
        #titleLabel { color: #ff00ff; text-shadow: 0 0 10px #ff00ff; }
        #mainPanel {
            background: rgba(26, 26, 26, 0.8); border-radius: 10px;
            border: 1px solid #ff00ff;
        }
        #sectionLabel { color: #00ffff; font-weight: bold; }
        QLabel, QRadioButton, QCheckBox { color: #e0e0e0; }
        QComboBox, QLineEdit {
            background: #1a1a1a; border: 2px solid #ff00ff;
            border-radius: 8px; padding: 10px; color: #e0e0e0;
        }
        QComboBox:hover, QLineEdit:hover { border: 2px solid #00ffff; }
        QPushButton {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:1 #00ffff);
            color: #0d0d0d; border: none;
            border-radius: 8px; padding: 12px; font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #00ffff, stop:1 #ff00ff);
        }
        #closeButton, #minimizeButton { font-size: 12pt; font-weight: bold; border-radius: 15px; color: black;}
        #closeButton { background: #ff00ff; }
        #closeButton:hover { background: #ff33ff; }
        #minimizeButton { background: #00ffff; }
        #minimizeButton:hover { background: #33ffff; }
        QProgressBar {
            border: 2px solid #ff00ff; border-radius: 8px; text-align: center;
            background: #1a1a1a; color: #e0e0e0; font-weight: bold;
        }
        QProgressBar::chunk {
            background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:1 #00ffff);
            border-radius: 6px;
        }
        #errorLabel { color: #ff00ff; font-weight: bold; }
        QTabWidget::pane {
            border: 1px solid #ff00ff; border-radius: 8px;
            background: rgba(26, 26, 26, 0.8); margin-top: -1px;
        }
        QTabBar::tab {
            background: #1a1a1a; color: #e0e0e0; padding: 10px 15px;
            margin-right: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px;
            border: 1px solid #ff00ff; border-bottom: none;
        }
        QTabBar::tab:selected { background: #ff00ff; color: #0d0d0d; }
        QTabBar::tab:hover { background: #3d003d; }
        QTextEdit {
            background: #0d0d0d; border: 1px solid #ff00ff; color: #00ff00;
            font-family: 'Consolas', 'Courier New', monospace;
        }
        #advancedButton { background: #4a004a; }
        #advancedButton:checked { background: #2a002a; }
        #advancedFrame {
            background: rgba(26, 0, 26, 0.5);
            border: 1px solid rgba(255, 0, 255, 0.2);
            border-radius: 5px; padding: 10px;
        }
    """