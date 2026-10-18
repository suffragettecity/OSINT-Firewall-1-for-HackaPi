#!/bin/bash
set -e
mkdir -p /opt/fw3-flags
: > /opt/fw3-access-sheet.csv

TEST_PW="hackapi2026"   # <-- the fixed string, same for every team. Remove when implemented with Firewall 2

while read -r N NAME; do
  ENVFILE=/opt/fw3-flags/team$N.env
  if [ -f "$ENVFILE" ]; then
    source "$ENVFILE"
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
  fi

  docker run -d --name fw3-team$N \
    -p $((2200+N)):22 \
    -e TEAM="$N" -e INTERN_PW="$INTERN_PW" -e ROOTPW="$ROOTPW" \
    -e FLAG_A="$FLAG_A" -e FLAG_B="$FLAG_B" -e FLAG_C="$FLAG_C" \
    --memory 128m --memory-swap 128m --cpus 0.5 --pids-limit 64 \
    --cap-drop NET_RAW \
    --restart unless-stopped \
    hackapi/firewall-3-ssh:1.0

  echo "$N,$NAME,$((2200+N)),$INTERN_PW" >> /opt/fw3-access-sheet.csv
done < teams.txt
