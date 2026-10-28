import argparse

from src.download import download
from src.pipeline import build


def main():
    parser = argparse.ArgumentParser(description="Build Olist delivery analytics from the original source.")
    parser.add_argument("--skip-download", action="store_true", help="Use eight existing CSVs in data/raw/.")
    parser.add_argument("--force-download", action="store_true", help="Replace local source CSVs with a fresh archive.")
    args = parser.parse_args()
    if args.skip_download and args.force_download:
        parser.error("Choose --skip-download or --force-download, not both.")
    if not args.skip_download:
        download(force=args.force_download)
    build()
    from src.reporting import create_reports
    create_reports()
    print("Ready. Open reports/dashboard.html or run: python -m streamlit run app.py")


if __name__ == "__main__":
    main()
