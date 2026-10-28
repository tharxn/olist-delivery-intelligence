"""Download the original dataset; never substitute generated observations."""
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from .config import DOWNLOAD, FILES, METADATA, RAW, REPORTS, SOURCE, make_directories


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_local_sources():
    """Keep a downloaded manifest from silently describing changed source CSVs."""
    manifest_path = REPORTS / "source_metadata.json"
    actual = {name: sha256(RAW / name) for name in FILES.values()}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mismatches = [name for name, digest in actual.items() if manifest.get("files", {}).get(name) != digest]
        if mismatches:
            raise ValueError(
                "Source files differ from the provenance manifest: " + ", ".join(mismatches)
                + ". Use --force-download to restore the original archive, or explicitly "
                  "update provenance when intentionally using a different dataset version."
            )
    else:
        manifest_path.write_text(json.dumps({
            "source": SOURCE,
            "provenance": "Locally supplied CSVs; not downloaded or authenticated by this run.",
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "license": "Consult the original publisher's terms",
            "files": actual,
        }, indent=2), encoding="utf-8")


def download(force=False):
    make_directories()
    if not force and all((RAW / filename).exists() for filename in FILES.values()):
        print("Using existing Olist CSV files.")
        return
    with tempfile.TemporaryDirectory(prefix="olist-", dir=RAW.parent) as folder:
        archive = Path(folder) / "olist.zip"
        print("Downloading the original Olist archive (about 45 MB)...", flush=True)
        with requests.get(DOWNLOAD, stream=True, timeout=(30, 180)) as response:
            response.raise_for_status()
            with archive.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    handle.write(chunk)
        if not zipfile.is_zipfile(archive):
            raise RuntimeError(
                "Kaggle did not return a ZIP. Download the original dataset manually "
                f"from {SOURCE} and put the eight CSVs in data/raw/."
            )
        # Copy only explicitly expected members. Do not extract arbitrary ZIP paths.
        with zipfile.ZipFile(archive) as zipped:
            for filename in FILES.values():
                if filename not in zipped.namelist():
                    raise RuntimeError(f"Missing expected source file: {filename}")
                with zipped.open(filename) as source, (RAW / filename).open("wb") as target:
                    shutil.copyfileobj(source, target)
        license_name = "See original dataset terms"
        try:
            response = requests.get(METADATA, timeout=30)
            response.raise_for_status()
            license_name = response.json().get("licenseName", license_name)
        except (requests.RequestException, ValueError):
            pass
        manifest = {
            "source": SOURCE,
            "download_url": DOWNLOAD,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "archive_sha256": sha256(archive),
            "license": license_name,
            "files": {name: sha256(RAW / name) for name in FILES.values()},
            "omitted": "Geolocation CSV: not needed for state-level analysis.",
        }
        (REPORTS / "source_metadata.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Source CSV files and provenance manifest saved.", flush=True)
