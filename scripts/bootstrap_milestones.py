"""Create any missing monthly milestones. Idempotent. A due time of 18:29:59Z is 23:59 IST."""
import json
import subprocess

from common import MILESTONES


def gh_api(*args: str) -> str:
    return subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True).stdout


existing = {m["title"] for m in json.loads(gh_api("repos/{owner}/{repo}/milestones?state=all&per_page=100"))}
for title, due in MILESTONES.items():
    if title in existing:
        print("exists", title)
        continue
    gh_api("repos/{owner}/{repo}/milestones", "-f", f"title={title}", "-f", f"due_on={due:%Y-%m-%d}T18:29:59Z")
    print("created", title)
