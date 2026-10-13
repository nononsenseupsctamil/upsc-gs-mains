"""Fill in text for `text-pending` PYQs from a CSV you typed/pasted from the official paper. Reformats only.

    python scripts/import_pyqs.py papers/2023-gs1.csv [--confidence single-source]

CSV columns: id,text   (id like GS1-CUL-07-M2023-Q01). Never fetches or generates text.
Only entries that are currently text-pending are filled; existing text is never overwritten.
"""
import argparse
import csv
import sys

import yaml

from common import PAPERS, ROOT


class Dumper(yaml.SafeDumper):
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--confidence", default="single-source", choices=["official", "cross-checked", "single-source"])
    args = ap.parse_args()
    rows = {r["id"].strip(): " ".join(r["text"].split()) for r in csv.DictReader(open(args.csv, newline=""))}
    filled = set()
    for p in PAPERS:
        path = ROOT / f"data/pyqs/{p}.yaml"
        raw = path.read_text()
        header = "".join(l for l in raw.splitlines(True) if l.startswith("#"))
        entries = yaml.safe_load(raw) or []
        changed = False
        for e in entries:
            if e["id"] in rows and e.get("confidence") == "text-pending":
                e["text"], e["confidence"], e["verified"] = rows[e["id"]], args.confidence, False
                filled.add(e["id"])
                changed = True
        if changed:
            path.write_text(header + yaml.dump(entries, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=120))
    unknown = sorted(set(rows) - filled)
    print(f"filled {len(filled)}")
    if unknown:
        print("not filled (unknown id or text already present):\n  " + "\n  ".join(unknown))
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
