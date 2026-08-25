#!/bin/python3
import sys
import time
import getpass
import subprocess

USER2SERVICES = {
    "simon": ["hello", "hello2"],
    "prometheus": ["prometheus"],
    "grafana": ["grafana"],
    "alertmanager": ["alertmanager"],
    "hookshot": ["matrix-hookshot"],
    "synapse": ["matrix-synapse"],
}

for user, services in USER2SERVICES.items():
    for service in services:
        stdout = subprocess.check_output(["su-systemctl", user, "show", service])
        properties = dict([tuple(line.split("=", 1)) for line in stdout.decode("utf8").splitlines()])
        current_state = properties["ActiveState"].lower()
        STATES = ["activating", "active", "deactivating", "failed", "inactive"]
        assert current_state in STATES, f"unknown state '{current_state}', expected one of {STATES}"
        for state in STATES:
            val = 1 if current_state == state else 0
            print('node_systemd_unit_state_%s{user="%s",name="%s.service"}=%d' % (state, user, service, val))
