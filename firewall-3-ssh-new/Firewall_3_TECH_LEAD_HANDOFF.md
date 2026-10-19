# Firewall 3 — Technical Lead Handoff: Build, Ship & Host
### Directory Exploration & Forensics Challenge · Hack-A-PI

**Lane boundary (unchanged):** organizers ship the *challenge software*; the
**technical lead** owns the Pi / laptop / router. Red on *code* → back to us.
Red on *hardware / network / persistence* → your lane.

**Scoring:** CTFd is **not used**. Players report flag strings **in person** to
an organizer/NPC, who checks them against `ORGANIZER_FW3_FLAGS.csv`.

**What this is:** one Docker image (`hackapi/firewall-3-ssh:1.0`) started as
**N separate containers**, one per team, each with its own `sshd` on host port
`2201`–`2200+N`. No shared filesystem, no shared Linux account between teams.

---

## 0. The two-machine rule (read first)

Everything is split across two computers. **Every step below is tagged.**

| Tag | Machine | CPU arch | Internet? | Does |
|---|---|---|---|---|
| 🖥️ **[AMD64 · EXTERNAL PC]** | Your Linux build PC | `x86_64` / amd64 | **Yes** | Build, cross-compile, `docker save`, anything needing downloads |
| 🥧 **[ARM64 · PI]** | Raspberry Pi `hackapi` | `aarch64` / arm64 | **No (air-gapped)** | `docker load`, run containers, network, ufw, reboot tests |

**Golden rules**

1. **Never build on the Pi.** `docker build` needs the internet (Debian base image
   + `apt-get`). The Pi is offline at the event, so it only ever *loads a finished
   tarball* and *runs* it.
2. The image **must be arm64.** The build PC is amd64, so it is **cross-built with
   `docker buildx` + QEMU** (Section A). An amd64 image will not run on the Pi.
3. The Pi receives **one tarball + three small files**. It does not need the
   source tree, `Dockerfile`, or `build/` directory.

```
 🖥️ AMD64 external PC (internet)                    🥧 ARM64 Pi (offline)
 ┌──────────────────────────────────┐   USB / scp   ┌──────────────────────────────┐
 │ generate_fs.py → embed_jpeg.py   │               │ docker load -i firewall-3... │
 │ docker buildx build --platform   │  ───────────▶ │ ./spawn-fw3.sh  (N teams)    │
 │   linux/arm64 --load             │  .tar + 3     │ ufw-docker allow  (per team) │
 │ docker save → firewall-3-ssh.tar │  small files  │ players ssh -p 220N intern@  │
 └──────────────────────────────────┘               └──────────────────────────────┘
```

---

## A. 🖥️ [AMD64 · EXTERNAL PC] Build & export  — internet required

> Do all of Section A **before** the event, with internet. Nothing here runs on
> the Pi.

### A1. Prerequisites
- [ ] Docker Engine + **buildx** plugin: `docker --version && docker buildx version`
- [ ] Python 3 (for the two filesystem generators): `python3 --version`
- [ ] You have the full `firewall-3-ssh/` folder, including `assets/real.jpg`
      (the clean base JPEG for the forensics challenge).

### A2. Enable ARM64 emulation (one-time per build PC)
The amd64 PC needs QEMU/binfmt handlers to execute arm64 binaries during the build
(`apt-get` inside the Dockerfile runs as arm64 code).

```bash
docker run --privileged --rm tonistiivi/binfmt --install arm64
# Verify: must print "aarch64"
docker run --rm --platform linux/arm64 debian:12-slim uname -m
```

- [ ] `uname -m` printed **`aarch64`**.

> Alternative (no extra image pull): `sudo apt install qemu-user-static binfmt-support`.

### A3. Create a buildx builder (one-time)
```bash
docker buildx create --name hackapi-builder --driver docker-container --use
docker buildx inspect --bootstrap          # should list linux/arm64 among platforms
```
- [ ] `linux/arm64` appears in the **Platforms** line.

### A4. Generate the challenge filesystem (**run from the `firewall-3-ssh/` root**)
Both scripts use relative paths (`build/output`, `assets/real.jpg`), so run them
from the `firewall-3-ssh/` folder, **in this order**:

