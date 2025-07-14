# hru_hru_launcher/ui/widgets.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(150)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.original_geometry = None

    def enterEvent(self, event):
        if not self.original_geometry:
            self.original_geometry = self.geometry()
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(self.original_geometry.adjusted(-2, -2, 4, 4))
        self.animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.original_geometry:
            self.animation.stop()
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(self.original_geometry)
            self.animation.start()
        super().leaveEvent(event)