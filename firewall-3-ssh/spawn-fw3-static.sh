#!/bin/bash
# Firewall 3 provisioning — STATIC INTERN PASSWORD variant  [RUNS ON: ARM64 PI]
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Hack-A-PI · Firewall 3 provisioning — STATIC INTERN PASSWORD variant
#
# WHAT CHANGED vs the randomized version:
#   • The intern SSH password is now STATIC and the SAME for every team, set to
#     the Firewall 2 flag (see INTERN_PW below). A team logs into Firewall 3 by
#     typing the flag they captured in Firewall 2 — the gate enforces itself,
#     no in-person password handout needed.
#   • FLAG_A / FLAG_B / FLAG_C and the root password are still per-team random
#     and persisted per team, as before.
#   • The PLAYER access sheet does not print the password — it points teams at
#     their Firewall 2 flag instead. The organizer CSV records everything.
#   • `passwd` is disabled inside every container. Since the password is now
#     shared across all teams, letting any team run `passwd` would let them
#     lock out (or open up) every other team's container.
#
# IF YOU ROTATE THE FIREWALL 2 FLAG: update INTERN_PW below to match, or the
# password teams earned in FW2 won't open FW3.
# ─────────────────────────────────────────────────────────────────────────────

# The Firewall 2 flag = the Firewall 3 intern password (same for all teams).
# Keep this byte-for-byte identical to FW2's live FLAG value.
INTERN_PW="${INTERN_PW_OVERRIDE:-FLAG{br0k3n_4cc3ss_c0ntr0l_d4n1_p4rk4r}}"

case "$INTERN_PW" in
  FLAG\{*\}) ;;
  *) echo "ERROR: INTERN_PW does not look like FLAG{...} — check the hardcoded value or INTERN_PW_OVERRIDE." >&2; exit 1 ;;
esac

STATE=/opt/hackapi/state
ORG=/opt/hackapi/organizer-only
TEAMS_FILE="${1:-/opt/hackapi/firewall-3-ssh/teams.txt}"

mkdir -p "$STATE/fw3-flags" "$ORG"
chmod 700 "$STATE" "$ORG"

SHEET="$STATE/fw3-access-sheet.csv"      # player-facing: no flags, no password
CSV="$ORG/ORGANIZER_FW3_FLAGS.csv"       # organizer-only: everything

: > "$SHEET"
echo "N,NAME,PORT,USER,PASSWORD" >> "$SHEET"
echo "N,NAME,FLAG_A,FLAG_B,FLAG_C,ROOTPW,INTERN_PW" > "$CSV"
chmod 600 "$CSV"

# Isolated network: no shared bridge, ICC disabled, so teams can't reach
# each other's containers even as root. (Does NOT stop a player's own
# machine from hitting another team's published host port directly — see
# the note at the bottom.)
if ! docker network inspect fw3net >/dev/null 2>&1; then
  docker network create --subnet 172.30.0.0/24 \
    -o com.docker.network.bridge.enable_icc=false fw3net >/dev/null
fi

COUNT=0
while read -r N NAME; do
  [ -z "${N:-}" ] && continue
  ENVFILE="$STATE/fw3-flags/team$N.env"

  if [ -f "$ENVFILE" ]; then
    # shellcheck disable=SC1090
    source "$ENVFILE"
  else
    ROOTPW=$(openssl rand -hex 4)
    FLAG_A="FLAG{dir_${N}_$(openssl rand -hex 3)}"
    FLAG_B="FLAG{root_${N}_$(openssl rand -hex 3)}"
    FLAG_C="FLAG{cleanup_${N}_$(openssl rand -hex 3)}"
    cat > "$ENVFILE" <<INNER
ROOTPW=$ROOTPW
FLAG_A=$FLAG_A
FLAG_B=$FLAG_B
FLAG_C=$FLAG_C
INNER
    chmod 600 "$ENVFILE"
  fi

  # Force the static password regardless of anything an old env file may hold.
  INTERN_PW="${INTERN_PW_OVERRIDE:-FLAG{br0k3n_4cc3ss_c0ntr0l_d4n1_p4rk4r}}"

  # Idempotent: safe to re-run the whole fleet without name clashes.
  docker rm -f "fw3-team$N" >/dev/null 2>&1 || true

  docker run -d --name "fw3-team$N" \
    --network fw3net --ip "172.30.0.$((10 + N))" \
    -p "$((2200 + N)):22" \
    -e TEAM="$N" -e INTERN_PW="$INTERN_PW" -e ROOTPW="$ROOTPW" \
    -e FLAG_A="$FLAG_A" -e FLAG_B="$FLAG_B" -e FLAG_C="$FLAG_C" \
    --memory 128m --memory-swap 128m --cpus 0.5 --pids-limit 64 \
    --cap-drop NET_RAW \
    --restart unless-stopped \
    hackapi/firewall-3-ssh:1.0 >/dev/null

  # Shared password => stop intern from changing it (would lock out, or open
  # up, every other team). Re-applied every run since the container is
  # recreated above.
  docker exec "fw3-team$N" chmod 000 /usr/bin/passwd >/dev/null 2>&1 || \
    echo "WARN: could not lock passwd in fw3-team$N" >&2

  # Player slip: the password is their Firewall 2 flag — do not print it here.
  echo "$N,$NAME,$((2200 + N)),intern,= your Firewall 2 flag" >> "$SHEET"
  # Organizer record: the real password (the FW2 flag) is logged for reference.
  echo "$N,$NAME,$FLAG_A,$FLAG_B,$FLAG_C,$ROOTPW,$INTERN_PW" >> "$CSV"

  # Per-team firewall rule; re-applied on every (re-)run since a recreated
  # container gets a fresh internal identity.
  if command -v ufw-docker >/dev/null 2>&1; then
    ufw-docker allow "fw3-team$N" 22/tcp || true
  fi
  COUNT=$((COUNT + 1))
done < "$TEAMS_FILE"

echo "Provisioned $COUNT team(s)."
echo "Intern password (all teams) = the Firewall 2 flag."
echo "Player slips:   $SHEET"
echo "Organizer CSV:  $CSV"
