"""Create/update every label in syllabus/labels.yaml. Idempotent."""
import subprocess

import yaml

from common import ROOT

for label in yaml.safe_load((ROOT / "syllabus/labels.yaml").read_text()):
    cmd = ["gh", "label", "create", label["name"], "--color", label["color"], "--force"]
    if label.get("description"):
        cmd += ["--description", label["description"]]
    subprocess.run(cmd, check=True)
    print("ok", label["name"])
