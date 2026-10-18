# Firewall 3 — Technical Lead Handoff & Deployment Checklist
### Directory Exploration & Forensics Challenge · Hack-A-PI · Friday pilot

**Lane boundary (unchanged):** organizers ship the *challenge software*; the
**technical lead** owns the Pi / laptop / router. Red on *code* → back to us.
Red on *hardware / network / persistence* → your lane.

**What this is:** one Docker image (`hackapi/firewall-3-ssh:1.0`), spun up
as **N separate containers** — one per team — each running its own sshd on
a distinct host port (`2201`–`2200+N`). No shared filesystem between teams,
no shared Linux account. Target host: **Raspberry Pi** (arm64), live-booted
from USB with a persistent partition for `/opt/hackapi`.

---

## A. Pre-pull & build — WHILE INTERNET IS STILL UP ⚠️ critical for air-gap
- [ ] Docker installed and working on the build machine (`docker --version`).
- [ ] If building on a non-Pi machine: confirm target architecture —
      `docker version --format '{{.Server.Arch}}'`. If not arm64, cross-build:
      `docker buildx build --platform linux/arm64 -t hackapi/firewall-3-ssh:1.0 --load .`
- [ ] Image present: `docker images | grep firewall-3-ssh`
- [ ] Architecture check: `docker inspect hackapi/firewall-3-ssh:1.0 --format '{{.Architecture}}'` → must print `arm64`.
- [ ] Export for transfer: `docker save hackapi/firewall-3-ssh:1.0 -o firewall-3-ssh.tar`
- [ ] Copy `firewall-3-ssh.tar` onto the USB drive's persistent partition under `/opt/hackapi/backups/`.

## B. Persistence setup on the Pi ⚠️ the live-boot-specific step
- [ ] Confirm `/opt/hackapi` is bind-mounted to the persistent partition, not the live-boot overlay:
      `mount | grep /opt/hackapi` → should show the bind mount, not `overlay`.
- [ ] Confirm Docker's own data-root points to persistent storage:
      `docker info | grep "Docker Root Dir"` → should print a path under the persistent partition, not `/var/lib/docker` on the overlay.
- [ ] Test: `touch /opt/hackapi/test && sudo reboot`, then after reboot confirm `/opt/hackapi/test` still exists.
- [ ] `docker load -i /opt/hackapi/backups/firewall-3-ssh.tar`
- [ ] `docker images | grep firewall-3-ssh` confirms the image loaded.

## C. Stand-up — per-team provisioning
- [ ] `teams.txt` present at `/opt/hackapi/teams.txt`, one `N NAME` row per team.
- [ ] `cd /opt/hackapi/firewall-3-ssh && ./spawn-fw3.sh`
- [ ] `docker ps --filter name=fw3-team` shows **N containers running**, one per team.
- [ ] Spot-check 2–3 containers: `docker inspect fw3-team1 --format '{{.HostConfig.Memory}} {{.HostConfig.NanoCpus}} {{.HostConfig.PidsLimit}}'` confirms resource caps actually applied.

## D. Air-gap verification ⚠️ the test that actually matters
- [ ] Disconnect the host from the internet (leave it on the closed lab LAN).
- [ ] `docker rm -f $(docker ps -aq --filter name=fw3-team) && ./spawn-fw3.sh` — **containers still start, still serve, same credentials as before** (re-uses `/opt/hackapi/state/fw3-flags/*.env`, does not regenerate).
- [ ] SSH into one container from a second device on the closed network — full session works, no errors.

## E. Network reachability on the closed Wi-Fi — TECH + MUR/GDGoC
- [ ] Pi LAN IP statically reserved at the router (DHCP reservation, not Pi-side static IP — see system architecture notes): ________________
- [ ] A second device on the closed Wi-Fi reaches `ssh -p 2201 intern@<host-ip>` through `ssh -p 220N`.
- [ ] **Host sshd moved off port 22**, confirmed blocked from the player subnet: `sudo ss -lptn 'sport = :2522'` shows the real admin sshd; `sudo ufw status` confirms it's denied from the player range.
- [ ] **No port clash:** nothing else on the host is already bound to `2201`–`2200+N`. `sudo ss -lptn` checked against the full range before `spawn-fw3.sh` runs.
- [ ] `ufw-docker` rules applied for each team port (plain `ufw` does not work — Docker bypasses it):
      `sudo ufw-docker allow fw3-team<N> <port>/tcp` for every team.