```bash
cd firewall-3-ssh
rm -rf build/output                         # start clean (decoy names are random each run)
python3 build/generate_fs.py                # decoy tree + README_FOLDER.txt (Flag A placeholder)
python3 build/embed_jpeg.py                 # builds .timesheet_dani.jpg with the root-pw placeholder
```

Sanity checks (placeholders must still be present — they are replaced **per team at
container start** by `entrypoint.sh`, never at build time):
```bash
grep -c FLAG_A_PLACEHOLDER build/output/srv/company/archive/2025/hr/.old/README_FOLDER.txt   # → 1
grep -a -c __ROOTPW_B64__  build/output/srv/company/archive/2025/hr/.old/.timesheet_dani.jpg # → 1
ls -a build/output/srv/company/archive/2025/hr/.old/    # shows .timesheet_dani.jpg + README_FOLDER.txt
```
- [ ] Both placeholders found; target file is named **`.timesheet_dani.jpg`**
      (the Dockerfile `chown`s exactly this path to the `dani` user).

### A5. Cross-build the arm64 image with buildx
```bash
docker buildx build \
  --platform linux/arm64 \
  -t hackapi/firewall-3-ssh:1.0 \
  --load .
```
- `--platform linux/arm64` → target is the **Pi**, not this PC.
- `--load` → imports the finished image into the local Docker so you can inspect
  and `docker save` it. (`--load` works with a single platform, which is all we need.)

Verify the architecture — **this is the check that prevents a dead Pi on event day:**
```bash
docker image inspect hackapi/firewall-3-ssh:1.0 --format '{{.Architecture}}/{{.Os}}'
# MUST print: arm64/linux
```
- [ ] Prints `arm64/linux` (if it prints `amd64/linux`, the `--platform` flag was
      dropped — rebuild).

### A6. (Optional) Smoke-test under QEMU on the build PC
Proves the image boots and the entrypoint injection works before you ship it.
Slow (emulated) but catches Dockerfile/entrypoint mistakes early.
```bash
docker run -d --name fw3-smoke --platform linux/arm64 -p 2299:22 \
  -e TEAM=99 -e INTERN_PW=hackapi2026 -e ROOTPW=deadbeef \
  -e FLAG_A='FLAG{dir_99_aaaaaa}' -e FLAG_B='FLAG{root_99_bbbbbb}' -e FLAG_C='FLAG{cleanup_99_cccccc}' \
  hackapi/firewall-3-ssh:1.0
ssh -p 2299 intern@localhost          # password: hackapi2026  → find / -user dani 2>/dev/null
docker rm -f fw3-smoke
```
- [ ] SSH login works; `find / -user dani 2>/dev/null` lists the hidden `.timesheet_dani.jpg`.

### A7. Save the image to a tarball
```bash
docker save hackapi/firewall-3-ssh:1.0 -o firewall-3-ssh.tar
# optional: shrink for a slow USB (docker load reads .tar.gz transparently)
gzip -k firewall-3-ssh.tar            # → firewall-3-ssh.tar.gz
sha256sum firewall-3-ssh.tar* > firewall-3-ssh.sha256
```
- [ ] `firewall-3-ssh.tar` (or `.tar.gz`) created; `.sha256` created.

> One-step alternative that skips `--load`/`docker save`:
> `docker buildx build --platform linux/arm64 -t hackapi/firewall-3-ssh:1.0 --output type=docker,dest=firewall-3-ssh.tar .`

### A8. Assemble the transfer bundle
Copy these to the **USB drive** (or `scp` to the Pi while it is still on a network
you control). Nothing else is needed on the Pi:

| File | Purpose |
|---|---|
| `firewall-3-ssh.tar` (or `.tar.gz`) | The arm64 image |
| `firewall-3-ssh.sha256` | Integrity check on the Pi |
| `spawn-fw3.sh` | Per-team provisioning (use the **fixed version in Appendix 1**) |
| `teams.txt` | `N NAME` rows (one per team) |
| `apply-ufw-docker.sh`, `boot-recovery.sh` | From Appendix 2 / 3 |

⚠️ Do **not** put `ORGANIZER_FLAGS.md`, the NPC briefing, or any `ORGANIZER_*` file
on the player-reachable Pi paths or in the Go-Bag.

---

## B. 🥧 [ARM64 · PI] Install & host — offline

