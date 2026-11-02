# Hack-A-PI

A three-stage, in-person pentest exercise set inside a fictional company, **NPC Inc**.
Teams recon a company social feed, break into a staff portal, then work through a
compromised Linux server. Everything runs **offline** on a closed network.

> **No CTFd.** Players report answers **in person** to an organizer/NPC, who checks
> them against the organizer sheets and records progress on the performance sheet.

```
 Firewall 1            Firewall 2             Firewall 3
 OSINT recon     ───►  Web exploitation ───►  SSH / forensics
 (NPC Pulse feed)      (Staff Portal)         (per-team container)
 recover /internal-    forge admin cookie,    find hidden file, extract root
 portal                IDOR -> FLAG{...}      password, escalate, clean up malware
                       (= F3 SSH password)
```

---

## Repository layout

```
.
├── combined.py                  WSGI dispatcher: serves F1 + F2 as ONE site on ONE port
├── Dockerfile                   image for the combined web app (F1 + F2)
├── docker-compose.yml           runs the combined web app (host :80 -> container :8080)
├── requirements.txt             Flask + waitress
├── README_COMBINED.md           how the F1/F2 dispatcher works
├── HackAPI_Walkthrough.md       ORGANIZER-ONLY  essential end-to-end solve
├── HackAPI_Flag_Performance_Sheet.md   ORGANIZER-ONLY  answer key + scoreboard
│
├── firewall-1-osint/            Firewall 1: "NPC Pulse" social feed (Flask)
│   ├── app.py  config.py  data/  templates/  static/  tests/
│   ├── LLM_HINTS.md             hint pack for the event LLM (player-facing helper)
│   ├── ORGANIZER_SOLUTION.md    ORGANIZER-ONLY
│   └── CHALLENGE_DOC.md         ORGANIZER-ONLY  pentest brief
│
├── firewall-2-web/              Firewall 2: NPC Inc corporate site + staff portal (Flask)
│   ├── app.py  templates/  static/
│   ├── ORGANIZER_FLAGS.md       ORGANIZER-ONLY
│   └── NPC_BRIEFING_Dani_Parkar.md   ORGANIZER-ONLY  in-person hint ladder
│
└── firewall-3-ssh-new/          Firewall 3: per-team SSH sandbox (Docker + Debian)
    ├── Dockerfile  entrypoint.sh  sshd_config
    ├── build/generate_fs.py  build/embed_jpeg.py     decoy tree + JPEG marker
    ├── malware/                 inert simulated malware + cleanup watcher
    ├── spawn-fw3.sh             provisions one container per team (random per-team pw)
    ├── spawn-fw3-static.sh      variant: intern password = the Firewall 2 flag
    ├── teams.txt                "N NAME" per team
    ├── Firewall_3_README.md
    └── Firewall_3_ORGANIZER_FLAGS.md / _NPC_BRIEFING.md / _TECH_LEAD_HANDOFF.md   ORGANIZER-ONLY
```

**Keep every file marked ORGANIZER-ONLY off the player network and out of the Go-Bag.**
`.dockerignore` excludes `*.md` and `tests/` so they are not baked into images.

---

## Event architecture

| Component | Hardware | Role |
|---|---|---|
| **Raspberry Pi** (`hackapi`, arm64, offline) | Pi + power + boot drive (extra SD card as spare) | Runs all containers. Central target for Firewall 3. |
| **External USB** | USB drive | Carries the Firewall 1-2 web app (image tarball / files). |
| **Thinkpad** | Laptop | Hosts the offline LLM and its UI (fed from `firewall-1-osint/LLM_HINTS.md`). |
| **Router** | Router + Ethernet cables | Closed network (closed SSID, WPA2) for ~40 players. DHCP reservation for the Pi; Pi on wired uplink. |

### Containerisation rule

| Firewall | State | Containers | Port(s) |
|---|---|---|---|
| 1 + 2 (combined) | Stateless (in-memory, no DB, no disk writes) | **One** container for all teams | host `:80` -> `:8080` (compose); `:5000` when run directly |
| 3 | Stateful (own filesystem, accounts, flags, root escalation) | **One per team**, `fw3-team<N>` | host `2201` ... `2200+N` -> container `22` |

Any future firewall follows the same rule: **stateless -> single instance; stateful -> one container per team.**
Everything lives under **`/opt/hackapi/`** on the Pi.

```
/opt/hackapi/
├── backups/            image tarballs + sha256
├── firewall-3-ssh/     spawn / ufw / boot-recovery scripts, teams.txt
├── state/              fw3-flags/team<N>.env, fw3-access-sheet.csv   (chmod 700)
└── organizer-only/     ORGANIZER_FW3_FLAGS.csv                      (chmod 700)
```

---

## Build and deploy: the two-machine rule

> **Never build on the Pi.** Builds need internet (base images, `apt`, `pip`) and an
> arm64 target. The Pi is air-gapped: it only **loads finished tarballs** and **runs** them.