## F. Flag & credential rotation — MUR/GDGoC
- [ ] Confirm `spawn-fw3.sh` is pulling `INTERN_PW` from the correct source for this event (fixed test string / per-team Firewall 2 flag / random — confirm which mode is active before the real event, not just the pilot).
- [ ] `/opt/hackapi/state/fw3-access-sheet.csv` generated, reviewed for correct team→port mapping.
- [ ] `export-fw3-access.sh` run, `firewall-2-web/team_access.json` updated, Firewall 2 container restarted to pick it up (only relevant once Firewall 2 is live).
- [ ] `ORGANIZER_FLAGS.md` and `ORGANIZER_FW3_FLAGS.csv` kept **off** the player network and out of the Go-Bag.

## G. Full solve dry-run — MUR/GDGoC
Prove the whole chain end-to-end before Friday, for at least two teams in parallel:
- [ ] **Connect:** `ssh -p <team-port> intern@<host-ip>` with the issued password → lands in that team's own shell.
- [ ] **Directory Exploration:** `find / -user aya 2>/dev/null` locates the hidden target file; `README_FOLDER.txt` next to it contains Flag A.
- [ ] **Forensics:** `strings .timesheet_aya.jpg | tail` reveals the base64-encoded root password.
- [ ] **Escalation:** `su -` with the decoded password flips the prompt to `#`; `cat /root/flag.txt` returns Flag B.
- [ ] **(Optional) Cleanup:** `cat /root/.cleanup/c2_beacon.log` returns Flag C.
- [ ] **Isolation check:** team 1's password does **not** work on team 2's port; a file deleted in team 1's container still exists untouched in team 2's.
- [ ] **Negative check:** `sudo -l` as `intern` returns "not allowed" — no unintended shortcut to root.

## H. Load & resilience — TECH
- [ ] All N containers running simultaneously; `docker stats` checked while 2+ teams run `find /` concurrently (I/O-heavy — the most realistic load spike).
- [ ] Pi thermals OK under load: `vcgencmd measure_temp` < ~75 °C.
- [ ] Recovery move known: `docker restart fw3-team<N>` for a single team; `./spawn-fw3.sh` is idempotent and safe to re-run for the whole fleet (re-uses existing `.env` files rather than regenerating).
- [ ] Reboot recovery tested: Pi power-cycled mid-test, `boot-recovery.sh` (systemd `@reboot` hook) brings all containers back with identical credentials.

## I. Physical / hardware
- [ ] Pi on a **known-good 5V/3A (Pi 4) or official 27W USB-C (Pi 5)** supply.
- [ ] Wired uplink to the router if possible.
- [ ] USB drive (boot + persistent partition) seated firmly; `nofail` set in `fstab` so a boot without it doesn't hang.
- [ ] Persistent partition has free space: `df -h /opt/hackapi` — Docker layers and per-team state both live there.

---

## Quick reference

```bash
# build (once)
docker build -t hackapi/firewall-3-ssh:1.0 .
# provision all teams
./spawn-fw3.sh
# status
docker ps --filter name=fw3-team
# restart one team
docker restart fw3-team7
# full re-provision (safe, idempotent)
docker rm -f $(docker ps -aq --filter name=fw3-team) && ./spawn-fw3.sh
# export access sheet for Firewall 2 handoff
./export-fw3-access.sh
```

| Item | Value |
|---|---|
| Host ports (participants) | **2201–2200+N** → `ssh -p <port> intern@<host-ip>` |
| Container port (internal) | 22 |
| Host's real sshd | moved to **2522**, blocked from player subnet |
| Challenge 1 flag location | `README_FOLDER.txt` beside the hidden target file |
| Challenge 2 flag location | `/root/flag.txt`, readable only as root |
| Challenge 3 flag location | `/root/.cleanup/c2_beacon.log` (optional) |
| Credential persistence | `/opt/hackapi/state/fw3-flags/team<N>.env` |
| Hardening in place | non-root `intern` user, per-container resource caps, `cap-drop NET_RAW`, no TCP forwarding |

## Definition of done
All N containers run **air-gapped**, a second device on the closed Wi-Fi
solves the full chain for at least two teams in parallel with verified
isolation, and credentials **survive a full Pi reboot unchanged.** Anything
failing on *filesystem content, the escalation chain, or flag values* →
back to organizers (code lane). Anything failing on *Docker host, LAN,
power, or persistence* → your lane.
