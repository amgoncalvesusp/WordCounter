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


def main(argv=None):
    args = list(sys.argv if argv is None else argv)
    app = QApplication(args)
    app.setApplicationName("Contador de Palavras")
    app.setOrganizationName("Pesquisa Acadêmica")

    if "--smoke-test" in args:
        if getattr(sys, "frozen", False):
            from src.core.ocr_engine import validate_bundled_tesseract

            if not validate_bundled_tesseract():
                return 2
        return 0

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
