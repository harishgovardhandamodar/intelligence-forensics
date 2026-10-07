"""Unit tests for the deterministic leak/exposure scanner (D2/D3)."""
import os
import stat

from iforensics import security as sec


def test_shannon_entropy_bounds():
    assert sec.shannon_entropy("") == 0.0
    assert sec.shannon_entropy("aaaaaaaa") == 0.0
    assert sec.shannon_entropy("abcd") == 2.0
    assert sec.shannon_entropy("aB3/c+d=" * 5) >= 3.0


def test_redact_never_echoes_full_secret():
    assert sec.redact("short") == "sh***"
    r = sec.redact("AKIAIOSFODNN7EXAMPLE")
    assert r.startswith("AKIA") and "EXAMPLE" not in r and len(r) < 20


def test_scan_text_finds_key_and_phi():
    text = "key = AKIAIOSFODNN7EXAMPLE\npatient_id: 42\nmail me a@b.co\n"
    kinds = {f["kind"] for f in sec.scan_text(text, "t")}
    assert "aws_access_key" in kinds
    assert "health_phi" in kinds
    assert "email" in kinds
    # matches are redacted in the output
    for f in sec.scan_text(text, "t"):
        assert "AKIAIOSFODNN7EXAMPLE" != f["match"]


def test_scan_text_high_entropy_token():
    tok = "Zq7Jm2Xp9Lr4Tb8Nv3Kd6Wf1Ys5Gh0Az"
    kinds = [f["kind"] for f in sec.scan_text(f"token {tok}\n", "t")]
    assert "high_entropy" in kinds


def test_scan_text_line_numbers():
    fs = sec.scan_text("clean\nkey = AKIAIOSFODNN7EXAMPLE\n", "t")
    assert fs and all(f["line"] == 2 for f in fs if f["kind"] == "aws_access_key")


def test_scan_path_skips_binary_and_big(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\x00\x00" + b"AKIAIOSFODNN7EXAMPLE")
    assert sec.scan_path(str(img)) == []  # wrong ext
    big = tmp_path / "big.json"
    big.write_text("AKIAIOSFODNN7EXAMPLE" * 40000)  # > MAX_BYTES
    assert sec.scan_path(str(big)) == []
    ok = tmp_path / "a.json"
    ok.write_text('{"k": "AKIAIOSFODNN7EXAMPLE"}')
    assert any(f["kind"] == "aws_access_key" for f in sec.scan_path(str(ok)))


def test_scan_tree_finds_and_skips(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "leak.json").write_text('{"t": "a@b.co"}')
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "cfg").write_text("a@b.co")
    assert (tmp_path / "bin.db").write_bytes  # noise
    (tmp_path / "bin.db").write_bytes(b"\x00AKIAIOSFODNN7EXAMPLE")
    fs = sec.scan_tree(str(tmp_path))
    srcs = {f["source"] for f in fs}
    assert os.path.join("sub", "leak.json") in srcs
    assert not any(s.startswith(".git") for s in srcs)


def test_permission_findings(tmp_path):
    open_file = tmp_path / "loose.md"
    open_file.write_text("hi")
    os.chmod(open_file, 0o644)
    tight = tmp_path / "tight.md"
    tight.write_text("hi")
    os.chmod(tight, 0o600)
    findings = {f["source"]: f for f in sec.permission_findings(str(tmp_path))}
    assert "loose.md" in findings
    assert findings["loose.md"]["mode"] == "0644"
    assert "tight.md" not in findings


def test_git_tracked_under_non_repo_is_empty(tmp_path):
    assert sec.git_tracked_under(str(tmp_path), "evidence") == []


class _R:
    def __init__(self, path, methods):
        self.path = path
        self.methods = methods


class _App:
    def __init__(self, routes):
        self.routes = routes


def test_audit_exposure_flags_no_auth_and_get_mutation():
    app = _App([
        _R("/api/investigate", {"GET"}),      # should be POST only
        _R("/api/runs", {"POST"}),
        _R("/api/evidence", {"GET"}),
        _R("/api/evidence/file", {"GET"}),
        _R("/", {"GET"}),
    ])
    kinds = {f["kind"] for f in sec.audit_exposure(app)}
    assert "no_auth" in kinds
    assert "side_effecting_get" in kinds
    assert "evidence_enumeration" in kinds


def test_audit_exposure_clean():
    app = _App([_R("/api/overview", {"GET"}), _R("/health", {"GET"})])
    assert sec.audit_exposure(app) == []


def test_summarize_worst_and_counts():
    s = sec.summarize([{"severity": "low"}, {"severity": "critical"},
                       {"severity": "low"}])
    assert s["total"] == 3 and s["worst"] == "critical"
    assert s["counts"]["low"] == 2 and s["counts"]["critical"] == 1


def test_entropy_ignores_prose_and_hyphenation():
    text = "Ollama-model-1b-gguf-quantized-version\n" + "consistent-configuration-values-8\n"
    blob = "the-quick-brown-fox-jumps-over-lazy-dogs-42\n"
    kinds = [f["kind"] for f in sec.scan_text(text + blob, "t")]
    assert "high_entropy" not in kinds
