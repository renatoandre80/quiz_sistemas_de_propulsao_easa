"""
Entry point for the EASA PDF ingestion pipeline.

Usage:
    python scripts/ingest.py
    python scripts/ingest.py --pdf path/to/custom.pdf

This script must be run once (or re-run after PDF updates) before starting
the Streamlit application.
"""
import argparse
import sys
from pathlib import Path

# Allow running from the project root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion.pdf_processor import run_ingestion_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest EASA PDF into ChromaDB")
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Path to the EASA PDF (defaults to data_source/easa_propulsao.pdf)",
    )
    args = parser.parse_args()

    try:
        run_ingestion_pipeline(pdf_path=args.pdf)
    except FileNotFoundError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        print("Place the PDF in data_source/easa_propulsao.pdf or use --pdf.", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nUnexpected error during ingestion: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
