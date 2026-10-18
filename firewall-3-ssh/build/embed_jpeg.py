with open("assets/real.jpg", "rb") as f:
    jpeg = f.read()

marker = b"\n# admin recovery (temp) pw: __ROOTPW_B64__\n"
with open("build/output/srv/company/archive/2025/hr/.old/.timesheet_dani.jpg", "wb") as f:
    f.write(jpeg + marker)
