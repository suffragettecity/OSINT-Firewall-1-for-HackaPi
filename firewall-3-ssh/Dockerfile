FROM debian:12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server file binutils coreutils procps python3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /bin/bash intern \
    # FIX: Stage 1 ("find / -user dani") requires an actual 'dani' account to
    # own the target file. Nothing previously created one (an earlier draft
    # used 'aya', which didn't match the actual filename .timesheet_dani.jpg
    # or the NPC hint ladder), so the intended technique returned zero
    # results. 'dani' never logs in (-r system account, nologin shell) — she
    # only needs to *own* the two files below.
    && useradd -r -s /usr/sbin/nologin dani \
    && mkdir -p /run/sshd

COPY sshd_config /etc/ssh/sshd_config
COPY build/output/ /

# FIX: hand the Stage-1 target + its flag file to 'dani' so the ownership
# search works. Everything else COPY'd above stays root-owned (the decoys
# are supposed to NOT match `find / -user dani`).
RUN chown dani:dani \
      /srv/company/archive/2025/hr/.old/.timesheet_dani.jpg \
      /srv/company/archive/2025/hr/.old/README_FOLDER.txt

COPY malware/ /opt/malware/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
