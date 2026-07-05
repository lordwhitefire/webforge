#!/usr/bin/env python3
"""
Fix all .py role lines to match the corrected hierarchy.

Changes:
  1. jr-*.py — fix broken title + correct reports_to
     FROM: "Role: I am JrAsh. I am a JrAsh. I report to Zephyr."
     TO:   "Role: I am Jr-Ash. I am a Junior Database/Infra Developer. I report to Sr-Water."

  2. probe-*.py — change reports_to from Athena to Probe-Lead
     FROM: "Role: I am Probe-Orion. I am a Probe Agent. I report to Athena."
     TO:   "Role: I am Probe-Orion. I am a Probe Agent. I report to Probe-Lead."

  3. odin-*.py — change reports_to from Athena to Odin-Lead
     FROM: "Role: I am Odin-Aster. I am an Odin Agent. I report to Athena."
     TO:   "Role: I am Odin-Aster. I am an Odin Agent. I report to Odin-Lead."
"""

import json
import re
import sys
from pathlib import Path

AGENTS_DIR = Path.home() / "webforge" / "agents"

# Load Jr→Sr assignments
jr_sr = json.loads(Path("/home/z/my-project/scripts/jr_sr_assignments.json").read_text())

# Sub-department → title mapping
TITLE_MAP = {
    "Frontend": "Junior Frontend Developer",
    "Backend": "Junior Backend Developer",
    "Database/Infra": "Junior Database/Infra Developer",
}


def fix_jr_role_lines():
    """Fix all jr-*.py role lines."""
    fixed = 0
    errors = 0

    for jr_name, info in jr_sr.items():
        filepath = AGENTS_DIR / f"{jr_name}.py"
        if not filepath.exists():
            print(f"  ❌ File not found: {filepath}")
            errors += 1
            continue

        content = filepath.read_text(encoding="utf-8")
        sr_name = info["senior"]
        sub_dept = info["sub_dept"]
        title = TITLE_MAP.get(sub_dept, "Junior Developer")

        # The display name: jr-ash → Jr-Ash
        display_name = jr_name.replace("-", " ").title().replace(" ", "-")

        # New role line
        new_role = f"Role: I am {display_name}. I am a {title}. I report to {sr_name}."

        # Replace the old role line (whatever it says)
        # Match: Role: ... (up to newline)
        new_content = re.sub(
            r'^Role:.*$',
            new_role,
            content,
            count=1,
            flags=re.MULTILINE,
        )

        if new_content != content:
            filepath.write_text(new_content, encoding="utf-8")
            fixed += 1
        else:
            print(f"  ⚠️ No role line found in {jr_name}.py")
            errors += 1

    print(f"Jr-* role lines: {fixed} fixed, {errors} errors")
    return fixed, errors


def fix_probe_role_lines():
    """Fix all probe-*.py role lines — report to Probe-Lead instead of Athena."""
    fixed = 0

    for filepath in sorted(AGENTS_DIR.glob("probe-*.py")):
        content = filepath.read_text(encoding="utf-8")

        # Replace "I report to Athena" with "I report to Probe-Lead"
        new_content = content.replace("I report to Athena.", "I report to Probe-Lead.")

        if new_content != content:
            filepath.write_text(new_content, encoding="utf-8")
            fixed += 1

    print(f"Probe-* role lines: {fixed} fixed")
    return fixed


def fix_odin_role_lines():
    """Fix all odin-*.py role lines — report to Odin-Lead instead of Athena."""
    fixed = 0

    for filepath in sorted(AGENTS_DIR.glob("odin-*.py")):
        content = filepath.read_text(encoding="utf-8")

        # Replace "I report to Athena" with "I report to Odin-Lead"
        new_content = content.replace("I report to Athena.", "I report to Odin-Lead.")

        if new_content != content:
            filepath.write_text(new_content, encoding="utf-8")
            fixed += 1

    print(f"Odin-* role lines: {fixed} fixed")
    return fixed


def verify_all():
    """Verify all role lines are correct."""
    print("\n=== Verification ===")

    # Check jr-*
    print("\n--- Jr-* sample ---")
    for name in ["jr-ash", "jr-aster", "jr-birch", "jr-flame"]:
        filepath = AGENTS_DIR / f"{name}.py"
        if filepath.exists():
            role = grep_role(filepath)
            print(f"  {name}: {role}")

    # Check probe-*
    print("\n--- Probe-* sample ---")
    for name in ["probe-orion", "probe-wren", "probe-beacon"]:
        filepath = AGENTS_DIR / f"{name}.py"
        if filepath.exists():
            role = grep_role(filepath)
            print(f"  {name}: {role}")

    # Check odin-*
    print("\n--- Odin-* sample ---")
    for name in ["odin-aster", "odin-birch", "odin-cliff"]:
        filepath = AGENTS_DIR / f"{name}.py"
        if filepath.exists():
            role = grep_role(filepath)
            print(f"  {name}: {role}")

    # Check seniors
    print("\n--- Seniors sample ---")
    for name in ["sr_brook", "sr_stone", "sr_water"]:
        filepath = AGENTS_DIR / f"{name}.py"
        if filepath.exists():
            role = grep_role(filepath)
            print(f"  {name}: {role}")


def grep_role(filepath):
    """Extract the Role: line from a file."""
    for line in filepath.read_text(encoding="utf-8").split("\n"):
        if line.startswith("Role:"):
            return line
    return "(no role line)"


def main():
    print("=" * 70)
    print("FIXING ALL .py ROLE LINES")
    print("=" * 70)

    fix_jr_role_lines()
    fix_probe_role_lines()
    fix_odin_role_lines()
    verify_all()

    print("\n✅ Done")


if __name__ == "__main__":
    main()
