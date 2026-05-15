import csv
import json
import os
from pathlib import Path
from typing import List

from models import Lead


def ensure_dir(directory: str) -> Path:
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_csv(leads: List[Lead], filepath: str) -> None:
    if not leads:
        return
    path = Path(filepath)
    write_header = not path.exists()
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(leads[0].to_dict().keys()))
        if write_header:
            writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_dict())


def export_json(leads: List[Lead], filepath: str) -> None:
    existing = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.extend([lead.to_dict() for lead in leads])
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def export_leads(leads: List[Lead], directory: str, filename: str, fmt: str) -> str:
    out_dir = ensure_dir(directory)
    ext = "csv" if fmt == "csv" else "json"
    filepath = str(out_dir / f"{filename}.{ext}")
    if fmt == "csv":
        export_csv(leads, filepath)
    else:
        export_json(leads, filepath)
    return filepath
