# oddish

## podman containers

Podman containers are run "rootless" by unprivileged users.

During `systemctl daemon-reload` (or `systemctl --user daemon-reload`), systemd reads `.container` files ([docs](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)) and feeds them through `podman-system-generator` to generate service unit files.
If the `.container` file is invalid, no error will be shown during `daemon-reload`, so you must run the generator manually:

```
sudo -u hookshot XDG_RUNTIME_DIR=/run/user/995 /usr/lib/systemd/system-generators/podman-system-generator --user --dryrun
```

To manage a user service as root:

```shell
systemctl --user -M CONTAINER_USER@ status CONTAINER_NAME`
systemctl --user -M CONTAINER_USER@ start CONTAINER_NAME
systemctl --user -M CONTAINER_USER@ stop CONTAINER_NAME
systemctl --user -M CONTAINER_USER@ restart CONTAINER_NAME
```

Podman sends the stdout/stderr from all containers to the journal by default.
You can view a container's output with `journalctl -e | grep CONTAINER_NAME` or `journalctl -f | grep CONTAINER_NAME`.

### podman rootless UID mapping

https://docs.podman.io/en/latest/markdown/podman-run.1.html#uidmap-flags-container-uid-from-uid-amount

Each podman container is assigned a subordinate UIDnumber and GIDnumber namespace of size 65536.
Each podman container should make use of the `{{ uidmap }}` and `{{ gidmap }}` variables.
See `matrix-hookshot.container.j2` for an example.

podman automatically builds its uid_map based on `/etc/subuid` before the `--uidmap` argument takes effect.
The `--uidmap` argument maps container UIDs to the "intermediate UIDs" that were created in this implicit uid_map, and then intermediate UIDs are mapped to real UIDs.

implicit uid_map example:
```
0 -> real UID of whoever called the `podman` command
1-63356 -> 1000000-10065535 (1st range in /etc/subuid)
65537-131072 -> 2000000-20063355 (2nd range in /etc/subuid)
```

* note: to show this implicit uid_map: `podman unshare cat /proc/self/uid_map`
* note: make sure to `podman system migrate` after making any changes to /etc/subuid

TODO: matrix-hookshot: You have not configured any permissions for the bridge, which by default means all users on spockroll.duckdns.org have admin levels of control. Please adjust your config.
