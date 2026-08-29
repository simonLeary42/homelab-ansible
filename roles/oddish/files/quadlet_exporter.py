#!/bin/python3
import subprocess
import sys
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

# example: [quadlet_exporter.py foo bar bing bong] -> [(foo, bar), (bing, bong)]
USER_SERVICES = list(zip(sys.argv[1::2], sys.argv[2::2]))
print(f"monitoring services: {list(USER_SERVICES)}", file=sys.stderr)


class Serv(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            output_lines = []
            for user, service in USER_SERVICES:
                subprocess_args = ["systemctl", "--user", f"-M{user}@", "show", service]
                print("+ " + " ".join(subprocess_args), file=sys.stderr)
                stdout = subprocess.check_output(subprocess_args)
                properties = dict(
                    [
                        tuple(line.split("=", 1))
                        for line in stdout.decode("utf8").splitlines()
                    ]
                )
                current_state = properties["ActiveState"].lower()
                STATES = ["activating", "active", "deactivating", "failed", "inactive"]
                assert current_state in STATES, (
                    f"unknown state '{current_state}', expected one of {STATES}"
                )
                for state in STATES:
                    val = 1 if current_state == state else 0
                    output_lines.append(
                        'node_systemd_unit_state{user="%s",name="%s.service",state="%s"} %d'
                        % (user, service, state, val)
                    )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(("\n".join(output_lines) + "\n").encode())
        except AssertionError:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"something went wrong\n")
            traceback.print_exc()


httpd = HTTPServer(("localhost", 9999), Serv)
httpd.serve_forever()
