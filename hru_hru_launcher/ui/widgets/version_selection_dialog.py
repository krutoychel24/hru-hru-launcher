# hru_hru_launcher/ui/widgets/version_selection_dialog.py

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QListWidget, QListWidgetItem, QDialogButtonBox)

class VersionSelectionDialog(QDialog):
    def __init__(self, title, prompt, versions, action_text, lang_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.selected_version = None

        layout = QVBoxLayout(self)
        
        prompt_label = QLabel(prompt)
        prompt_label.setWordWrap(True)
        layout.addWidget(prompt_label)

        self.list_widget = QListWidget()
        for version in versions:
            self.list_widget.addItem(QListWidgetItem(version))
        self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)

        button_box = QDialogButtonBox()
        self.action_button = button_box.addButton(action_text, QDialogButtonBox.AcceptRole)
        self.cancel_button = button_box.addButton(lang_dict.get("cancel_button", "Cancel"), QDialogButtonBox.RejectRole)
        
        self.action_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setStyleSheet("""
            QDialog { background-color: #282a36; color: #f8f8f2; }
            QListWidget { border: 1px solid #44475a; padding: 5px; border-radius: 5px; }
            QPushButton { padding: 8px 15px; border-radius: 5px; background-color: #6272a4; }
        """)

    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_version = current_item.text()
        super().accept()

    def get_selected_version(self):
        return self.selected_version