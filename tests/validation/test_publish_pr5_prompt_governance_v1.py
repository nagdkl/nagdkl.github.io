from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
import zipfile
import sys

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts/human_node/publish_pr5_prompt_governance_v1.py"
spec = importlib.util.spec_from_file_location("publisher", MODULE_PATH)
assert spec and spec.loader
publisher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = publisher
spec.loader.exec_module(publisher)


def build_bundle(path: Path, *, traversal: bool = False) -> str:
    files = {rel: f"fixture:{rel}\n".encode() for rel in publisher.SOURCE_PATHS}
    manifest = {
        "write_set": list(publisher.SOURCE_PATHS),
        "files": {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()},
    }
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("bundle-manifest.json", json.dumps(manifest))
        for rel, data in files.items():
            zf.writestr(rel, data)
        if traversal:
            zf.writestr("../escape", b"bad")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PublisherTests(unittest.TestCase):
    def test_source_paths_include_git_backed_publisher_and_test(self):
        self.assertIn("scripts/human_node/publish_pr5_prompt_governance_v1.py", publisher.SOURCE_PATHS)
        self.assertIn("tests/validation/test_publish_pr5_prompt_governance_v1.py", publisher.SOURCE_PATHS)
        self.assertEqual(len(publisher.SOURCE_PATHS), 6)

    def test_bundle_hash_is_required_arg_not_self_pinned(self):
        with self.assertRaises(SystemExit):
            publisher.parse_args(["--bundle", "x"])
        args = publisher.parse_args(["--bundle", "x", "--bundle-sha256", "a" * 64])
        self.assertEqual(args.bundle_sha256, "a" * 64)

    def test_safe_extract_bundle_passes_exact_pathset(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); bundle = td / "b.zip"; digest = build_bundle(bundle)
            out = publisher.safe_extract_bundle(bundle, td / "out", digest)
            self.assertEqual({p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}, set(publisher.SOURCE_PATHS) | {"bundle-manifest.json"})

    def test_safe_extract_bundle_rejects_wrong_hash(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); bundle = td / "b.zip"; build_bundle(bundle)
            with self.assertRaises(publisher.Blocked) as cm:
                publisher.safe_extract_bundle(bundle, td / "out", "0" * 64)
            self.assertEqual(cm.exception.reason, "bundle_sha256_mismatch")

    def test_safe_extract_bundle_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); bundle = td / "b.zip"; digest = build_bundle(bundle, traversal=True)
            with self.assertRaises(publisher.Blocked) as cm:
                publisher.safe_extract_bundle(bundle, td / "out", digest)
            self.assertEqual(cm.exception.reason, "unsafe_bundle_member")

    def test_mirror_lock_is_nonblocking_and_zero_retry(self):
        with tempfile.TemporaryDirectory() as td:
            lock = Path(td) / "mirror.lock"
            first = publisher.acquire_mirror_lock(lock)
            try:
                with self.assertRaises(publisher.Blocked) as cm:
                    publisher.acquire_mirror_lock(lock)
                self.assertEqual(cm.exception.reason, "mirror_busy")
            finally:
                first.close()

    def test_initialize_mirror_reuses_cache_and_refreshes_refs(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "src"; remote = td / "remote.git"; cache = td / "cache.git"; private = td / "private"
            private.mkdir()
            subprocess.run(["git","init","-q",str(src)],check=True)
            subprocess.run(["git","-C",str(src),"config","user.name","test"],check=True)
            subprocess.run(["git","-C",str(src),"config","user.email","test@example.invalid"],check=True)
            (src/"README.md").write_text("one\n")
            subprocess.run(["git","-C",str(src),"add","README.md"],check=True)
            subprocess.run(["git","-C",str(src),"commit","-qm","one"],check=True)
            subprocess.run(["git","-C",str(src),"branch","-M","main"],check=True)
            subprocess.run(["git","clone","--bare","-q",str(src),str(remote)],check=True)
            subprocess.run(["git","-C",str(src),"remote","add","origin",str(remote)],check=True)
            subprocess.run(["git","-C",str(src),"branch",publisher.BRANCH],check=True)
            subprocess.run(["git","-C",str(src),"push","-q","origin","main",publisher.BRANCH],check=True)
            steps = publisher.Steps(td/"evidence")
            first = publisher.initialize_mirror(str(remote),cache,private,steps)
            self.assertEqual(first,cache)
            first_main = publisher.mirror_ref(cache,"refs/heads/main")
            (src/"README.md").write_text("two\n")
            subprocess.run(["git","-C",str(src),"add","README.md"],check=True)
            subprocess.run(["git","-C",str(src),"commit","-qm","two"],check=True)
            subprocess.run(["git","-C",str(src),"push","-q","origin","main"],check=True)
            second = publisher.initialize_mirror(str(remote),cache,private,steps)
            self.assertEqual(second,cache)
            self.assertNotEqual(first_main,publisher.mirror_ref(cache,"refs/heads/main"))

    def test_invalid_canonical_mirror_is_preserved_and_fallback_used(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); src=td/"src"; remote=td/"remote.git"; cache=td/"cache.git"; private=td/"private"
            private.mkdir(); cache.mkdir(); (cache/"DO_NOT_DELETE").write_text("preserve\n")
            subprocess.run(["git","init","-q",str(src)],check=True)
            subprocess.run(["git","-C",str(src),"config","user.name","test"],check=True)
            subprocess.run(["git","-C",str(src),"config","user.email","test@example.invalid"],check=True)
            (src/"x").write_text("x\n"); subprocess.run(["git","-C",str(src),"add","x"],check=True); subprocess.run(["git","-C",str(src),"commit","-qm","x"],check=True)
            subprocess.run(["git","-C",str(src),"branch","-M","main"],check=True)
            subprocess.run(["git","clone","--bare","-q",str(src),str(remote)],check=True)
            subprocess.run(["git","-C",str(src),"remote","add","origin",str(remote)],check=True)
            subprocess.run(["git","-C",str(src),"branch",publisher.BRANCH],check=True); subprocess.run(["git","-C",str(src),"push","-q","origin",publisher.BRANCH],check=True)
            steps=publisher.Steps(td/"evidence")
            used=publisher.initialize_mirror(str(remote),cache,private,steps)
            self.assertNotEqual(used,cache)
            self.assertTrue((cache/"DO_NOT_DELETE").is_file())
            self.assertTrue(publisher.validate_mirror(used,str(remote)))

    def test_detached_worktree_is_ephemeral_and_mirror_survives(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); src=td/"src"; remote=td/"remote.git"; cache=td/"cache.git"; private=td/"private"; work=td/"work"
            private.mkdir(); subprocess.run(["git","init","-q",str(src)],check=True)
            subprocess.run(["git","-C",str(src),"config","user.name","test"],check=True); subprocess.run(["git","-C",str(src),"config","user.email","test@example.invalid"],check=True)
            (src/"x").write_text("x\n"); subprocess.run(["git","-C",str(src),"add","x"],check=True); subprocess.run(["git","-C",str(src),"commit","-qm","x"],check=True); subprocess.run(["git","-C",str(src),"branch","-M","main"],check=True)
            subprocess.run(["git","clone","--bare","-q",str(src),str(remote)],check=True); subprocess.run(["git","-C",str(src),"remote","add","origin",str(remote)],check=True); subprocess.run(["git","-C",str(src),"branch",publisher.BRANCH],check=True); subprocess.run(["git","-C",str(src),"push","-q","origin",publisher.BRANCH],check=True)
            mirror=publisher.initialize_mirror(str(remote),cache,private,publisher.Steps(td/"evidence")); head=publisher.mirror_ref(mirror,"refs/heads/main")
            publisher.add_detached_worktree(mirror,work,head)
            self.assertEqual(subprocess.run(["git","-C",str(work),"rev-parse","HEAD"],text=True,stdout=subprocess.PIPE,check=True).stdout.strip(),head)
            publisher.remove_worktree(mirror,work)
            self.assertFalse(work.exists()); self.assertTrue(cache.exists()); self.assertTrue(publisher.validate_mirror(cache,str(remote)))

    def test_push_uses_explicit_repo_url_not_mirror_origin_alias(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"git", "push", repo_url', source)
        self.assertNotIn('["git", "push", "origin", f"HEAD:refs/heads/{branch}"]', source)


if __name__ == "__main__":
    unittest.main()
