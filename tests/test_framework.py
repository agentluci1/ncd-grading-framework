"""Validation: schema is valid JSON, weights and gates are consistent, HTML matches the Markdown sources."""
import contextlib
import io
import json
import shutil
import tempfile
import re
import sys
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402
import jsonschema  # noqa: E402

EXAMPLE = Path(__file__).parent.parent / "examples" / "example-grade.json"

MD = (build.ROOT / "NCD-GRADING-FRAMEWORK.md").read_text()
WEIGHTS = {"correctness": 2, "code_quality": 1.5, "security": 2, "accessibility": 1.5, "performance": 1,
           "design_polish": 1.5, "copy_quality": 1, "framework_conformance": 1, "completeness": 1.5}


def verdict(dims, criticals, gates_ok=True):
    overall = sum(dims[d] * w for d, w in WEIGHTS.items()) / sum(WEIGHTS.values())
    ok = overall >= 8.5 and min(dims.values()) >= 7 and criticals == 0 and gates_ok
    return "EXCELLENT" if ok and overall >= 9.0 else "PASS" if ok else "BLOCK"


class FrameworkTests(unittest.TestCase):
    def test_schema_is_valid_json(self):
        block = re.search(r"## 9\..*?```json\n(.*?)```", MD, re.S).group(1)
        schema = json.loads(block)
        self.assertEqual(set(schema["properties"]["dims"]["required"]), set(WEIGHTS))
        jsonschema.Draft202012Validator.check_schema(schema)
        example = json.loads(EXAMPLE.read_text())
        jsonschema.validate(example, schema)
        bad = dict(example, verdict="MAYBE")
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)
        no_evidence = json.loads(EXAMPLE.read_text())
        no_evidence["dims"]["security"]["evidence"] = []
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(no_evidence, schema)
        for broken in (dict(example, gates=[]), dict(example, usability=None),
                       dict(example, profile="website-ncd"),
                       dict(example, gates=[dict(example["gates"][0]) for _ in range(6)])):
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(broken, schema)
        site_gates = [{"id": str(i), "name": f"gate {i}", "result": "PASS", "evidence": ["shots/x.png"]} for i in range(1, 9)]
        website = dict(example, profile="website-ncd", gates=site_gates, usability=None)
        jsonschema.validate(website, schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(dict(website, usability=example["usability"]), schema)
        extra = dict(example, bonus=1)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(extra, schema)

    def test_example_arithmetic(self):
        ex = json.loads(EXAMPLE.read_text())
        dims = {d: v["score"] for d, v in ex["dims"].items()}
        overall = sum(dims[d] * w for d, w in WEIGHTS.items()) / sum(WEIGHTS.values())
        self.assertAlmostEqual(ex["overall"], round(overall, 2), places=2)
        gates_ok = all(g["result"] == "PASS" for g in ex["gates"]) and ex["usability"]["score"] >= 7
        self.assertEqual(ex["verdict"], verdict(dims, len(ex["critical_findings"]), gates_ok))

    def test_unverified_gate_blocks_high_scores(self):
        ex = json.loads(EXAMPLE.read_text())
        high = {d: 9.5 for d in WEIGHTS}
        self.assertTrue(any(g["result"] == "UNVERIFIED" for g in ex["gates"]))
        gates_ok = all(g["result"] == "PASS" for g in ex["gates"])
        self.assertEqual(verdict(high, 0, gates_ok), "BLOCK")
        self.assertEqual(verdict(high, 0, True), "EXCELLENT")

    def test_weight_table_matches(self):
        for dim, w in WEIGHTS.items():
            self.assertRegex(MD, rf"\| {dim} \| {w:.1f} \|")
        self.assertIn("**13.0**", MD)

    def test_gate_boundaries(self):
        self.assertEqual(verdict({d: 8.5 for d in WEIGHTS}, 0), "PASS")
        self.assertEqual(verdict({d: 9.0 for d in WEIGHTS}, 0), "EXCELLENT")
        self.assertEqual(verdict({d: 9.5 for d in WEIGHTS}, 1), "BLOCK")
        low = {d: 9.5 for d in WEIGHTS} | {"performance": 6.9}
        self.assertEqual(verdict(low, 0), "BLOCK")
        self.assertEqual(verdict({d: 8.49 for d in WEIGHTS}, 0), "BLOCK")
        self.assertEqual(verdict({d: 9.5 for d in WEIGHTS}, 0, gates_ok=False), "BLOCK")

    def test_html_in_sync_and_lists_render(self):
        for src, out, title in build.PAGES:
            self.assertEqual((build.ROOT / out).read_text(), build.render(src, title), f"{out} stale: run build.py")
        self.assertIn("<li>", (build.ROOT / "index.html").read_text())
        self.assertNotRegex((build.ROOT / "index.html").read_text(), r"<p>- \[ \]")
        for _, out, _ in build.PAGES:
            self.assertNotIn(" style=", (build.ROOT / out).read_text(), f"{out}: inline style blocked by CSP")


class BuildFailureTests(unittest.TestCase):
    """Run against a temporary copy so the real public outputs are never touched."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for f in build.ROOT.iterdir():
            shutil.copy(f, self.root / f.name)
        self.before = {out: (self.root / out).read_bytes() for _, out, _ in build.PAGES}

    def tearDown(self):
        self.tmp.cleanup()

    def run_with_failing_replace(self, fail_restore=False):
        real_replace, calls = build.os.replace, []

        def flaky(src, dst):
            calls.append(dst)
            if len(calls) == 2:
                raise OSError("disk full (simulated)")
            real_replace(src, dst)

        patches = [mock.patch.object(build, "render", lambda src, title, root=None: "<p>changed</p>"),
                   mock.patch.object(build.os, "replace", flaky), mock.patch("sys.stderr", new=io.StringIO())]
        if fail_restore:
            patches.append(mock.patch.object(Path, "write_bytes", side_effect=OSError("read-only")))
        with contextlib.ExitStack() as stack:
            err = [stack.enter_context(p) for p in patches][2]
            code = build.main(self.root)
        return code, err.getvalue()

    def test_second_write_failure_restores_outputs(self):
        code, err = self.run_with_failing_replace()
        self.assertEqual(code, 1)
        self.assertIn("outputs restored", err)
        for out, data in self.before.items():
            self.assertEqual((self.root / out).read_bytes(), data)
            self.assertFalse((self.root / out).with_suffix(".tmp").exists())

    def test_missing_source_changes_nothing(self):
        (self.root / "GRADE-DCN.md").unlink()
        with mock.patch("sys.stderr", new=io.StringIO()) as err:
            self.assertEqual(build.main(self.root), 1)
        self.assertIn("outputs restored", err.getvalue())
        for out, data in self.before.items():
            self.assertEqual((self.root / out).read_bytes(), data)

    def test_malformed_source_reports_cleanly(self):
        (self.root / "GRADE-DCN.md").write_bytes(b"\xff\xfe bad")
        with mock.patch("sys.stderr", new=io.StringIO()) as err:
            self.assertEqual(build.main(self.root), 1)
        self.assertIn("build failed", err.getvalue())
        for out, data in self.before.items():
            self.assertEqual((self.root / out).read_bytes(), data)

    def test_temp_write_failure_changes_nothing(self):
        real_write, calls = Path.write_text, []

        def flaky_write(path, *args, **kwargs):
            calls.append(path)
            if path.suffix == ".tmp" and len(calls) == 2:
                raise OSError("no space (simulated)")
            return real_write(path, *args, **kwargs)

        with mock.patch.object(build, "render", lambda src, title, root=None: "<p>changed</p>"), \
                mock.patch.object(Path, "write_text", flaky_write), mock.patch("sys.stderr", new=io.StringIO()) as err:
            self.assertEqual(build.main(self.root), 1)
        self.assertIn("outputs restored", err.getvalue())
        for out, data in self.before.items():
            self.assertEqual((self.root / out).read_bytes(), data)
            self.assertFalse((self.root / out).with_suffix(".tmp").exists())

    def test_restore_failure_is_reported_not_raised(self):
        code, err = self.run_with_failing_replace(fail_restore=True)
        self.assertEqual(code, 1)
        self.assertIn("NOT restored", err)


if __name__ == "__main__":
    unittest.main()
