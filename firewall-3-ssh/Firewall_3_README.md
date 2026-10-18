# Firewall 3 — Directory Exploration & Forensics Challenge
**Hack-A-PI** · per-team isolated SSH sandbox · Docker + Debian · air-gapped

A deliberately vulnerable corporate server environment, re-created once per
team as an isolated Docker container. It presents as a plain internal Linux
box — **no hacker aesthetic, no CTF flavor text, no hints in the shell.** The
intended filesystem and privilege-escalation path is real; each team's
container is fully separate from every other team's, so nothing one team
does (deleting files, filling disk, breaking their own shell) can affect
anyone else.

> **Organizer docs are intentionally separate and must stay off the player
> network:** `ORGANIZER_FLAGS.md` (flags + full solve), `NPC_BRIEFING.md`
> (in-person hint ladder), `TECH_LEAD_HANDOFF.md` (deploy + network
> checklist).

---

## Quick start

```bash
cd /opt/hackapi/firewall-3-ssh
docker build -t hackapi/firewall-3-ssh:1.0 .     # once, image is reused for every team
./spawn-fw3.sh                                    # provisions one container per team
docker ps --filter name=fw3-team                  # confirm N containers are up
```

Each team connects over SSH to their own container:

```bash
ssh -p <team-port> intern@<pi-ip>
```

Host, port, and username are printed on each team's access slip. Password
is issued as the reward for completing **Firewall 2** (see
`ORGANIZER_FLAGS.md` for the handoff mechanism).

## What's inside

```
firewall-3-ssh/
├── Dockerfile               non-root base image, arm64-compatible (Pi)
├── entrypoint.sh             per-team secret injection, runs once at container start
├── sshd_config                password auth, no root login, no TCP forwarding
├── spawn-fw3.sh               provisions/re-provisions one container per team
├── export-fw3-access.sh       exports the access sheet for the Firewall 2 handoff
├── build/
│   ├── generate_fs.py         builds the decoy directory tree + Challenge 1 target
│   ├── embed_jpeg.py          embeds the hidden root-password marker in the JPEG
│   └── output/                 generated filesystem, COPY'd into the image
├── malware/
│   ├── malware_dropper.sh      Challenge 3 decoy script
│   └── c2_beacon.log           Challenge 3 decoy log (holds the cleanup token)
├── assets/
│   └── real.jpg                 clean base image for the Challenge 2 target
└── *.md                        organizer-only docs (see above)
```

## Design guarantees

- **Fully offline.** No external calls, no CDN dependencies, no internet
  required once the image is built. Only the initial `docker build` needs
  connectivity (base image + apt packages).
- **One container per team.** Each team gets its own filesystem, its own
  `intern` and `root` accounts, its own set of flags. A deletion, crash, or
  privilege escalation in one team's container has zero effect on any
  other team.
- **Resource-capped.** `--memory 128m --cpus 0.5 --pids-limit 64` per
  container keeps one team from starving the Pi for the other N-1.
- **No network pivoting.** `AllowTcpForwarding no` in `sshd_config` and
  `--cap-drop NET_RAW` at the container level stop a team's shell from
  being used to probe other teams' containers or the Pi's own services.
- **Persistent across reboots.** Container state (passwords, flags) lives
  under `/opt/hackapi/state/fw3-flags/`, which is bind-mounted to the
  Pi's persistent partition — a mid-event reboot does not regenerate or
  lose any team's credentials.

## The challenge (one line, no spoilers)

A hidden file buried in a decoy-filled directory tree turns out to hold a
leaked root recovery password once inspected properly — escalating from
there opens up one final log that shouldn't have been readable. Full
walkthrough: `ORGANIZER_FLAGS.md`.
