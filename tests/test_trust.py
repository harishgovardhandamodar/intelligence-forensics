"""Tests for D4 trust-boundary assertions."""
import os

from iforensics import trust

GOOD_COMPOSE = """services:
  app:
    volumes:
      - /host/fox-services/data:/fox-data:ro
"""


def _write(base, rel, text):
    p = os.path.join(base, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def test_audit_on_repo_passes_no_boundary_is_violated():
    r = trust.audit(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assert r["summary"]["fail"] == 0
    assert r["ok"] is True
    assert {x["rule"] for x in r["rules"]} == {"T1", "T2", "T3", "T4", "T5", "T6"}


def test_t1_fails_without_ro_mount_and_with_write_sql(tmp_path):
    b = str(tmp_path)
    _write(b, "docker-compose.yml", "volumes:\n  - /data:/fox-data\n")
    _write(b, "iforensics/store.py", "con.execute('DELETE FROM requests')\n")
    r = trust.check_t1(b)
    assert r["status"] == "fail"
    assert any("write SQL" in e for e in r["evidence"])


def test_t2_flags_server_host_but_only_warns_for_browser_cdn(tmp_path):
    b = str(tmp_path)
    _write(b, "iforensics/fox_client.py", "URL='http://203.0.113.9:9000/api'\n")
    assert trust.check_t2(b)["status"] == "fail"
    b2 = str(tmp_path / "b")
    _write(b2, "static/app.js", "const s='https://cdn.example.com/x.js'\n")
    assert trust.check_t2(b2)["status"] == "warn"
    b3 = str(tmp_path / "c")
    _write(b3, "iforensics/a.py", "URL='http://localhost:8210/x'\n")
    assert trust.check_t2(b3)["status"] == "pass"


def test_t3_fails_on_cloud_host_or_remote_ollama(tmp_path):
    b = str(tmp_path)
    _write(b, "iforensics/ollama_client.py",
           'OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")\n')
    _write(b, "iforensics/x.py", "endpoint='https://api.openai.com/v1'\n")
    assert trust.check_t3(b)["status"] == "fail"


def test_t4_detects_embedded_secret_and_docker_socket(tmp_path):
    b = str(tmp_path)
    _write(b, "docker-compose.yml", "volumes:\n  - /var/run/docker.sock:/var/run/docker.sock\n")
    assert trust.check_t4(b)["status"] == "fail"
    b2 = str(tmp_path / "b")
    _write(b2, "iforensics/config.py", 'KEY="sk-abcdefghij0123456789XYZ"\n')
    assert trust.check_t4(b2)["status"] == "fail"


def test_t6_fails_when_reconstruction_missing_label(tmp_path):
    b = str(tmp_path)
    _write(b, "iforensics/reconstruct.py",
           'open(os.path.join(dest, "RECONSTRUCTED.json"), "w")\ncaveats = []\n')
    os.makedirs(os.path.join(b, "reconstructions", "svc_a"), exist_ok=True)
    assert trust.check_t6(b)["status"] == "fail"
    _write(b, "reconstructions/svc_a/RECONSTRUCTED.json", "{}")
    assert trust.check_t6(b)["status"] == "pass"