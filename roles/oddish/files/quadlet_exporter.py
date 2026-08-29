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
                output_lines.append(
                    'systemd_unit_result_success{user="%s",name="%s.service"} %d'
                    % (user, service, 1 if properties["Result"] == "success" else 0)
                )
                output_lines.append(
                    'systemd_unit_exec_main_status{user="%s",name="%s.service"} %d'
                    % (user, service, int(properties["ExecMainStatus"]))
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
