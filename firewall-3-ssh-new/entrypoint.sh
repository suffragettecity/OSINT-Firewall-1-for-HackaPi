#!/bin/bash
set -e
# injected at `docker run`: TEAM, INTERN_PW, ROOTPW, FLAG_A, FLAG_B, FLAG_C

echo "intern:${INTERN_PW}" | chpasswd
echo "root:${ROOTPW}" | chpasswd

sed -i "s/FLAG_A_PLACEHOLDER/$FLAG_A/" \
  /srv/company/archive/2025/hr/.old/README_FOLDER.txt

python3 - <<PY
import base64
path = "/srv/company/archive/2025/hr/.old/.timesheet_dani.jpg"
with open(path, "rb") as f: data = f.read()
b64pw = base64.b64encode("${ROOTPW}".encode()).decode()
data = data.replace(b"__ROOTPW_B64__", b64pw.encode())
with open(path, "wb") as f: f.write(data)
PY

mkdir -p /root
echo "$FLAG_B" > /root/flag.txt
chmod 700 /root
chmod 600 /root/flag.txt

# ---- Challenge 3: malware cleanup (now MANDATORY, verified) ----------------
# FLAG_C is NOT embedded in any file the player can just cat. It is stored
# only in a root-only secret file and is released into
# /root/CLEANUP_VERIFIED.txt by a background watcher, and only once BOTH
# malware artifacts have actually been deleted from /root/.cleanup/. Same
# access gate as Flag B: everything here lives under /root (700), so none of
# this is reachable before privilege escalation.
if [ -n "${FLAG_C:-}" ]; then
  mkdir -p /root/.cleanup
  cp /opt/malware/malware_dropper.sh /opt/malware/c2_beacon.log /root/.cleanup/
  chmod 700 /root/.cleanup
  chmod 600 /root/.cleanup/malware_dropper.sh /root/.cleanup/c2_beacon.log

  mkdir -p /root/.fw3_secret
  chmod 700 /root/.fw3_secret
  printf '%s\n' "$FLAG_C" > /root/.fw3_secret/FLAG_C
  chmod 600 /root/.fw3_secret/FLAG_C

  # Background verifier. Started before FLAG_C is unset below; it never reads
  # FLAG_C from its own environment or argv (nothing readable via `ps`) — it
  # reads the secret file directly at verification time, as root.
  nohup /opt/malware/watch_cleanup.sh >/var/log/fw3-cleanup-watch.log 2>&1 &
  disown
else
  echo "WARN: FLAG_C not set — Challenge 3 will not be solvable in this container." >&2
fi

cat <<BANNER > /etc/issue.net
This system is for authorized security assessment only — Team ${TEAM}.
BANNER

unset INTERN_PW ROOTPW FLAG_A FLAG_B FLAG_C
exec /usr/sbin/sshd -D
