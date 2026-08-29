import sys
import time
import getpass
import subprocess

service, = sys.argv[1:]
username = getpass.getuser()
now = int(time.time())

stdout = subprocess.check_output(["systemctl", "--user", "show", service], check=True)
properties = dict([(k, v) for k, v in line.split("=") for line in stdout.splitlines()])
current_state = properties["ActiveState"].lower()
STATES = ["activating", "active", "deactivating", "failed", "inactive"]
assert current_state in STATES, f"unknown state '{current_state}', expected one of {STATES}"

print('node_systemd_unit_state_timestamp{user="%s",name="%s.service"}=%d' % (user, service, now)
for state in STATES:
    val = 1 if current_state == state else 0
    print('node_systemd_unit_state_%s{user="%s",name="%s.service"}=%d' % (state, user, service, val)
