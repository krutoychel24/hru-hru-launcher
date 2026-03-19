# hru_hru_launcher/ui/widgets/animated_button.py

from PySide6.QtCore import (QPropertyAnimation, QEasingCurve, QPoint,
                             QSequentialAnimationGroup, Property, QObject)
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtCore import Qt, QRect, QRectF


class AnimatedButton(QPushButton):
    """
    Premium button with smooth press-down animation.
    Keeps QPushButton's full styling via QSS.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._press_anim = QPropertyAnimation(self, b"pos")
        self._press_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._press_anim.setDuration(80)

        self._release_anim = QPropertyAnimation(self, b"pos")
        self._release_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._release_anim.setDuration(120)

        self._start_pos = QPoint()

    def mousePressEvent(self, event):
        self._start_pos = self.pos()
        self._release_anim.stop()
        self._press_anim.stop()
        self._press_anim.setStartValue(self._start_pos)
        self._press_anim.setEndValue(self._start_pos + QPoint(0, 2))
        self._press_anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_anim.stop()
        self._release_anim.setStartValue(self.pos())
        self._release_anim.setEndValue(self._start_pos)
        self._release_anim.start()
        super().mouseReleaseEvent(event)