> The Pi never needs the internet from this point on. Do these steps with the
> Pi on the **closed lab LAN** (or fully disconnected).

### B1. Copy the bundle onto persistent storage
The Pi is live-booted from USB with a **persistent partition** for `/opt/hackapi`.
```bash
sudo mkdir -p /opt/hackapi/backups /opt/hackapi/firewall-3-ssh /opt/hackapi/state /opt/hackapi/organizer-only
sudo chmod 700 /opt/hackapi/organizer-only /opt/hackapi/state
# from the mounted USB:
sudo cp firewall-3-ssh.tar* firewall-3-ssh.sha256 /opt/hackapi/backups/
sudo cp spawn-fw3.sh teams.txt apply-ufw-docker.sh boot-recovery.sh /opt/hackapi/firewall-3-ssh/
sudo chmod +x /opt/hackapi/firewall-3-ssh/*.sh
cd /opt/hackapi/backups && sha256sum -c firewall-3-ssh.sha256
```
- [ ] `sha256sum -c` reports **OK**.

### B2. Confirm persistence (live-boot specific ⚠️)
```bash
mount | grep /opt/hackapi            # should be a bind/real mount, NOT "overlay"
docker info | grep "Docker Root Dir" # must be under the persistent partition
touch /opt/hackapi/test && sudo reboot
# after reboot:
ls /opt/hackapi/test                 # still exists
```
- [ ] `/opt/hackapi` survives a reboot.
- [ ] Docker's data-root is on persistent storage (otherwise `docker load` is lost on every boot — see Appendix 3 for the reload fallback).
- [ ] `sudo systemctl enable docker` (Docker starts on boot).

### B3. Confirm this really is arm64, then load the image
```bash
uname -m                                        # → aarch64
docker load -i /opt/hackapi/backups/firewall-3-ssh.tar      # or the .tar.gz
#   Loaded image: hackapi/firewall-3-ssh:1.0
docker images | grep firewall-3-ssh
docker image inspect hackapi/firewall-3-ssh:1.0 --format '{{.Architecture}}'   # → arm64
```
- [ ] `uname -m` = `aarch64` and the image architecture = `arm64`.
- [ ] No `exec format error` when you start a container (that error means an amd64 image was shipped).

### B4. Move the host's own sshd off the player-facing path
Teams SSH to **containers** on `2201+`. The Pi's real admin sshd must not be a
target. Move it to **2522** and deny it from the player range.
```bash
sudo sed -i 's/^#\?Port .*/Port 2522/' /etc/ssh/sshd_config
sudo systemctl restart ssh            # if ssh.socket is active, restart it too
sudo ss -lptn 'sport = :2522'         # real admin sshd
sudo ufw allow from <ORGANIZER_IP> to any port 2522 proto tcp
sudo ufw status
```
⚠️ Keep your current SSH session open and confirm a **second** session on `:2522`
works before closing the first. From now on admin login is
`ssh -p 2522 pi@hackapi`.
- [ ] Admin sshd answers on **2522**; player subnet is denied there.

### B5. Check for port clashes, then provision all teams
Firewall 1–2 (served from the external USB) use **:80 / :5000**; Firewall 3 uses
**2201–2200+N**. They must not overlap.
```bash
sudo ss -lptn                         # nothing already on 2201..2200+N
cd /opt/hackapi/firewall-3-ssh
./spawn-fw3.sh
docker ps --filter name=fw3-team      # N containers "Up"
```
- [ ] `docker ps` shows **N** `fw3-teamN` containers, ports `2201→22 … 220N→22`.
- [ ] Resource caps actually applied (spot-check 2–3):
      `docker inspect fw3-team1 --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}'`
      → `134217728 500000000 64`

### B6. Open each team port with `ufw-docker`
Plain `ufw` is bypassed by Docker, so `ufw-docker` is used. **Two gotchas:**
- `ufw-docker allow <container> <port>` takes the **container's internal port
  (22)** — *not* the host port `220N`.
- The rule is tied to the container's **current IP**. If a container is
  recreated, **re-run the rules** (they are in `apply-ufw-docker.sh`).
```bash
sudo ./apply-ufw-docker.sh            # loops every fw3-team*  →  ufw-docker allow <name> 22/tcp
sudo ufw-docker list fw3-team1        # confirm the rule exists
```
- [ ] Every team container has an allow rule.
- [ ] From a **second device on the closed Wi-Fi**: `ssh -p 2201 intern@<pi-ip>` reaches team 1.

