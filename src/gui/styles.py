"""Qt stylesheet for modern dark-accent theme."""

STYLE = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}
QLabel#Title {
    color: #f5e0dc;
    font-size: 22pt;
    font-weight: 600;
    padding: 4px;
}
QLabel#Subtitle {
    color: #a6adc8;
    font-size: 10pt;
    padding-bottom: 12px;
}
QLabel#SectionHeader {
    color: #cba6f7;
    font-size: 11pt;
    font-weight: 600;
    padding-top: 8px;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 500;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #cba6f7;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton:disabled {
    background-color: #2a2a3a;
    color: #6c7086;
    border-color: #313244;
}
QPushButton#PrimaryButton {
    background-color: #cba6f7;
    color: #1e1e2e;
    border: none;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background-color: #b4befe;
}
QPushButton#PrimaryButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}
QPushButton#DangerButton {
    background-color: #313244;
    color: #f38ba8;
    border: 1px solid #f38ba8;
}
QPushButton#DangerButton:hover {
    background-color: #f38ba8;
    color: #1e1e2e;
}

QListWidget, QTableWidget {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #45475a;
    selection-color: #f5e0dc;
    alternate-background-color: #1e1e2e;
}
QListWidget::item, QTableWidget::item {
    padding: 6px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #313244;
}
QHeaderView::section {
    background-color: #313244;
    color: #cba6f7;
    padding: 8px;
    border: none;
    border-right: 1px solid #1e1e2e;
    font-weight: 600;
}

QProgressBar {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    text-align: center;
    color: #cdd6f4;
    min-height: 22px;
}
QProgressBar::chunk {
    background-color: #cba6f7;
    border-radius: 5px;
}

QStatusBar {
    background-color: #181825;
    color: #a6adc8;
    border-top: 1px solid #313244;
}

QCheckBox {
    color: #cdd6f4;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #45475a;
    border-radius: 4px;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #cba6f7;
    border-color: #cba6f7;
}

QFrame#DropZone {
    background-color: #181825;
    border: 2px dashed #45475a;
    border-radius: 12px;
    min-height: 100px;
}
QFrame#DropZone[active="true"] {
    border-color: #cba6f7;
    background-color: #1e1e2e;
}

QScrollBar:vertical {
    background: #181825;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #181825;
    height: 10px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #45475a;
    border-radius: 5px;
    min-width: 30px;
}
"""
