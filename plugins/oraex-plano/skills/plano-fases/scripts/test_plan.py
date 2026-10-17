#!/usr/bin/env python3
"""Testes do plan.py (só biblioteca padrão): python3 test_plan.py"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan  # noqa: E402

EXAMPLE = HERE.parent / "examples" / "PORTAL_CLIENTE.plan.json"
EXAMPLE_DOC = HERE.parent / "examples" / "PORTAL_CLIENTE.md"


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class ValidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.p = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def errors(self, p: dict) -> list[str]:
        try:
            plan.validate(p)
        except plan.PlanError as e:
            return e.errors
        return []

    def test_example_is_valid(self) -> None:
        self.assertEqual(self.errors(self.p), [])

    def test_missing_and_unknown_fields_are_named(self) -> None:
        p = copy.deepcopy(self.p)
        del p["phases"][0]["acceptance"]
        p["phases"][1]["stauts"] = "done"
        errs = "\n".join(self.errors(p))
        self.assertIn("phases[0] (F1): falta o campo obrigatório 'acceptance'", errs)
        self.assertIn("phases[1] (F2a): campo desconhecido 'stauts'", errs)

    def test_status_rules(self) -> None:
        p = copy.deepcopy(self.p)
        p["phases"][0].pop("finished")
        p["phases"][3].pop("started")
        p["phases"][4]["finished"] = "2026-10-01"
        p["decisions"][1]["status"] = "decided"
        p["blockers"][0]["phase"] = "F9"
        errs = "\n".join(self.errors(p))
        self.assertIn("fase 'done' precisa de 'finished'", errs)
        self.assertIn("fase 'in_progress' precisa de 'started'", errs)
        self.assertIn("fase 'next' não pode ter 'finished'", errs)
        self.assertIn("decisions[1] (D2): falta o campo obrigatório 'decision'", errs)
        self.assertIn("fase 'F9' não existe", errs)

    def test_dates_and_duplicates(self) -> None:
        p = copy.deepcopy(self.p)
        p["phases"][1]["id"] = "F1"
        p["phases"][2]["started"] = "2026-13-01"
        p["phases"][0]["finished"] = "2026-09-01"
        errs = "\n".join(self.errors(p))
        self.assertIn("id repetido", errs)
        self.assertIn("data inexistente", errs)
        self.assertIn("antes de 'started'", errs)

    def test_current_phase(self) -> None:
        self.assertEqual(plan.current_phase(self.p)["id"], "F2c")
        p = copy.deepcopy(self.p)
        p["phases"][3]["status"] = "done"
        p["phases"][3]["finished"] = "2026-10-17"
        self.assertEqual(plan.current_phase(p)["id"], "F3a")


class GitFlowTest(unittest.TestCase):
    """Dois devs, um origin: o compare só libera publicação que contém a anterior."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        sh(t, "git", "init", "-q", "--bare", "origin.git")
        self.a = self.clone(t, "a")
        (self.a / "docs").mkdir()
        (self.a / "docs" / "P.plan.json").write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        (self.a / "docs" / "PORTAL_CLIENTE.md").write_text(EXAMPLE_DOC.read_text(encoding="utf-8"), encoding="utf-8")
        self.commit(self.a, "plano")
        sh(self.a, "git", "push", "-q", "origin", "HEAD:main")
        self.b = self.clone(t, "b")
        self.out = t / "out"
        self.out.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def clone(self, t: Path, name: str) -> Path:
        sh(t, "git", "clone", "-q", "origin.git", name)
        d = t / name
        sh(d, "git", "config", "user.email", f"{name}@x")
        sh(d, "git", "config", "user.name", name)
        sh(d, "git", "checkout", "-q", "-B", "main")
        return d

    def commit(self, d: Path, msg: str) -> None:
        sh(d, "git", "add", "-A")
        sh(d, "git", "commit", "-q", "-m", msg)

    def edit(self, d: Path, fn) -> None:
        f = d / "docs" / "P.plan.json"
        p = json.loads(f.read_text(encoding="utf-8"))
        fn(p)
        f.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def publish(self, d: Path, name: str) -> Path:
        out = self.out / f"{name}.html"
        out.write_text(plan.render(d / "docs" / "P.plan.json"), encoding="utf-8")
        return out

    def compare(self, d: Path, live: Path) -> tuple[int, str]:
        return plan.compare(d / "docs" / "P.plan.json", live)

    def test_dirty_plan_is_refused(self) -> None:
        self.edit(self.a, lambda p: p.update(next_action="outra"))
        with self.assertRaises(plan.PlanError):
            plan.render(self.a / "docs" / "P.plan.json")
        self.assertIn("Pré-visualização", plan.render(self.a / "docs" / "P.plan.json", allow_dirty=True))

    def test_artifact_url_alone_is_not_a_change(self) -> None:
        self.edit(self.a, lambda p: p["artifact"].update(url="https://claude.ai/artifact/abc123"))
        plan.render(self.a / "docs" / "P.plan.json")  # não levanta

    def test_two_devs_never_lose_an_update(self) -> None:
        v1 = self.publish(self.a, "v1")
        self.assertEqual(self.compare(self.a, v1)[0], 0)  # igual

        # A fecha F2c e publica.
        self.edit(self.a, lambda p: plan.validate(p) or p["phases"][3].update(status="done", finished="2026-10-17"))
        self.commit(self.a, "fecha F2c")
        code, msg = self.compare(self.a, v1)
        self.assertEqual(code, 0, msg)
        self.assertTrue(msg.startswith("à frente"))
        sh(self.a, "git", "push", "-q", "origin", "HEAD:main")
        v2 = self.publish(self.a, "v2")

        # B, sem o commit de A, decide D2: barrado até buscar e integrar.
        self.edit(self.b, lambda p: p["decisions"][1].update(status="decided", decision="bucket próprio"))
        self.commit(self.b, "decide D2")
        self.assertEqual(self.compare(self.b, v2)[0], 3)  # desconhecido
        sh(self.b, "git", "fetch", "-q")
        code, msg = self.compare(self.b, v2)
        self.assertEqual(code, 2)
        self.assertTrue(msg.startswith("divergente"))
        sh(self.b, "git", "pull", "-q", "--no-rebase", "--no-edit", "origin", "main")
        code, msg = self.compare(self.b, v2)
        self.assertEqual(code, 0, msg)
        sh(self.b, "git", "push", "-q", "origin", "HEAD:main")
        v3 = self.publish(self.b, "v3")
        html = v3.read_text(encoding="utf-8")
        self.assertIn('class="phase s-done" id="f2c"', html)
        self.assertIn("bucket próprio", html)

        # A ficou para trás: com fetch sem pull, "atrás"; depois do pull, "igual".
        sh(self.a, "git", "fetch", "-q")
        code, msg = self.compare(self.a, v3)
        self.assertEqual(code, 2)
        self.assertTrue(msg.startswith("atrás"))
        sh(self.a, "git", "pull", "-q", "--ff-only", "origin", "main")
        self.assertTrue(self.compare(self.a, v3)[1].startswith("igual"))

    def test_other_plan_is_refused(self) -> None:
        live = self.publish(self.a, "x")
        live.write_text(live.read_text(encoding="utf-8").replace('"plan_id": "portal-cliente"', '"plan_id": "outro"'),
                        encoding="utf-8")
        self.assertEqual(self.compare(self.a, live)[0], 1)

    def test_record_is_found_in_doc(self) -> None:
        html = self.publish(self.a, "r").read_text(encoding="utf-8")
        self.assertIn("Registro — F2b (2026-10-10, staging)", html)
        self.assertIn("#registro--f2b-2026-10-10-staging", html)


if __name__ == "__main__":
    unittest.main(verbosity=1)
