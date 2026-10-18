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

if [ -n "$FLAG_C" ]; then
  mkdir -p /root/.cleanup
  cp -r /opt/malware/* /root/.cleanup/
  sed -i "s/__FLAG_C__/$FLAG_C/" /root/.cleanup/c2_beacon.log
fi

cat <<BANNER > /etc/issue.net
This system is for authorized security assessment only — Team ${TEAM}.
BANNER

unset INTERN_PW ROOTPW FLAG_A FLAG_B FLAG_C
exec /usr/sbin/sshd -D
