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
Each podman container should specify `UIDMap={{ uidmap }}` and `GIDMap={{ gidmap }}`.

TODO:
```
echo 'kernel.unprivileged_userns_clone=1' | sudo tee /etc/sysctl.d/userns.conf > /dev/null
```
is this necessary?

TODO: add users with container to systemd-journal group

TODO: changed apparmor to complain-only mode for unprivileged user namespace creation
