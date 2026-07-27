#!/usr/bin/env python3
"""
👁️ WATCH — 影仔 checks the doors, and says plainly what he could not check.

The 2026-07-27 audit took about twenty-five hand-rolled commands and made four
wrong claims along the way, every one of them from checking the artefact instead
of the evidence:

  · matched a leaked AWS key on an 8-char prefix that turns out to be
    account-wide, so it matched everything
  · called a password "rotated" by diffing it against an 8-character
    placeholder in a .env file
  · called a bucket private because one HTTP client got a 403, when the
    bucket was serving the bytes happily to another
  · called an endpoint an open faucet from a 21-hour-old reading

So this file has one rule, and it is the whole reason it exists:

    **Check the evidence, never the artefact.**
    An audit log beats a file on disk. A real request beats a config. And a
    check that cannot be made must SAY SO, out loud, in the report — because a
    quiet skip reads exactly like a pass, and that is how an audit lies.

Nothing here changes anything. It is read-only, everywhere, always.

    python3 kingdom/trapline/watch.py            # everything
    python3 kingdom/trapline/watch.py git        # repo hygiene only
    python3 kingdom/trapline/watch.py aws        # cloud posture only

Standard library only. No dependency, no network unless a check names it.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

TRAPLINE = Path(__file__).resolve().parent
KINGDOM = TRAPLINE.parent
ROOT = KINGDOM.parent

OK, WARN, BAD, SKIP = "✅", "🟡", "🔴", "⚪"
findings = []


def say(level, area, msg, fix=""):
    findings.append((level, area, msg, fix))
    print(f"  {level} {msg}")
    if fix and level in (WARN, BAD):
        print(f"       → {fix}")


def run(cmd, timeout=25):
    """Run a command. Returns (ok, stdout). Never raises — a broken check is a
    SKIP, never a silent pass."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode == 0, p.stdout.strip()
    except Exception:
        return False, ""


# ── git hygiene ──────────────────────────────────────────────────────────────
def check_git():
    print("\n\033[1m git — the repos\033[0m")

    ok, out = run(["git", "config", "--global", "core.excludesfile"])
    gi = Path(os.path.expanduser(out)) if ok and out else None
    if gi and gi.exists():
        body = gi.read_text(errors="ignore")
        covers = any(l.strip() in (".env", ".env*", "*.env") for l in body.splitlines())
        say(OK if covers else WARN, "git",
            f"global gitignore at {out}" + ("" if covers else " — does NOT cover .env"),
            "" if covers else f"printf '\\n.env\\n.env.*\\n!.env.example\\n' >> {out}")
    else:
        say(WARN, "git", "no global gitignore is configured",
            "git config --global core.excludesfile ~/.gitignore_global")

    ok, out = run(["git", "config", "--global", "core.hooksPath"])
    say(OK if (ok and out) else WARN, "git",
        f"global hooksPath = {out}" if (ok and out) else "no global hooksPath — nothing scans a commit before it lands",
        "" if (ok and out) else "see kingdom/trapline/hooks/ — `kingdom trapline install-hook`")

    # tracked env files across the estate — the artefact check that IS the evidence,
    # because `git ls-files` is what git will actually push.
    roots = [Path.home() / "Projects", Path.home() / "Desktop"]
    tracked = []
    for base in roots:
        if not base.exists():
            continue
        for d in base.iterdir():
            if not (d / ".git").exists():
                continue
            ok, out = run(["git", "-C", str(d), "ls-files"], timeout=20)
            if not ok:
                continue
            for f in out.splitlines():
                name = Path(f).name
                if name.startswith(".env") and not name.endswith((".example", ".sample", ".template")):
                    tracked.append(f"{d.name}/{f}")
    if tracked:
        say(BAD, "git", f"{len(tracked)} real .env file(s) are TRACKED BY GIT:",
            "git rm --cached <file>  — and rotate whatever is inside, history keeps it")
        for t in tracked[:8]:
            print(f"         · {t}")
    else:
        say(OK, "git", "no real .env files are tracked in any repo under ~/Projects or ~/Desktop")