### B7. Air-gap proof ⚠️ (the test that actually matters)
- [ ] Disconnect the Pi from the internet (leave it on the closed lab LAN).
- [ ] `docker rm -f $(docker ps -aq --filter name=fw3-team) && ./spawn-fw3.sh && sudo ./apply-ufw-docker.sh`
      → containers **start again, same passwords/flags** (reused from `state/fw3-flags/*.env`).
- [ ] SSH from a second device still works.

### B8. Reboot recovery
- [ ] Power-cycle the Pi mid-test. Containers return via `--restart unless-stopped`;
      if the live-boot overlay wiped Docker state, `boot-recovery.sh`
      (`systemd` `@reboot`) reloads the tar, respawns, and re-applies ufw rules.
- [ ] Credentials are **identical** after the reboot.

---

## C. Network on the closed Wi-Fi — TECH + organizers
- [ ] Pi LAN IP reserved at the **router** (DHCP reservation, not Pi-side static): `________________`
- [ ] Wired uplink Pi ↔ router (frees Wi-Fi airtime for ~40 players).
- [ ] Closed SSID, WPA2, clean channel, 2.4 + 5 GHz up.
- [ ] Access slips printed from `/opt/hackapi/state/fw3-access-sheet.csv` (team → port → user).

## D. Player access & the Firewall 2 → 3 handoff
Each team's slip:
```
Team <N> — Firewall 3 Access
Host: <pi-ip>     Port: 220<N>     User: intern
Password: [handed over after the team shows the Firewall 2 flag to an organizer]
```
- **Pilot:** `INTERN_PW` is the fixed string `hackapi2026` for every team
  (`TEST_PW` in `spawn-fw3.sh`).
- **Real event:** the organizer verifies the Firewall 2 flag **in person**, then
  gives the team its password. Decide **before** the event whether `TEST_PW` stays
  fixed or is replaced by a per-team value, and re-provision accordingly.
- Flags and the root password are **per team** and random; they are generated once
  and persist in `/opt/hackapi/state/fw3-flags/team<N>.env`.

## E. Full solve dry-run (two teams in parallel) — organizers
Lore note: the file owner is **`dani`** (Dani Parkar). Older docs say `aya` — that
is out of date; the Dockerfile creates the `dani` user.
- [ ] **Connect:** `ssh -p <port> intern@<pi-ip>` → team's own shell.
- [ ] **Directory exploration:** `find / -user dani 2>/dev/null` →
      `/srv/company/archive/2025/hr/.old/.timesheet_dani.jpg`; `cat …/README_FOLDER.txt` → **Flag A**.
- [ ] **Forensics:** `strings .timesheet_dani.jpg | tail` → `# admin recovery (temp) pw: <base64>`;
      `echo '<base64>' | base64 -d` → root password.
- [ ] **Escalation:** `su -` (interactive session) with that password → `cat /root/flag.txt` → **Flag B**.
- [ ] **(Optional) Cleanup:** `cat /root/.cleanup/c2_beacon.log` → **Flag C**.
- [ ] **Isolation:** team 1's password fails on team 2's port; a file deleted in team 1 still exists in team 2.
- [ ] **Negative check:** as `intern`, `sudo -l` → not allowed.
- [ ] Compare each flag with the team's row in `/opt/hackapi/organizer-only/ORGANIZER_FW3_FLAGS.csv`.

## F. Load & resilience — TECH
- [ ] All N containers up; `docker stats` while 2+ teams run `find /` (the realistic I/O spike).
- [ ] Thermals: `vcgencmd measure_temp` < ~75 °C.
- [ ] One team stuck/broken: `docker restart fw3-team<N>` (credentials unchanged).
- [ ] Whole fleet: `./spawn-fw3.sh && sudo ./apply-ufw-docker.sh` (idempotent — Appendix 1).
- [ ] Force **new** credentials for a fresh run:
      `rm -rf /opt/hackapi/state/fw3-flags/* && docker rm -f $(docker ps -aq --filter name=fw3-team) && ./spawn-fw3.sh && sudo ./apply-ufw-docker.sh`

