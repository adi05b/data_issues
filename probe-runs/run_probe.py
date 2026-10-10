#!/usr/bin/env python3
"""Run one SPARQL probe and snapshot it, matching the 2026-09-02 conventions.

Read-only: POSTs a SELECT/ASK to the endpoint and writes the response beside the
query. Nothing is written to the graph. Usage: run_probe.py <run_dir> <id> <file.rq>
"""

import csv
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ENDPOINT = "https://minmod.isi.edu/sparql"


def main() -> int:
    run_dir, probe_id, rq_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    run_dir.mkdir(parents=True, exist_ok=True)
    query = rq_path.read_text()
    (run_dir / f"{probe_id}.rq").write_text(query)

    started = time.perf_counter()
    sent_at = datetime.now(UTC).isoformat()
    proc = subprocess.run(
        [
            "curl", "-sS", "-m", "300", "-X", "POST", ENDPOINT,
            "-H", "Content-Type: application/sparql-query",
            "-H", "Accept: application/sparql-results+json",
            "-D", str(run_dir / f"{probe_id}.headers"),
            "--data-binary", f"@{rq_path}",
        ],
        capture_output=True,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    (run_dir / f"{probe_id}.curlerr").write_bytes(proc.stderr)
    body = proc.stdout
    (run_dir / f"{probe_id}.json").write_bytes(body)

    status = 0
    headers = (run_dir / f"{probe_id}.headers").read_text(errors="replace").splitlines()
    for line in headers:
        if line.upper().startswith("HTTP/"):
            status = int(line.split()[1])

    rows, error = 0, None
    try:
        parsed = json.loads(body)
        names = parsed["head"]["vars"]
        bindings = parsed["results"]["bindings"]
        rows = len(bindings)
        with (run_dir / f"{probe_id}.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(names)
            for binding in bindings:
                writer.writerow([binding.get(n, {}).get("value", "") for n in names])
    except Exception as exc:  # a non-JSON body is itself the finding
        error = f"{type(exc).__name__}: {exc}"

    meta = {
        "id": probe_id,
        "sent_at": sent_at,
        "http_status": status,
        "elapsed_ms": elapsed_ms,
        "bytes": len(body),
        "curl_exit": proc.returncode,
        "row_count": rows,
        "truncated_by_limit": bool(rows) and f"LIMIT {rows}" in query.upper().replace("\n", " "),
        "error": error,
    }
    (run_dir / f"{probe_id}.meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta))
    return 0 if status == 200 and error is None else 1


if __name__ == "__main__":
    sys.exit(main())
