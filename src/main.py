"""Application entry point."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    project_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Contador de Palavras")
    app.setOrganizationName("Pesquisa Acadêmica")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
