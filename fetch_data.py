"""
fetch_data.py
Downloads the public UCI SECOM dataset into data/raw/ and checks its shape.
Raw data is NOT committed to git (see .gitignore); run this once after cloning.

    python fetch_data.py

Source: UCI Machine Learning Repository, "SECOM" (dataset 179).
    https://archive.ics.uci.edu/dataset/179/secom
Files used: secom.data (sensor values), secom_labels.data (pass/fail + timestamp),
secom.names (the dataset's own description).
"""
import hashlib
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/179/secom.zip"
RAW = Path(__file__).parent / "data" / "raw"
WANTED = ["secom.data", "secom_labels.data", "secom.names"]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    if all((RAW / n).exists() for n in WANTED):
        print("Raw files already present in", RAW)
    else:
        print("Downloading", URL)
        req = urllib.request.Request(URL, headers={"User-Agent": "secom-spc-loader (study project)"})
        blob = urllib.request.urlopen(req, timeout=120).read()
        print(f"Zip size: {len(blob):,} bytes")
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = z.namelist()
            for n in WANTED:
                if n not in names:
                    sys.exit(f"Expected file {n} not in the zip. Zip holds: {names}")
                # write only the three known names, never a path taken from the zip
                (RAW / n).write_bytes(z.read(n))

    for n in WANTED:
        p = RAW / n
        digest = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        print(f"{n:20s} {p.stat().st_size:>10,} bytes  sha256 {digest}")

    # shape check: the dataset page says 1,567 rows x 590 features
    rows = (RAW / "secom.data").read_text().strip().splitlines()
    labels = (RAW / "secom_labels.data").read_text().strip().splitlines()
    print(f"secom.data rows: {len(rows)}, values in first row: {len(rows[0].split())}")
    print(f"secom_labels.data rows: {len(labels)}")
    if len(rows) != 1567 or len(rows[0].split()) != 590 or len(labels) != 1567:
        sys.exit("Shape is not 1567 x 590 with 1567 labels. Stopping.")
    print("Shape matches the UCI description.")


if __name__ == "__main__":
    main()
