#!/usr/bin/env python3
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VARS_FILE = REPO_ROOT / "roles/oddish/vars/main.yml"
USER_AGENT = "check-latest-versions"

GITHUB_RELEASES = {
    "node_exporter_version": (
        "prometheus/node_exporter",
        lambda v: f"node_exporter-{v}.linux-amd64.tar.gz",
    ),
    "grype_version": (
        "anchore/grype",
        lambda v: f"grype_{v}_linux_amd64.tar.gz",
    ),
}

CONTAINER_IMAGES = {
    "prometheus_version": ("ghcr.io", "prometheus/prometheus-linux-amd64"),
    "alertmanager_version": ("ghcr.io", "prometheus/alertmanager-linux-amd64"),
    "ntfy_version": ("docker.io", "binwiederhier/ntfy"),
    "grafana_version": ("docker.io", "grafana/grafana"),
}

REGISTRY_ENDPOINTS = {
    "docker.io": (
        "https://registry-1.docker.io",
        "https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull",
    ),
    "ghcr.io": (
        "https://ghcr.io",
        "https://ghcr.io/token?scope=repository:{repo}:pull",
    ),
}

MANIFEST_ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


def request(url, headers=None, method="GET"):
    all_headers = {"User-Agent": USER_AGENT}
    all_headers.update(headers or {})
    req = urllib.request.Request(url, headers=all_headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = b"" if method == "HEAD" else resp.read()
        return body, resp.headers


def get_json(url, headers=None):
    body, _ = request(url, headers)
    return json.loads(body)


def read_pinned_versions():
    pins = {}
    for line in VARS_FILE.read_text().splitlines():
        match = re.match(r"^(\w+_version):\s*(\S+)\s*$", line)
        if match:
            pins[match.group(1)] = match.group(2)
    return pins


def github_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def checksum_from_release_file(assets, asset_name):
    for name, asset in assets.items():
        if re.search(r"(sha256sum|checksum)s?.*\.txt$", name, re.IGNORECASE):
            body, _ = request(asset["browser_download_url"])
            for line in body.decode().splitlines():
                parts = line.split()
                if len(parts) == 2 and parts[1].lstrip("*") == asset_name:
                    return parts[0]
    raise RuntimeError(f"no checksum found for {asset_name}")


def latest_github_release(repo, asset_name_for):
    release = get_json(f"https://api.github.com/repos/{repo}/releases/latest", github_headers())
    version = release["tag_name"].removeprefix("v")
    asset_name = asset_name_for(version)
    assets = {asset["name"]: asset for asset in release["assets"]}
    if asset_name not in assets:
        raise RuntimeError(f"asset {asset_name} not found in release {release['tag_name']}")
    digest = assets[asset_name].get("digest") or ""
    if digest.startswith("sha256:"):
        checksum = digest.removeprefix("sha256:")
    else:
        checksum = checksum_from_release_file(assets, asset_name)
    return version, f"sha256:{checksum}"


def registry_auth_headers(registry, repo):
    _, token_url_template = REGISTRY_ENDPOINTS[registry]
    body = get_json(token_url_template.format(repo=repo))
    token = body.get("token") or body["access_token"]
    return {"Authorization": f"Bearer {token}"}


def list_tags(registry, repo, headers):
    base_url, _ = REGISTRY_ENDPOINTS[registry]
    url = f"{base_url}/v2/{repo}/tags/list?n=1000"
    tags = []
    while url:
        body, resp_headers = request(url, headers)
        tags.extend(json.loads(body).get("tags") or [])
        link = resp_headers.get("Link", "")
        match = re.search(r'<([^>]+)>;\s*rel="?next"?', link)
        url = urllib.parse.urljoin(base_url, match.group(1)) if match else None
    return tags


def manifest_digest(registry, repo, tag, headers):
    base_url, _ = REGISTRY_ENDPOINTS[registry]
    _, resp_headers = request(
        f"{base_url}/v2/{repo}/manifests/{tag}",
        {**headers, "Accept": MANIFEST_ACCEPT},
        method="HEAD",
    )
    return resp_headers["Docker-Content-Digest"]


def tag_suffix(tag):
    match = re.fullmatch(r"(?:v?\d+(?:\.\d+)+|main)(-.+)?", tag)
    if not match:
        return None
    return match.group(1) or ""


def version_key(tag, suffix):
    match = re.fullmatch(r"v?(\d+(?:\.\d+)+)" + re.escape(suffix), tag)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def latest_container_tag(registry, repo, pinned_tag, headers):
    suffix = tag_suffix(pinned_tag)
    if suffix is None:
        raise RuntimeError(f"cannot determine variant suffix of pinned tag {pinned_tag}")
    candidates = []
    for tag in list_tags(registry, repo, headers):
        key = version_key(tag, suffix)
        if key is not None:
            candidates.append((key, tag))
    if not candidates:
        raise RuntimeError(f"no tags matching suffix '{suffix}' found in {repo}")
    return max(candidates)[1]


def check_github(var, repo, asset_name_for, pins):
    version, checksum = latest_github_release(repo, asset_name_for)
    return {
        "var": var,
        "current": pins.get(var, "?"),
        "latest": version,
        "checksum": checksum,
    }


def check_container(var, registry, repo, pins):
    pinned = pins.get(var, "")
    pinned_tag = pinned.split("@", 1)[0]
    headers = registry_auth_headers(registry, repo)
    latest_tag = latest_container_tag(registry, repo, pinned_tag, headers)
    digest = manifest_digest(registry, repo, latest_tag, headers)
    return {
        "var": var,
        "current": pinned,
        "latest": latest_tag,
        "checksum": digest,
    }


def main():
    pins = read_pinned_versions()
    results = []
    failed = False

    checks = [
        (lambda var=var, repo=repo, asset_for=asset_for: check_github(var, repo, asset_for, pins))
        for var, (repo, asset_for) in GITHUB_RELEASES.items()
    ] + [
        (lambda var=var, registry=registry, repo=repo: check_container(var, registry, repo, pins))
        for var, (registry, repo) in CONTAINER_IMAGES.items()
    ]

    for check in checks:
        try:
            results.append(check())
        except Exception as exc:
            failed = True
            print(f"error: {exc}", file=sys.stderr)

    for result in results:
        if result["var"] in CONTAINER_IMAGES:
            latest_value = f"{result['latest']}@{result['checksum']}"
        else:
            latest_value = result["latest"]
        is_current = result["current"] == latest_value or (
            result["var"] not in CONTAINER_IMAGES and result["current"] == result["latest"]
        )
        status = "up to date" if is_current else "UPDATE AVAILABLE"
        print(f"{result['var']}: {status}")
        print(f"  current:  {result['current']}")
        print(f"  latest:   {result['latest']}")
        print(f"  checksum: {result['checksum']}")
        print()

    print("Suggested values:")
    for result in results:
        if result["var"] in CONTAINER_IMAGES:
            print(f"{result['var']}: {result['latest']}@{result['checksum']}")
        else:
            print(f"{result['var']}: {result['latest']}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
