"""Reject plaintext Kubernetes Secret manifests from public GitOps paths."""

from pathlib import Path

import yaml


GITOPS_ROOTS = (Path("clusters"), Path("platform"))


def manifest_files():
    for root in GITOPS_ROOTS:
        if root.exists():
            yield from root.rglob("*.yaml")
            yield from root.rglob("*.yml")


def main():
    failures = []
    for path in sorted(manifest_files()):
        with path.open(encoding="utf-8") as stream:
            for index, document in enumerate(yaml.safe_load_all(stream), start=1):
                if not isinstance(document, dict) or document.get("kind") != "Secret":
                    continue

                sops = document.get("sops")
                payload = {
                    **(document.get("data") or {}),
                    **(document.get("stringData") or {}),
                }
                encrypted = payload and all(
                    isinstance(value, str) and value.startswith("ENC[")
                    for value in payload.values()
                )
                if not isinstance(sops, dict) or not encrypted:
                    failures.append(f"{path}:{index}")

    if failures:
        joined = "\n".join(failures)
        raise SystemExit(f"plaintext or malformed Secret manifests:\n{joined}")


if __name__ == "__main__":
    main()