| Tag | Machine | Arch | Internet |
|---|---|---|---|
| 🖥️ **[AMD64 · EXTERNAL PC]** | Linux build PC | x86_64 | Yes |
| 🥧 **[ARM64 · PI]** | Raspberry Pi `hackapi` | aarch64 | **No** |

Pi admin access (hostname `hackapi`, user `pi`; the password is held by the technical lead, not stored in this repo).
Admin sshd is moved to port **2522** so it is not on the player-facing port range.

### Step 1: 🖥️ [AMD64 · EXTERNAL PC] one-time setup (internet)

```bash
docker run --privileged --rm tonistiivi/binfmt --install arm64
docker run --rm --platform linux/arm64 debian:12-slim uname -m        # must print: aarch64
docker buildx create --name hackapi-builder --driver docker-container --use
docker buildx inspect --bootstrap                                      # must list linux/arm64
```

### Step 2: 🖥️ [AMD64 · EXTERNAL PC] build the combined web image (Firewalls 1 + 2)

```bash
# from the repo root
docker buildx build --platform linux/arm64 -t hackapi/combined-web:1.0 --load .
docker image inspect hackapi/combined-web:1.0 --format '{{.Architecture}}/{{.Os}}'   # MUST be arm64/linux
docker save hackapi/combined-web:1.0 -o combined-web.tar
sha256sum combined-web.tar > combined-web.sha256
```

### Step 3: 🖥️ [AMD64 · EXTERNAL PC] build the Firewall 3 image

Both generators use relative paths and **must run from `firewall-3-ssh-new/`, in this order**:

```bash
cd firewall-3-ssh-new
rm -rf build/output
python3 build/generate_fs.py         # decoy tree + README_FOLDER.txt (flag placeholder)
python3 build/embed_jpeg.py          # builds the JPEG with the root-password placeholder
grep -c FLAG_A_PLACEHOLDER build/output/srv/company/archive/2025/hr/.old/README_FOLDER.txt   # -> 1
grep -a -c __ROOTPW_B64__ build/output/srv/company/archive/2025/hr/.old/.timesheet_dani.jpg  # -> 1

docker buildx build --platform linux/arm64 -t hackapi/firewall-3-ssh:1.0 --load .
docker image inspect hackapi/firewall-3-ssh:1.0 --format '{{.Architecture}}/{{.Os}}'         # MUST be arm64/linux
docker save hackapi/firewall-3-ssh:1.0 -o firewall-3-ssh.tar
sha256sum firewall-3-ssh.tar > firewall-3-ssh.sha256
```

`assets/real.jpg` (clean base JPEG) must exist in `firewall-3-ssh-new/assets/`.

### Step 4: 🖥️ [AMD64 · EXTERNAL PC] assemble the transfer bundle (USB)

| File | Purpose |
|---|---|
| `combined-web.tar` + `.sha256` | Firewall 1-2 image |
| `firewall-3-ssh.tar` + `.sha256` | Firewall 3 image |
| `docker-compose.yml` | Runs the combined web app |
| `spawn-fw3.sh` **or** `spawn-fw3-static.sh`, `teams.txt` | Per-team provisioning |
| `apply-ufw-docker.sh`, `boot-recovery.sh` | See `Firewall_3_TECH_LEAD_HANDOFF.md`, Appendices 2-3 |

Do **not** copy any `ORGANIZER_*` file to player-reachable Pi paths.

### Step 5: 🥧 [ARM64 · PI] install and verify (offline)

```bash
uname -m                                                   # aarch64
sudo mkdir -p /opt/hackapi/{backups,firewall-3-ssh,state,organizer-only}
sudo chmod 700 /opt/hackapi/state /opt/hackapi/organizer-only
# copy bundle from USB, then:
cd /opt/hackapi/backups && sha256sum -c combined-web.sha256 && sha256sum -c firewall-3-ssh.sha256
docker load -i /opt/hackapi/backups/combined-web.tar
docker load -i /opt/hackapi/backups/firewall-3-ssh.tar
```

Confirm `/opt/hackapi` and Docker's data-root survive a reboot (live-boot persistence), and that Docker is enabled on boot.

### Step 6: 🥧 [ARM64 · PI] start Firewalls 1 + 2 (single container)

```bash
cd /opt/hackapi/<web-app-dir>            # where docker-compose.yml was copied
# FLAG defaults to the built-in value; set it in .env only if you rotate it
docker compose up -d
curl -s http://localhost/health          # -> ok
```

### Step 7: 🥧 [ARM64 · PI] start Firewall 3 (one container per team)

```bash
cd /opt/hackapi/firewall-3-ssh
./spawn-fw3-static.sh                    # or ./spawn-fw3.sh (see "Passwords" below)
sudo ./apply-ufw-docker.sh               # ufw-docker allow <container> 22/tcp  (container port, not 220N)
docker ps --filter name=fw3-team
```

Per team: `ssh -p 220<N> intern@<pi-ip>`. Resource caps: `--memory 128m --cpus 0.5 --pids-limit 64 --cap-drop NET_RAW`.
Flags and root passwords are generated once and persisted in `/opt/hackapi/state/fw3-flags/team<N>.env`
(survive reboots). To force fresh values: delete that directory's contents, remove the containers, re-run spawn.

