"""Create a minimal relocatable Tesseract bundle for the desktop app."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _runtime_files(source: Path) -> list[Path]:
    root_files = [source / "tesseract.exe", *source.glob("*.dll")]
    tessdata = source / "tessdata"
    data_files = [
        path
        for path in tessdata.rglob("*")
        if path.is_file() and path.suffix.lower() != ".jar"
    ]
    return sorted({path for path in [*root_files, *data_files] if path.is_file()})


def create_bundle(source: Path, output: Path) -> None:
    if not (source / "tesseract.exe").is_file():
        raise FileNotFoundError(source / "tesseract.exe")

    files = _runtime_files(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in files:
            bundle.write(path, path.relative_to(source).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    create_bundle(args.source.resolve(), args.output.resolve())
    print(f"Created Tesseract bundle: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