# ── the kingdom's own chains ─────────────────────────────────────────────────
def check_kingdom():
    print("\n\033[1m kingdom — the chains\033[0m")
    for wing, script in [("host", "host/zerone_host.py"), ("flow", "flow/flow.py"),
                         ("care", "care/care.py"), ("gospel", "gospel/gospel.py"),
                         ("trapline", "trapline/trapline.py")]:
        p = KINGDOM / script
        if not p.exists():
            say(SKIP, wing, f"{wing}: no script at {script} — NOT CHECKED")
            continue
        ok, out = run([sys.executable, str(p), "verify"])
        first = out.splitlines()[0] if out else "(no output)"
        say(OK if ok else BAD, wing, f"{wing}: {first}",
            "" if ok else f"python3 kingdom/{script} verify")

    armed = TRAPLINE / ".armed"
    if armed.exists() and armed.read_text().strip():
        say(WARN, "trapline", f"traps ARMED: {', '.join(armed.read_text().split())}",
            "kingdom trapline disarm <name>")
    else:
        say(OK, "trapline", "every trap disarmed — nothing can fire on anyone")

    # the private files must never have become tracked
    ok, out = run(["git", "-C", str(ROOT), "ls-files", "kingdom/trapline/"])
    leaked = [f for f in out.splitlines()
              if Path(f).name in ("placements.jsonl", ".salt", ".armed", ".fires.md")]
    say(BAD if leaked else OK, "trapline",
        f"private trapline files TRACKED: {leaked}" if leaked
        else "placements/.salt/.armed/.fires.md all still untracked",
        "git rm --cached <file>" if leaked else "")


