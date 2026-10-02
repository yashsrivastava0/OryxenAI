"""Fetch only the local PDF models used by the Discovery intake pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from docling.utils.model_downloader import download_models


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    download_models(
        output_dir=args.output_dir,
        with_layout=True,
        with_tableformer=True,
        with_code_formula=False,
        with_picture_classifier=False,
        with_rapidocr=True,
    )


if __name__ == "__main__":
    main()
