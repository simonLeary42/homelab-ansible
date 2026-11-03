#!/bin/python3
import os
import pwd
import subprocess
import sys
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

# example: [systemd_user_service_exporter.py foo bar] -> services foo and bar for the current user
USER = pwd.getpwuid(os.getuid()).pw_name
SERVICES = sys.argv[1:]
PORT = 9000 + os.getuid()
print(f"monitoring services for {USER} on port {PORT}: {SERVICES}", file=sys.stderr)


class Serv(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        try:
            output_lines = []
            for service in SERVICES:
                subprocess_args = ["systemctl", "--user", "show", service]
                stdout = subprocess.check_output(subprocess_args)
                lines = stdout.decode("utf8").splitlines()
                properties = {k: v for k, v in [line.split("=", 1) for line in lines]}
                output_lines.append(
                    'systemd_unit_result_success{user="%s",name="%s.service"} %d'
                    % (USER, service, 1 if properties["Result"] == "success" else 0)
                )
                output_lines.append(
                    'systemd_unit_exec_main_status{user="%s",name="%s.service"} %d'
                    % (USER, service, int(properties["ExecMainStatus"]))
                )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(("\n".join(output_lines) + "\n").encode())
        except KeyboardInterrupt:
            raise
        except:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("something went wrong\n".encode())
            traceback.print_exc()


httpd = HTTPServer(("localhost", PORT), Serv)
httpd.serve_forever()
