from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

MODULE_PATH = Path(__file__).parents[1] / "scripts/recover_pages_after_terminal_loss_v2.py"
spec = importlib.util.spec_from_file_location("recovery_v2", MODULE_PATH)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def _git(*args: str, cwd: Path) -> str:
    cp = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)
    return cp.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, str, str, str]:
    src = tmp_path / "src"
    src.mkdir()
    _git("init", "-q", cwd=src)
    _git("config", "user.name", "Synergy AQA", cwd=src)
    _git("config", "user.email", "aqa@example.invalid", cwd=src)
    (src / "_layouts").mkdir()
    (src / "index.md").write_text("# День открытых дверей\n", encoding="utf-8")
    (src / "_layouts/default.html").write_text("<main>{{ content }}</main>\n", encoding="utf-8")
    _git("add", ".", cwd=src)
    _git("commit", "-qm", "fixture", cwd=src)
    head = _git("rev-parse", "HEAD", cwd=src)
    index = _git("rev-parse", "HEAD:index.md", cwd=src)
    layout = _git("rev-parse", "HEAD:_layouts/default.html", cwd=src)
    bare = tmp_path / "remote.git"
    _git("clone", "-q", "--bare", str(src), str(bare), cwd=tmp_path)
    return bare, head, index, layout


class Handler(BaseHTTPRequestHandler):
    body = "<html>День открытых дверей</html>".encode()
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)
    def log_message(self, *_):
        pass


def serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server


def run_cli(tmp_path: Path, repo: Path, head: str, index: str, layout: str, url: str):
    state = tmp_path / "state"
    return subprocess.run([
        sys.executable, str(MODULE_PATH),
        "--repo-url", str(repo), "--live-url", url,
        "--expected-main", head, "--expected-index-blob", index,
        "--expected-layout-blob", layout, "--state-root", str(state),
        "--clone-timeout", "10", "--http-timeout", "5",
    ], text=True, capture_output=True, timeout=20)


def test_success_from_unrelated_directory(tmp_path: Path, monkeypatch):
    repo, head, index, layout = make_repo(tmp_path)
    server = serve()
    try:
        unrelated = tmp_path / "dirty-unrelated"
        unrelated.mkdir()
        (unrelated / "untracked.txt").write_text("do not touch")
        monkeypatch.chdir(unrelated)
        cp = run_cli(tmp_path, repo, head, index, layout, f"http://127.0.0.1:{server.server_port}/")
        assert cp.returncode == 0, cp.stderr
        assert "LIVE_HTTP=PASS" in cp.stdout
        assert (unrelated / "untracked.txt").read_text() == "do not touch"
    finally:
        server.shutdown()


def test_head_drift_fails_closed(tmp_path: Path):
    repo, head, index, layout = make_repo(tmp_path)
    server = serve()
    try:
        wrong = "0" * 40
        cp = run_cli(tmp_path, repo, wrong, index, layout, f"http://127.0.0.1:{server.server_port}/")
        assert cp.returncode == 78
        assert "canonical_main_drift" in cp.stderr
        assert "LIVE_HTTP=PASS" not in cp.stdout
    finally:
        server.shutdown()


def test_http_marker_missing_fails_closed(tmp_path: Path):
    repo, head, index, layout = make_repo(tmp_path)
    old = Handler.body
    Handler.body = b"<html>wrong</html>"
    server = serve()
    try:
        cp = run_cli(tmp_path, repo, head, index, layout, f"http://127.0.0.1:{server.server_port}/")
        assert cp.returncode == 78
        assert "live_http_marker_missing" in cp.stderr
    finally:
        server.shutdown()
        Handler.body = old


def test_invalid_identity_fails_before_network(tmp_path: Path):
    cp = subprocess.run([sys.executable, str(MODULE_PATH), "--expected-main", "bad", "--state-root", str(tmp_path / "state")], text=True, capture_output=True, timeout=10)
    assert cp.returncode == 78
    assert "invalid_expected_main" in cp.stderr


def test_http_probe_status_and_marker():
    server = serve()
    try:
        result = m.http_probe(f"http://127.0.0.1:{server.server_port}/", "День открытых дверей", 5)
        assert result["status"] == 200
        assert result["marker_present"] is True
    finally:
        server.shutdown()


def test_command_timeout_is_typed_blocked(tmp_path: Path):
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    git = fakebin / "git"
    git.write_text("#!/bin/sh\n/bin/sleep 5\n", encoding="utf-8")
    git.chmod(0o755)
    env = {"PATH": str(fakebin)}
    cp = subprocess.run([
        sys.executable, str(MODULE_PATH),
        "--repo-url", "https://example.invalid/repo.git",
        "--clone-timeout", "1", "--state-root", str(tmp_path / "state"),
    ], text=True, capture_output=True, timeout=10, env=env)
    assert cp.returncode == 78
    assert "command_timeout" in cp.stderr
    assert "Traceback" not in cp.stderr
    receipts = list((tmp_path / "state").glob("runs/*/receipt.json"))
    assert len(receipts) == 1
    assert '"status": "BLOCKED"' in receipts[0].read_text()


def test_missing_git_fails_closed_without_network(tmp_path: Path):
    env = {"PATH": str(tmp_path / "empty-path")}
    Path(env["PATH"]).mkdir()
    cp = subprocess.run([
        sys.executable, str(MODULE_PATH), "--state-root", str(tmp_path / "state")
    ], text=True, capture_output=True, timeout=10, env=env)
    assert cp.returncode == 78
    assert "missing_git" in cp.stderr
    assert "Traceback" not in cp.stderr


def test_repeat_success_is_safe_and_creates_distinct_receipts(tmp_path: Path):
    repo, head, index, layout = make_repo(tmp_path)
    server = serve()
    state = tmp_path / "state"
    try:
        args = [
            sys.executable, str(MODULE_PATH),
            "--repo-url", str(repo), "--live-url", f"http://127.0.0.1:{server.server_port}/",
            "--expected-main", head, "--expected-index-blob", index,
            "--expected-layout-blob", layout, "--state-root", str(state),
            "--clone-timeout", "10", "--http-timeout", "5",
        ]
        first = subprocess.run(args, text=True, capture_output=True, timeout=20)
        second = subprocess.run(args, text=True, capture_output=True, timeout=20)
        assert first.returncode == second.returncode == 0
        receipts = sorted(state.glob("runs/*/receipt.json"))
        assert len(receipts) == 2
        assert receipts[0] != receipts[1]
    finally:
        server.shutdown()


def test_read_only_source_has_no_legacy_windows_scan_or_shell_execution():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "/mnt/c/Users" not in source
    assert "shell=True" not in source
    assert "os.system" not in source
    assert "find /mnt" not in source


def test_read_only_source_does_not_embed_git_mutation_commands():
    import ast
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    string_constants = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    forbidden = {"push", "merge", "commit", "reset", "clean"}
    assert not (forbidden & string_constants)
