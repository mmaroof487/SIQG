#!/usr/bin/env python3
"""
Argus Pre-Deploy Static Checks (#13 + #16)
==========================================
Run from project root:
    python scripts/pre_deploy_checks.py

Exits 1 if any check fails. All checks must pass before deployment.
"""
import subprocess
import sys
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
GATEWAY = ROOT / "gateway"
FRONTEND = ROOT / "frontend-ts" / "src"
LOG_PATHS = list(ROOT.glob("*.log")) + list(GATEWAY.glob("*.log")) + list(Path(".").glob("gateway.log"))

PASS = []
FAIL = []


def check(label: str, passed: bool, detail: str = ""):
    if passed:
        PASS.append(label)
        print(f"  ✅  {label}")
    else:
        FAIL.append(label)
        print(f"  ❌  {label}", end="")
        if detail:
            print(f"\n       {detail}", end="")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# #13  Log secret scan
# ─────────────────────────────────────────────────────────────────────────────

SECRET_PATTERNS = [
    # Credentials in log lines
    (r"password\s*[:=]\s*\S+",                       "password value in logs"),
    (r"Authorization:\s*Bearer\s+[A-Za-z0-9\-_\.]+", "Authorization: Bearer header"),
    (r"Bearer\s+[A-Za-z0-9\-_\.]+\.[A-Za-z0-9\-_\.]+", "Bearer JWT token"),
    (r"Cookie:\s*\S+",                                "Cookie header (may contain session)"),
    (r"Set-Cookie:\s*\S+",                            "Set-Cookie header in logs"),
    # API keys
    (r"gsk_[A-Za-z0-9]+",                            "Groq API key (gsk_)"),
    (r"sk-[A-Za-z0-9]{20,}",                         "OpenAI API key (sk-)"),
    # Connection strings (any scheme with embedded credentials)
    (r"postgres(?:ql)?://[^:]+:[^@]+@",              "PostgreSQL connection string"),
    (r"redis://[^:]+:[^@]+@",                        "Redis connection string with password"),
    (r"mysql(?:2)?://[^:]+:[^@]+@",                  "MySQL connection string"),
    (r"mongodb(?:\+srv)?://[^:]+:[^@]+@",            "MongoDB connection string"),
    # Secret material
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY", "PEM private key block"),
    (r"SECRET_KEY\s*[:=]\s*\S+",                     "SECRET_KEY value"),
    (r"JWT_SECRET\s*[:=]\s*\S+",                     "JWT_SECRET value"),
    (r"ENCRYPTION_KEY\s*[:=]\s*\S+",                 "ENCRYPTION_KEY value"),
    # Cookie flags — look for session cookies logged without HttpOnly
    (r"Set-Cookie.*argus_token=[^;]+(?!.*HttpOnly)", "Session cookie without HttpOnly"),
]

print("\n── #13 Log Secret Scan ──────────────────────────────────────────")
if not LOG_PATHS:
    check("Log files present for scanning", False, "No *.log files found — run the gateway and re-run this script")
else:
    for log_path in LOG_PATHS:
        try:
            content = log_path.read_text(errors="replace")
        except Exception as e:
            check(f"Read {log_path.name}", False, str(e))
            continue

        found_secrets = []
        for pattern, label in SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_secrets.append(f"{label}: {matches[0][:60]}…")

        check(
            f"{log_path.name} — no secrets leaked",
            not found_secrets,
            "\n       ".join(found_secrets) if found_secrets else "",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Source-code secret scan (belt-and-suspenders)
# ─────────────────────────────────────────────────────────────────────────────

print("\n── Source Code Secret Scan ──────────────────────────────────────")
SOURCE_PATTERNS = [
    ("dummy_development_master_key", "gateway/**/*.py"),
    ("12345678901234567890123456789012", "gateway/**/*.py"),
    (r"gsk_[A-Za-z0-9]{20,}", "gateway/**/*.py"),
    ("localStorage.setItem.*token", "frontend-ts/src/**/*.ts"),
    ("localStorage.setItem.*token", "frontend-ts/src/**/*.tsx"),
    (r'allow_origins=\["\*"\]', "gateway/**/*.py"),
]

for pattern, glob in SOURCE_PATTERNS:
    hits = []
    for f in ROOT.glob(glob):
        try:
            content = f.read_text(errors="replace")
            for lineno, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line, re.IGNORECASE):
                    hits.append(f"{f.relative_to(ROOT)}:{lineno}")
        except Exception:
            pass
    check(
        f'No "{pattern[:40]}" in {glob}',
        not hits,
        ", ".join(hits[:5]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# #16  Dependency scan
# ─────────────────────────────────────────────────────────────────────────────

print("\n── #16 Dependency Scan ──────────────────────────────────────────")


def _run(cmd: list[str], cwd=None) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or ROOT)
    return result.returncode, result.stdout + result.stderr


# pip check — incompatible packages
code, out = _run([sys.executable, "-m", "pip", "check"])
check("pip check — no incompatible packages", code == 0, out.strip()[:200] if code != 0 else "")

# pip-audit — known CVEs
code, out = _run([sys.executable, "-m", "pip_audit", "--format", "columns", "-r", str(GATEWAY / "requirements.txt")])
if "No known vulnerabilities" in out or code == 0:
    check("pip-audit — no CVEs in requirements.txt", True)
else:
    # pip_audit might not be installed
    if "No module named pip_audit" in out or "not found" in out.lower():
        check("pip-audit installed", False, "Run: pip install pip-audit")
    else:
        check("pip-audit — no CVEs", False, out.strip()[:300])

# npm audit — frontend
pkg_json = ROOT / "frontend-ts" / "package.json"
if pkg_json.exists():
    code, out = _run(["npm", "audit", "--audit-level=high"], cwd=ROOT / "frontend-ts")
    check("npm audit — no high/critical CVEs", code == 0, out.strip()[-300:] if code != 0 else "")
else:
    check("frontend-ts/package.json exists", False, "Cannot run npm audit")


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

print(f"\n{'='*55}")
print(f"  PASSED: {len(PASS)}   FAILED: {len(FAIL)}")
print(f"{'='*55}")

if FAIL:
    print("\nFailing checks:")
    for f in FAIL:
        print(f"  ❌  {f}")
    sys.exit(1)
else:
    print("\n✅ All pre-deploy static checks passed.")
    sys.exit(0)
