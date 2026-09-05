#!/bin/bash
set -euo pipefail
# shellcheck disable=SC2154
trap 's=$?; echo >&2 "$0: Error on line "$LINENO": $BASH_COMMAND"; exit $s' ERR
# Note that it is usually not sufficient to specify a command for this setting that only asks the service to terminate (for example, by sending some form of termination signal to it), but does not wait for it to do so.
# Since the remaining processes of the services are killed according to KillMode= and KillSignal= or RestartKillSignal= as described above immediately after the command exited, this may not result in a clean stop.
# The specified command should hence be a synchronous operation, not an asynchronous one.
# Also note that the stop operation is always performed if the service started successfully, even if the processes in the service terminated on their own or were killed.
# The stop commands must be prepared to deal with that case.
# $MAINPID will be unset if systemd knows that the main process exited by the time the stop commands are called.
# https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
if ! [ -d "/proc/$MAINPID" ]; then
    echo "server is not running?"
    exit 0
fi
/usr/local/bin/mc-rcon stop
elapsed=0
while [ "$elapsed" -lt 30 ] && [ -d "/proc/$MAINPID" ]; do
    echo "waiting for server to stop ($elapsed)..."
    elapsed=$((elapsed + 1))
    sleep 1
done
if [ "$elapsed" -ge 30 ]; then
    echo "timed out waiting for server to stop, systemd may kill the process now"
    exit 1
fi
