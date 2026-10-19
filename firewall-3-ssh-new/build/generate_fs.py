import os, random

ROOT = "build/output"
DIRS = ["var/backups", "srv/company/archive/2024", "srv/company/archive/2025",
        "home/intern/.cache", "opt/legacy", "var/log/app"]
DECOY_NAMES = ["report_q{}.bak", "notes_{}.txt", "old_config_{}.yml",
               "backup_{}.tar", "draft_{}.docx"]

target_dir = f"{ROOT}/srv/company/archive/2025/hr/.old"
os.makedirs(target_dir, exist_ok=True)

for d in DIRS:
    full = f"{ROOT}/{d}"
    os.makedirs(full, exist_ok=True)
    for _ in range(6):
        name = random.choice(DECOY_NAMES).format(random.randint(1, 99))
        open(os.path.join(full, name), "w").write("decoy content\n")

with open(f"{target_dir}/README_FOLDER.txt", "w") as f:
    f.write("Archived HR assets — do not delete.\nFLAG_A_PLACEHOLDER\n")
