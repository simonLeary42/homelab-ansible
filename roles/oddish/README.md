# oddish

## podman containers

Podman containers are run "rootless" by unprivileged users.
Podman integrates with SystemD using a special user service unit file using the `.container` extension rather than `.service`: https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html
Relevant `systemctl` commands:

```shell
systemctl --user -M CONTAINER_USER@ status CONTAINER_NAME`
systemctl --user -M CONTAINER_USER@ start CONTAINER_NAME
systemctl --user -M CONTAINER_USER@ stop CONTAINER_NAME
systemctl --user -M CONTAINER_USER@ restart CONTAINER_NAME
```

debugging example:
```
sudo -u hookshot XDG_RUNTIME_DIR=/run/user/995 /usr/lib/systemd/system-generators/podman-system-generator --user --dryrun
```

Each podman container is assigned a subordinate UIDnumber and GIDnumber namespace of size 65536.
Each podman container should make use of the `{{ uidmap }}` and `{{ gidmap }}` variables.
See `matrix-hookshot.container.j2` for an example.

TODO: is this necessary?

```
echo 'kernel.unprivileged_userns_clone=1' | sudo tee /etc/sysctl.d/userns.conf > /dev/null
```

TODO: add users with container to systemd-journal group

TODO: changed apparmor to complain-only mode for unprivileged user namespace creation
* also installed app armor utils

TODO: matrix-hookshot: You have not configured any permissions for the bridge, which by default means all users on spockroll.duckdns.org have admin levels of control. Please adjust your config.