### Step 8: 🥧 [ARM64 · PI] air-gap and reboot proof

Disconnect uplink, tear down and respawn containers (same credentials must return), SSH from a second device, then power-cycle.

---

## Passwords and the F2 -> F3 gate

Two provisioning variants exist for the Firewall 3 `intern` password:

| Script | Intern password | Gate |
|---|---|---|
| `spawn-fw3-static.sh` | The **Firewall 2 flag**, same for every team. `passwd` is disabled in each container. | Self-enforcing: typing the FW2 flag logs you in. |
| `spawn-fw3.sh` | Random per team, printed to the organizer CSV | Organizer hands it over after verifying the FW2 flag in person. |

If you rotate the Firewall 2 `FLAG`, update `INTERN_PW` in `spawn-fw3-static.sh` (or pass `INTERN_PW_OVERRIDE`) to match.

---

## Running locally (development)

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python combined.py                       # http://127.0.0.1:5000  (feed; /internal-portal = Firewall 2)
cd firewall-1-osint && python -m pytest -q
```

Firewall 1 loot rotates via `.env` (`LOOT_S1`...`LOOT_S6`); Firewall 2's flag rotates via the `FLAG` env var.
Do not change the Firewall 2 signing key unless you edit it in both `app.py` and `static/js/session.js`.

---

## Roles

| Role | Reads | Never shares |
|---|---|---|
| **Players** | Access slip (host, port, user), the feed, the LLM | Anything marked ORGANIZER-ONLY |
| **Organizers / NPCs** | Walkthrough, flag sheet, hint ladders (Dani, Aya/SOC) | Flag strings or exact commands aloud |
| **Technical lead** | Tech-lead handoff, Pi, router, ufw, persistence | Pi admin credentials |

Lane boundary: red on *challenge code* goes back to the organizers; red on *hardware, network, Docker host, power, persistence* is the technical lead's.

---

## Known inconsistencies to fix before the event

These were found while reviewing the repo. They are not covered elsewhere.

1. **FLAG_C mechanism mismatch.** `entrypoint.sh` and `watch_cleanup.sh` release FLAG_C to `/root/CLEANUP_VERIFIED.txt` after both malware files are deleted. `HackAPI_Walkthrough.md` and the Flag Performance Sheet say it appears in `/var/log/security/incident_log.txt` after an incident note is logged and the malware is removed, and the Walkthrough tells players to append a note there. The code never creates that file or checks for a note. Also, `Firewall_3_ORGANIZER_FLAGS.md` still describes Stage 3 as simply reading `c2_beacon.log`. Pick one design and align the code and all docs.
2. **`aya` vs `dani`.** `Firewall_3_ORGANIZER_FLAGS.md`, `Firewall_3_NPC_BRIEFING.md`, `Firewall_3_README.md`, and the committed `README_FOLDER.txt`/`generate_fs.py` references use or imply `aya`; the Dockerfile, `embed_jpeg.py`, and the Walkthrough use `dani`. The build is correct as `dani`; update the docs.
3. **`spawn-fw3.sh` default path** is `/opt/HackaPi/firewall-3-ssh/teams.txt` (capital H/P); the Pi uses `/opt/hackapi/...`. Linux paths are case-sensitive, so pass the path explicitly or fix the default (`spawn-fw3-static.sh` is already correct).
4. **`spawn-fw3.sh` does not lock `passwd`, does not `chmod 600` the env file, and does not truncate nothing else**; only the static variant does the hardening. Use the static variant for the real event, or port those changes.
5. **Stale `.env.example`** in `firewall-1-osint/` uses `ADI-2291`, "Lena", and `adi-setup-override-7731`; the actual defaults are `NPC-2291`, "Dani", and `npc-setup-override-7731`. Copying it unedited would change loot and break the CTFd-free answer sheet.
6. **Folder names in `README_COMBINED.md`** say `firewall1/`, `firewall2/`; the repo uses `firewall-1-osint/` and `firewall-2-web/`.
7. **Stale test note.** `test_firewall1.py` references an `aya_client()` and "lena" fixture naming; harmless, but rename for clarity.
8. **`README_FOLDER.txt`, `.old/`-target and decoy files** under `firewall-3-ssh-new/build/output/` are generated artifacts committed to the repo. Rebuild them (Step 3) rather than trusting the committed copies; decoy names are random per run.
9. **Export scripts referenced but absent**: `export-fw3-access.sh`, `apply-ufw-docker.sh`, `boot-recovery.sh` appear only in docs/appendices. Create them from the appendices in `Firewall_3_TECH_LEAD_HANDOFF.md`.

---

## Design guarantees

- **Offline.** No CDNs, fonts, or runtime network calls. Only builds need internet.
- **Isolation.** F3 teams cannot affect each other (own container, own `fw3net` IP, ICC disabled, `AllowTcpForwarding no`).
- **Safe by construction.** F1/F2 have no database, no shell-out, integer-only post routing, and whitelisted file serving. The F3 "malware" is inert and fictional.
- **Fictional data only.**