## G. Physical / hardware
- [ ] Pi on a known-good **5 V/3 A (Pi 4)** or official **27 W USB-C (Pi 5)** supply.
- [ ] Boot USB (boot + persistent partition) seated firmly; `nofail` in `fstab`.
- [ ] Free space on persistence: `df -h /opt/hackapi` (image layers + per-team state).

---

## Quick reference

```bash
# ── 🖥️ AMD64 EXTERNAL PC (internet) ──────────────────────────────────────────
docker run --privileged --rm tonistiivi/binfmt --install arm64        # once
docker buildx create --name hackapi-builder --driver docker-container --use   # once
cd firewall-3-ssh && rm -rf build/output
python3 build/generate_fs.py && python3 build/embed_jpeg.py
docker buildx build --platform linux/arm64 -t hackapi/firewall-3-ssh:1.0 --load .
docker image inspect hackapi/firewall-3-ssh:1.0 --format '{{.Architecture}}'  # arm64
docker save hackapi/firewall-3-ssh:1.0 -o firewall-3-ssh.tar
sha256sum firewall-3-ssh.tar > firewall-3-ssh.sha256

# ── 🥧 ARM64 PI (offline) ────────────────────────────────────────────────────
sha256sum -c /opt/hackapi/backups/firewall-3-ssh.sha256
docker load -i /opt/hackapi/backups/firewall-3-ssh.tar
cd /opt/hackapi/firewall-3-ssh && ./spawn-fw3.sh && sudo ./apply-ufw-docker.sh
docker ps --filter name=fw3-team
docker restart fw3-team7                                              # one team
```

| Item | Value |
|---|---|
| Image | `hackapi/firewall-3-ssh:1.0` (**arm64**, built on amd64 via buildx) |
| Host ports (players) | **2201–2200+N** → `ssh -p <port> intern@<pi-ip>` |
| Container port | 22 (use **22** in `ufw-docker allow`) |
| Host admin sshd | **2522**, blocked from player subnet |
| Image tarball on Pi | `/opt/hackapi/backups/firewall-3-ssh.tar` |
| Scripts on Pi | `/opt/hackapi/firewall-3-ssh/` |
| Credential persistence | `/opt/hackapi/state/fw3-flags/team<N>.env` |
| Access slips source | `/opt/hackapi/state/fw3-access-sheet.csv` |
| Organizer answer key | `/opt/hackapi/organizer-only/ORGANIZER_FW3_FLAGS.csv` (chmod 700 dir) |
| Per-container caps | `--memory 128m --memory-swap 128m --cpus 0.5 --pids-limit 64 --cap-drop NET_RAW` |
| Hardening | non-root `intern`, `PermitRootLogin no`, `AllowTcpForwarding no`, per-team isolation |
| Flag verification | In person, against the CSV — **no CTFd** |

## Definition of done
Image built **on amd64 for arm64**, shipped as a tarball, **loaded on the Pi with
no internet**; all N containers run air-gapped; a second device on the closed Wi-Fi
solves the full chain for at least two teams in parallel with verified isolation;
credentials **survive a Pi reboot unchanged**. Failures in *filesystem content, the
escalation chain, or flag values* → back to organizers (code lane). Failures in
*Docker host, LAN, power, ufw, or persistence* → your lane.

---

# Appendices — script fixes to apply before the pilot

The current `spawn-fw3.sh` has gaps versus this checklist. Use these versions
(prepared on the **🖥️ amd64 PC**, copied to the **🥧 Pi** in the A8 bundle).

## Appendix 1 — `spawn-fw3.sh` (idempotent, persistent paths, organizer CSV)
Fixes: flags/credentials now live in `/opt/hackapi/state/fw3-flags` (persistent,
matches the handoff); re-running no longer fails on "container name in use"; the
organizer answer key CSV is actually generated; run from any directory.

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"                       # teams.txt lives next to this script

STATE=/opt/hackapi/state
FLAGS_DIR=$STATE/fw3-flags
SHEET=$STATE/fw3-access-sheet.csv
ORG_CSV=/opt/hackapi/organizer-only/ORGANIZER_FW3_FLAGS.csv
IMAGE=hackapi/firewall-3-ssh:1.0

