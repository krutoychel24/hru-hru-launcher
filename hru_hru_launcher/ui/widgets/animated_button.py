from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QPushButton

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.OutBounce)
        self.animation.setDuration(200)

    def mousePressEvent(self, event):
        self.start_pos = self.pos()
        self.animation.setStartValue(self.start_pos)
        self.animation.setEndValue(self.start_pos + QPoint(0, 3))
        self.animation.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(self.start_pos)
        self.animation.start()
        super().mouseReleaseEvent(event)