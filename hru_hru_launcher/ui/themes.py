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