mkdir -p "$FLAGS_DIR" "$(dirname "$ORG_CSV")"
chmod 700 "$STATE" "$(dirname "$ORG_CSV")"
echo "N,NAME,PORT,USER,PASSWORD" > "$SHEET"
echo "N,NAME,FLAG_A,FLAG_B,FLAG_C,ROOTPW" > "$ORG_CSV"

TEST_PW="hackapi2026"   # fixed string, same for every team (pilot). Replace for the real event.

while read -r N NAME; do
  [ -z "$N" ] && continue
  ENVFILE=$FLAGS_DIR/team$N.env
  if [ -f "$ENVFILE" ]; then
    source "$ENVFILE"                      # reuse → credentials survive re-provisioning
  else
    INTERN_PW="$TEST_PW"
    ROOTPW=$(openssl rand -hex 4)
    FLAG_A="FLAG{dir_${N}_$(openssl rand -hex 3)}"
    FLAG_B="FLAG{root_${N}_$(openssl rand -hex 3)}"
    FLAG_C="FLAG{cleanup_${N}_$(openssl rand -hex 3)}"
    cat > "$ENVFILE" <<INNER
INTERN_PW=$INTERN_PW
ROOTPW=$ROOTPW
FLAG_A=$FLAG_A
FLAG_B=$FLAG_B
FLAG_C=$FLAG_C
INNER
    chmod 600 "$ENVFILE"
  fi

  docker rm -f "fw3-team$N" >/dev/null 2>&1 || true     # makes re-runs safe

  docker run -d --name "fw3-team$N" \
    -p $((2200+N)):22 \
    -e TEAM="$N" -e INTERN_PW="$INTERN_PW" -e ROOTPW="$ROOTPW" \
    -e FLAG_A="$FLAG_A" -e FLAG_B="$FLAG_B" -e FLAG_C="$FLAG_C" \
    --memory 128m --memory-swap 128m --cpus 0.5 --pids-limit 64 \
    --cap-drop NET_RAW \
    --restart unless-stopped \
    "$IMAGE"

  echo "$N,$NAME,$((2200+N)),intern,$INTERN_PW" >> "$SHEET"
  echo "$N,$NAME,$FLAG_A,$FLAG_B,$FLAG_C,$ROOTPW" >> "$ORG_CSV"
done < teams.txt

echo "Done. Now run:  sudo ./apply-ufw-docker.sh"
```

## Appendix 2 — `apply-ufw-docker.sh` (re-run after every spawn)
```bash
#!/bin/bash
# ufw-docker takes the CONTAINER port (22), and binds to the container's current IP.
set -e
for c in $(docker ps --format '{{.Names}}' --filter name=fw3-team); do
  ufw-docker delete allow "$c" >/dev/null 2>&1 || true   # drop stale rule from an old IP
  ufw-docker allow "$c" 22/tcp
done
ufw status | grep -c ALLOW
```

## Appendix 3 — `boot-recovery.sh` (systemd `@reboot`)
```bash
#!/bin/bash
# Safe on a persistent Docker root (no-op reload) and on a wiped live-boot overlay (reloads from tar).
set -e
until docker info >/dev/null 2>&1; do sleep 2; done
if ! docker image inspect hackapi/firewall-3-ssh:1.0 >/dev/null 2>&1; then
  docker load -i /opt/hackapi/backups/firewall-3-ssh.tar
fi
cd /opt/hackapi/firewall-3-ssh
./spawn-fw3.sh
./apply-ufw-docker.sh
```
Hook it up once on the Pi:
```bash
sudo tee /etc/systemd/system/fw3-recovery.service >/dev/null <<'EOF'
[Unit]
Description=Hack-A-PI Firewall 3 recovery
After=docker.service network-online.target
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/opt/hackapi/firewall-3-ssh/boot-recovery.sh
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable fw3-recovery.service
```

## Appendix 4 — Known doc/code mismatches to clean up
- `ORGANIZER_FLAGS.md` and the NPC briefing still say file owner **`aya`** and
  `.timesheet_aya.jpg`; the build uses **`dani`** / `.timesheet_dani.jpg`.
- Any remaining **CTFd** mentions in Firewall 3 docs should be removed (flags are
  verified in person).
- `export-fw3-access.sh` / `firewall-2-web/team_access.json` are only needed if
  Firewall 2 later issues per-team passwords automatically; they are **not**
  required for the in-person handoff described in Section D.
