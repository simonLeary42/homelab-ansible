# oddish

Monolithic home server, named after the pokemon.

Services exposed:
* gitea (port 3003)
* matrix-synapse (port 8448)

Configured internally:
* apt sources
* snapd is removed
* certbot
* dynamic DNS
* wireguard
* matrix-hookshot
* apache2 (proxy for matrix-synapse)
* podman, UID namespaces
* prometheus
* prometheus node exporter
* prometheus alert manager
* grafana
* btrfs snapshots
* ssh

## usage

### variables

At time of writing, all role variables are defined inside the role, and nothing is expected to be defined at a host/group level.

### tags

* `alertmanager`
* `apache`
* `btrfs`
* `certbot`
* `gitea`
* `hookshot`
* `network`
* `node_exporter`
* `nosnapd`
* `podman`
* `prometheus`
* `ssh`
* `synapse`
* `wireguard`

## manual wifi setup

It would be easiest to use ethernet for provisioning.
If that is not desired, you can get a fresh ubuntu install connected to wifi by editing `/etc/netplan/` and starting/restarting the `wpa_supplicant` service.
See the `netplan` config file for an example.

## manual filesystem setup

This role expects that btrfs subvolumes have already been created:
* `@` mounted at `/`
* `@home` mounted at `/home`

At time of writing, the default ubuntu server installer does not create btrfs subvolumes.
After formatting the rootfs as btrfs, you have to create the new subvolumes, copy all files from the root subvolume, modify `/etc/fstab`, potentially modify grub, and reboot.

This role also expects that there is no active swap file on the `@` subvolume.
This can be done by disabling swap or creating a `@swap` subvolume and configuring the system to use that instead of `/swap.img`.
Helpful guide on creating a new swap file: https://askubuntu.com/a/1206161

## manual gitea setup

* TODO user creation

## manual matrix setup

* TODO user creation

## manual prometheus settup

* TODO user creation
* TODO import node_exporter rules

## manual grafana setup

* TODO import dashboard "node exporter full"

## podman containers

Podman containers are run "rootless" by unprivileged users.

Unfortunately, rootless systemd-integrated podman containers must be in the `--user` scope, which can make them more annoying to work with:

> Note that Quadlet units do not support running as a non-root user by defining the User, Group, or DynamicUser systemd options. If you want to run a rootless Quadlet, you will need to create the user and add the unit file to one of the above rootless unit search paths.

https://github.com/podman-container-tools/podman/discussions/20573

During `systemctl daemon-reload` (or `systemctl --user daemon-reload`), systemd reads `.container` files ([docs](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html)) and feeds them through `podman-system-generator` to generate service unit files.
If the `.container` file is invalid, no error will be shown during `daemon-reload`, so you must run the generator manually:

```
sudo -u hookshot XDG_RUNTIME_DIR=/run/user/995 /usr/lib/systemd/system-generators/podman-system-generator --user --dryrun
```

To manage a user service as root:

```shell
systemctl --user -M CONTAINER_USER@ start CONTAINER_NAME
systemctl --user -M CONTAINER_USER@ stop CONTAINER_NAME
systemctl --user -M CONTAINER_USER@ restart CONTAINER_NAME
sudo -u CONTAINER_USER XDG_RUNTIME_DIR=/run/user/CONTAINER_USER_UID_NUMBER systemctl status CONTAINER_NAME
```

The helper script `su-systemctl` is provided, and can be used like this:

```shell
su-systemctl CONTAINER_USER start CONTAINER_NAME
su-systemctl CONTAINER_USER stop CONTAINER_NAME
su-systemctl CONTAINER_USER restart CONTAINER_NAME
su-systemctl CONTAINER_USER status CONTAINER_NAME
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

### debugging rootless podman containers

Here is an example where the `grafana` container failed due to permission denied on its config file:

```console
grafana@oddish:~$ systemctl --user status grafana | grep ExecStart
    Process: 13044 ExecStart=/usr/bin/podman run --name grafana --replace --rm --cgroups=split --sdnotify=conmon -d --uidmap 0:0:1 --uidmap 1:1:65535 --gidmap 0:0:1 --gidmap 1:1:65535 -v /etc/grafana:/etc/grafana -v /var/lib/grafana:/var/lib/grafana -v /var/log/grafana:/var/log/grafana --publish 3000:3000 docker.io/grafana/grafana:13.1.3 (code=exited, status=1/FAILURE)
grafana@oddish:~$ /usr/bin/podman run --uidmap 0:0:1 --uidmap 1:1:65535 --gidmap 0:0:1 --gidmap 1:1:65535 -v /etc/grafana:/etc/grafana -v /var/lib/grafana:/var/lib/grafana -v /var/log/grafana:/var/log/grafana --publish 3000:3000 --entrypoint /bin/sh docker.io/grafana/grafana:13.1.3 -c 'stat /etc/grafana/grafana.ini'
  File: /etc/grafana/grafana.ini
  Size: 1156            Blocks: 8          IO Block: 4096   regular file
Device: fc00h/64512d    Inode: 1310775     Links: 1
Access: (0600/-rw-------)  Uid: (    0/    root)   Gid: (    0/    root)
Access: 2026-08-16 19:55:17.729561731 +0000
Modify: 2026-08-16 19:55:17.341563702 +0000
Change: 2026-08-16 19:55:17.730563332 +0000
```


I get the exact `podman` command from `systemctl status`, and I modify it to remove the `-d` argument and change the entrypoint to `stat` the config file instead.
I can then confirm that the config file is owned as `root` inside the container.
The fix for this particular problem was to make sure the container ran as its fake `root` user.
