# Firewall 3 — Directory Exploration & Forensics Challenge
## ORGANIZERS ONLY — Flags & Solution Walkthrough

> Keep this file **off the participant network and out of the Go-Bag.**
> It is not copied into any Docker image.

---

## Challenge at a glance

| Field | Value |
|---|---|
| Firewall | 3 — Directory Exploration & Forensics |
| Category | Linux filesystem recon, forensics, privilege escalation |
| Company (cover) | Same fictional corporate server as Firewalls 1–2 |
| Vulnerable author (lore) | **Aya Nocari** (the intern) |
| Mapping | Information disclosure (hidden-in-plain-sight file), weak secret storage (password embedded in binary data), privilege escalation via leaked credential |
| Flags | **Three**, per team — see below |
| Flag format | `FLAG{...}` — lowercase leetspeak, underscores, no spaces |
| Isolation | One Docker container per team, own filesystem, own credentials |
| Est. solve time | 20–40 min per team with the NPC hint ladder available |

Unlike Firewalls 1 and 2, Firewall 3 issues **per-team unique flags** — every
team's `FLAG_A`, `FLAG_B`, and `FLAG_C` values are distinct, generated at
provisioning time and stored in `/opt/hackapi/state/fw3-flags/team<N>.env`.
This prevents one team from simply handing their flag string to another.

---

## Access handoff

Each team receives:

```
Team <N> — Firewall 3 Access
Host: <pi-ip>
Port: 220<N>
User: intern
Password: [issued upon completing Firewall 2]
```

The password is **not** pre-printed on the slip. It is handed out as part of
the Firewall 2 solve reward (see Firewall 2's own `ORGANIZER_FLAGS.md` for
the exact mechanism). This keeps the Firewall 2 → Firewall 3 gate real: a
team cannot reach Firewall 3 without actually solving Firewall 2.

---

## The vulnerability chain (3 stages)

```
  Stage 1                  Stage 2                    Stage 3 (optional)
  Directory Exploration →  Forensics → Root Escalation → Malware Cleanup   → 3 FLAGS
  find the hidden file     extract leaked root pw        read the beacon log
  among decoys              from the JPEG, su to root      as root
```

Each stage is gated by what the player can see, not by a hard technical
block — this is a beginner-friendly firewall, so nothing requires anything
beyond `find`, `ls`, `strings`, `base64`, `su`, and `cat`.

---

## Full proof-of-concept

Replace `TARGET` and `PORT` with the deployed host and the team's assigned
port.

```bash
TARGET=10.10.10.5
PORT=2207
```

### Stage 1 — Directory exploration

```bash
ssh -p $PORT intern@$TARGET
# password: issued via Firewall 2
```

The container's filesystem contains six decoy-filled directories
(`/var/backups`, `/srv/company/archive/2024`, `/srv/company/archive/2025`,
`/home/intern/.cache`, `/opt/legacy`, `/var/log/app`), each holding ~6
randomly-named junk files (`report_q3.bak`, `old_config_17.yml`, etc.).

```bash
find / -user aya 2>/dev/null
#   /srv/company/archive/2025/hr/.old/.timesheet_aya.jpg
```

```bash
cat /srv/company/archive/2025/hr/.old/README_FOLDER.txt
#   Archived HR assets — do not delete.
#   FLAG{dir_7_a91f3c}
```

**Flag A** captured.

### Stage 2 — Forensics → root escalation

```bash
cd /srv/company/archive/2025/hr/.old/
file .timesheet_aya.jpg
#   JPEG image data, ...
strings .timesheet_aya.jpg | tail
#   ... # admin recovery (temp) pw: NGE3YzkxZGI=
```

```bash
echo 'NGE3YzkxZGI=' | base64 -d
#   4a7c91db
```

```bash
su -
Password: 4a7c91db
```

Prompt flips to `root@...:~#`.

```bash
cat /root/flag.txt
#   FLAG{root_7_c4e812}
```

**Flag B** captured.

### Stage 3 — Malware cleanup (optional)

```bash
cat /root/.cleanup/malware_dropper.sh
cat /root/.cleanup/c2_beacon.log
#   [2026-10-14 03:14:02] beacon sent
#   [2026-10-14 03:14:02] exfil target confirmed
#   # cleanup-token: FLAG{cleanup_7_9f0a21}
```

**Flag C** captured.

---

## Flag verification (no CTFd)

Players report flag strings in person to an organizer or NPC. Check each
against the team's row in `ORGANIZER_FW3_FLAGS.csv`
(`/opt/hackapi/organizer-only/ORGANIZER_FW3_FLAGS.csv`), generated
automatically by `spawn-fw3.sh`:

```
N,NAME,FLAG_A,FLAG_B,FLAG_C,ROOTPW
7,TeamName,FLAG{dir_7_a91f3c},FLAG{root_7_c4e812},FLAG{cleanup_7_9f0a21},4a7c91db
```

---

## Teaching points (for the debrief / scoreboard writeups)

1. **Obscurity is not protection.** Hiding a file with a dot-prefix or
   burying it among decoys slows discovery; it doesn't prevent it. Anyone
   who thinks to run `find` with the right filter gets there regardless.
2. **Never store secrets in binary data a user can read.** Appending a
   password to a JPEG is functionally identical to leaving it in a plaintext
   file — `strings` doesn't care what container format wraps the data.
3. **A leaked credential is a leaked credential, Base64 or not.** Encoding
   is not encryption. If it can be decoded with a single command, it offers
   no real protection — it's a courtesy formatting step, not a security
   control.

## Rotating for the real event

- **Flags and passwords regenerate automatically** per team on first run of
  `spawn-fw3.sh`, then persist across reboots via
  `/opt/hackapi/state/fw3-flags/team<N>.env`. To force fresh values for a
  re-run of the event, delete that directory's contents before
  re-provisioning:
  ```bash
  rm -rf /opt/hackapi/state/fw3-flags/*
  docker rm -f $(docker ps -aq --filter name=fw3-team)
  ./spawn-fw3.sh
  ```
- **Do not hand-edit** `team<N>.env` files directly unless you also restart
  that specific container (`docker restart fw3-team<N>`) — the values are
  only read at container start, via `entrypoint.sh`.
