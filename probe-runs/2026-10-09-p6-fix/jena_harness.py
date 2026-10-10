"""Docker-free stand-in for the test-kg / test-kgrel containers.

- FusekiDB._sparql_query/_sparql_update run against a throwaway Apache Jena
  5.2.0 TDB2 directory through the tdb2.tdbquery / tdb2.tdbupdate CLIs (the
  same engine and version as containers/fuseki/Dockerfile).
- `docker ...` shell commands in tests/conftest.py become no-ops.
- httpx.post raises, so nothing can reach a real store.
Postgres is a local throwaway cluster named in CFG_FILE.
"""

import json
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

JENA = Path(os.environ["JENA_HOME"])
DB = Path(tempfile.mkdtemp(prefix="kgsync-tdb2-"))
_lock = threading.Lock()
_real_check_output = subprocess.check_output


def _no_network(*a, **k):
    raise RuntimeError("network disabled in jena_harness")


class _Resp:
    status_code = 200

    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


def _jena(tool, *args):
    r = subprocess.run(
        [str(JENA / "bin" / tool), "--loc", str(DB), *args],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout


def _query(self, query):
    with _lock:
        f = DB.parent / (DB.name + ".rq")
        f.write_text(self.prefix_part + query)
        kind = "ttl" if "CONSTRUCT" in query.upper() else "json"
        return _Resp(_jena("tdb2.tdbquery", f"--results={kind}", f"--query={f}"))


def _update(self, query):
    with _lock:
        f = DB.parent / (DB.name + ".ru")
        f.write_text(self.prefix_part + query)
        _jena("tdb2.tdbupdate", f"--update={f}")
        return _Resp("")


def _check_output(cmd, *args, **kwargs):
    if isinstance(cmd, str) and cmd.startswith("docker "):
        return b""
    return _real_check_output(cmd, *args, **kwargs)


def pytest_configure(config):
    import httpx
    from minmodkg.libraries.rdf.fuseki import FusekiDB

    httpx.post = _no_network
    FusekiDB._sparql_query = _query
    FusekiDB._sparql_update = _update
    subprocess.check_output = _check_output


def pytest_unconfigure(config):
    shutil.rmtree(DB, ignore_errors=True)
