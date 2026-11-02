#!/bin/bash
set -euo pipefail

STATE=/opt/hackapi/state
ORG=/opt/hackapi/organizer-only
TEAMS_FILE="${1:-/opt/HackaPi/firewall-3-ssh/teams.txt}"

mkdir -p "$STATE/fw3-flags" "$ORG"
chmod 700 "$ORG"

SHEET="$STATE/fw3-access-sheet.csv"      # player-facing: no flags, no root pw
CSV="$ORG/ORGANIZER_FW3_FLAGS.csv"       # organizer-only: everything

: > "$SHEET"
echo "N,NAME,PORT,USER,INTERN_PW" >> "$SHEET"
echo "N,NAME,FLAG_A,FLAG_B,FLAG_C,ROOTPW,INTERN_PW" > "$CSV"

# Isolated network: no shared bridge, ICC disabled, so teams can't reach
# each other's containers even as root.
if ! docker network inspect fw3net >/dev/null 2>&1; then
  docker network create --subnet 172.30.0.0/24 \
    -o com.docker.network.bridge.enable_icc=false fw3net >/dev/null
fi

while read -r N NAME; do
  [ -z "${N:-}" ] && continue
  ENVFILE="$STATE/fw3-flags/team$N.env"

  if [ -f "$ENVFILE" ]; then
    # shellcheck disable=SC1090
    source "$ENVFILE"
  else
    INTERN_PW=$(openssl rand -hex 4)
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
  fi

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
    hackapi/firewall-3-ssh:1.0

  echo "$N,$NAME,$((2200 + N)),intern,$INTERN_PW" >> "$SHEET"
  echo "$N,$NAME,$FLAG_A,$FLAG_B,$FLAG_C,$ROOTPW,$INTERN_PW" >> "$CSV"

  # Per-team firewall rule; re-applied on every (re-)run since a recreated
  # container gets a fresh internal identity.
  if command -v ufw-docker >/dev/null 2>&1; then
    ufw-docker allow "fw3-team$N" 22/tcp || true
  fi
done < "$TEAMS_FILE"

echo "Provisioned $(wc -l < "$TEAMS_FILE") team(s)."
echo "Player slips:   $SHEET"
echo "Organizer CSV:  $CSV"
