#!/usr/bin/env python3
import argparse
import json
import sys


def filter_matches(report, risk_threshold, source):
    for match in report.get("matches", []):
        vulnerability = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        risk = float(vulnerability.get("risk") or 0)
        if risk >= risk_threshold:
            yield {
                "file": source,
                "id": vulnerability.get("id"),
                "severity": vulnerability.get("severity"),
                "package": artifact.get("name"),
                "version": artifact.get("version"),
                "risk": round(risk, 2),
                "fix_versions": vulnerability.get("fix", {}).get("versions", []),
            }


def main():
    parser = argparse.ArgumentParser(
        description="Filter grype JSON output for vulnerabilities with high risk."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        metavar="input",
        help="grype JSON files; '-' or no files reads stdin",
    )
    parser.add_argument(
        "--risk-threshold",
        type=float,
        default=0,
        help="minimum grype risk score",
    )
    args = parser.parse_args()

    reports = []
    for path in args.inputs or ["-"]:
        if path == "-":
            reports.append(("<stdin>", json.load(sys.stdin)))
        else:
            with open(path, encoding="utf-8") as f:
                reports.append((path, json.load(f)))

    results = sorted(
        (
            result
            for source, report in reports
            for result in filter_matches(report, args.risk_threshold, source)
        ),
        key=lambda r: r["risk"],
        reverse=True,
    )
    print(json.dumps(results, indent=2))
    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