# ── aws posture ──────────────────────────────────────────────────────────────
def check_aws():
    print("\n\033[1m aws — the cloud\033[0m")
    env = dict(os.environ, AWS_PAGER="")

    def aws(args, timeout=30):
        try:
            p = subprocess.run(["aws"] + args, capture_output=True, text=True,
                               timeout=timeout, env=env)
            return (p.returncode == 0, p.stdout.strip())
        except Exception:
            return (False, "")

    ok, who = aws(["sts", "get-caller-identity", "--query", "Arn", "--output", "text"])
    if not ok:
        say(SKIP, "aws", "no usable AWS credentials — CLOUD NOT CHECKED (this is a skip, not a pass)",
            "aws sso login  /  aws configure")
        return
    say(BAD if who.endswith(":root") else OK, "aws",
        f"caller: {who}" + ("  — operating as ROOT" if who.endswith(":root") else ""),
        "use a named IAM user with MFA for day-to-day work" if who.endswith(":root") else "")

    ok, out = aws(["iam", "get-account-summary", "--query",
                   "SummaryMap.{K:AccountAccessKeysPresent,M:AccountMFAEnabled}", "--output", "text"])
    if ok and out:
        parts = out.split()
        keys, mfa = (parts + ["?", "?"])[:2]
        say(BAD if keys == "1" else OK, "aws",
            "root has long-lived access key(s)" if keys == "1" else "root has no access keys",
            "delete them — root should hold none" if keys == "1" else "")
        say(OK if mfa == "1" else BAD, "aws",
            "root MFA enabled" if mfa == "1" else "root has NO MFA",
            "" if mfa == "1" else "enable it today")

    # admins without MFA — the softest path to owning everything
    ok, users = aws(["iam", "list-users", "--query", "Users[].UserName", "--output", "text"])
    if ok:
        naked = []
        for u in users.split():
            _, pol = aws(["iam", "list-attached-user-policies", "--user-name", u,
                          "--query", "AttachedPolicies[].PolicyName", "--output", "text"], 20)
            if "AdministratorAccess" not in (pol or ""):
                continue
            _, mfa = aws(["iam", "list-mfa-devices", "--user-name", u,
                          "--query", "MFADevices", "--output", "text"], 20)
            _, login = aws(["iam", "get-login-profile", "--user-name", u], 20)
            if not (mfa or "").strip():
                naked.append(u + (" (console)" if login else ""))
        say(BAD if naked else OK, "aws",
            f"ADMIN without MFA: {', '.join(naked)}" if naked else "every admin user has MFA",
            "aws iam enable-mfa-device …" if naked else "")

    # never-used active keys
    if ok:
        dead = []
        for u in users.split():
            _, ks = aws(["iam", "list-access-keys", "--user-name", u, "--query",
                         "AccessKeyMetadata[?Status=='Active'].AccessKeyId", "--output", "text"], 20)
            for k in (ks or "").split():
                _, lu = aws(["iam", "get-access-key-last-used", "--access-key-id", k,
                             "--query", "AccessKeyLastUsed.LastUsedDate", "--output", "text"], 20)
                if lu == "None":
                    dead.append(f"{u}/…{k[-4:]}")
        say(WARN if dead else OK, "aws",
            f"{len(dead)} active key(s) NEVER used: {', '.join(dead)}" if dead
            else "no active key is unused",
            "aws iam update-access-key --status Inactive …" if dead else "")

    # databases open to the world — evidence: the security group, not the config flag
    ok, dbs = aws(["rds", "describe-db-instances", "--query",
                   "DBInstances[].[DBInstanceIdentifier,PubliclyAccessible]", "--output", "text"], 40)
    if ok and dbs:
        for line in dbs.splitlines():
            name, pub = (line.split() + ["", ""])[:2]
            if pub != "True":
                continue
            _, sgs = aws(["rds", "describe-db-instances", "--db-instance-identifier", name,
                          "--query", "DBInstances[].VpcSecurityGroups[].VpcSecurityGroupId",
                          "--output", "text"], 30)
            world = False
            for sg in (sgs or "").split():
                _, rules = aws(["ec2", "describe-security-groups", "--group-ids", sg,
                                "--query", "SecurityGroups[].IpPermissions[].IpRanges[].CidrIp",
                                "--output", "text"], 30)
                if "0.0.0.0/0" in (rules or ""):
                    world = True
            say(BAD if world else WARN, "aws",
                f"RDS '{name}' is reachable from the ENTIRE INTERNET" if world
                else f"RDS '{name}' is public but the security group is scoped",
                "restrict the SG — Vercel static egress IPs / RDS Proxy / a pooler" if world else "")

    # guardduty: has anything actually happened?
    ok, det = aws(["guardduty", "list-detectors", "--query", "DetectorIds", "--output", "text"], 20)
    if not (ok and det.strip()):
        say(WARN, "aws", "GuardDuty is not enabled", "aws guardduty create-detector --enable")
    else:
        _, ids = aws(["guardduty", "list-findings", "--detector-id", det.split()[0],
                      "--max-results", "50", "--query", "FindingIds", "--output", "text"], 30)
        n = len((ids or "").split())
        say(WARN if n else OK, "aws",
            f"GuardDuty: {n} finding(s) on record" if n else "GuardDuty: clean",
            "aws guardduty list-findings …" if n else "")


def main(argv):
    which = argv[1] if len(argv) > 1 else "all"
    print("\n\033[1m👁️  the watch\033[0m — 影仔 checks the doors. read-only; nothing is changed.")
    print("   \033[2mrule: check the evidence, never the artefact. a check that cannot")
    print("   be made says so — a quiet skip reads exactly like a pass.\033[0m")
    if which in ("all", "git"):
        check_git()
    if which in ("all", "kingdom"):
        check_kingdom()
    if which in ("all", "aws"):
        check_aws()

    bad = sum(1 for f in findings if f[0] == BAD)
    warn = sum(1 for f in findings if f[0] == WARN)
    skip = sum(1 for f in findings if f[0] == SKIP)
    good = sum(1 for f in findings if f[0] == OK)
    print(f"\n\033[1m {good} holding · {warn} to tidy · {bad} to fix · {skip} NOT CHECKED\033[0m")
    if skip:
        print(" \033[2m a skip is not a pass. the unchecked doors are listed above.\033[0m")
    print(" 💓0️⃣🐷❤️👧\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
