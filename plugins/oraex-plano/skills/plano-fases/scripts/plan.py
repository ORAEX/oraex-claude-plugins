#!/usr/bin/env python3
"""plan.py — valida, resume e renderiza um plano em fases (<PLANO>.plan.json).

Só biblioteca padrão (Python 3.9+). O arquivo versionado no repo é a fonte da
verdade; o HTML gerado é só visualização, carimbado com o commit de onde veio.

Comandos:
  validate PLAN                         valida o schema (erro claro por campo)
  summary  PLAN                         resumo curto para o terminal
  render   PLAN -o OUT [--allow-dirty]  gera o HTML do quadro
  compare  PLAN LIVE_HTML               compara o local com a página publicada
  phase    PLAN ID --status S [--date D] muda o status de uma fase (e as datas)

Códigos de saída: 0 ok · 1 plano inválido/erro · 2 atrás ou divergente do
publicado (git pull) · 3 commit do publicado desconhecido (git fetch).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = 1
SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "page.html"

PHASE_STATUS = {
    "done": "Concluída",
    "in_progress": "Em andamento",
    "next": "Próxima",
    "pending": "Pendente",
    "dropped": "Descartada",
}
DECISION_STATUS = {"open": "Em aberto", "decided": "Decidida"}
BLOCKER_STATUS = {"open": "Aberto", "resolved": "Resolvido"}
ITEM_STATUS = {"open": "Aberta", "done": "Feita"}
LINK_KINDS = {"commit", "pr", "doc", "url"}

TOP_KEYS = {"schema_version", "id", "title", "doc", "repo", "artifact", "next_action",
            "phases", "decisions", "blockers", "open_items"}
PHASE_KEYS = {"id", "title", "delivers", "acceptance", "status", "started", "finished",
              "links", "notes"}
DECISION_KEYS = {"id", "question", "status", "options", "decision", "phase", "decided_on"}
BLOCKER_KEYS = {"id", "description", "status", "phase", "owner", "since", "resolved_on"}
ITEM_KEYS = {"text", "status", "phase", "owner"}
LINK_KEYS = {"kind", "ref", "label"}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARTIFACT_RE = re.compile(r"^https://claude\.ai/(code/)?artifact/[A-Za-z0-9-]+$")


class PlanError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("\n".join(errors))
        self.errors = errors


# ── validação ───────────────────────────────────────────────────────────────

def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PlanError([f"arquivo não encontrado: {path}"])
    except json.JSONDecodeError as e:
        raise PlanError([f"{path}: JSON inválido na linha {e.lineno}, coluna {e.colno}: {e.msg}"])
    validate(data)
    return data


def validate(p: object) -> None:
    errs: list[str] = []

    def unknown(obj: dict, allowed: set, where: str) -> None:
        for k in sorted(set(obj) - allowed):
            errs.append(f"{where}: campo desconhecido '{k}' (permitidos: {', '.join(sorted(allowed))})")

    def text(obj: dict, key: str, where: str, required: bool = True) -> None:
        v = obj.get(key)
        if v is None:
            if required:
                errs.append(f"{where}: falta o campo obrigatório '{key}'")
        elif not isinstance(v, str) or not v.strip():
            errs.append(f"{where}.{key}: deve ser texto não vazio")

    def date(obj: dict, key: str, where: str) -> str | None:
        v = obj.get(key)
        if v is None:
            return None
        if not isinstance(v, str) or not DATE_RE.match(v):
            errs.append(f"{where}.{key}: data deve ser AAAA-MM-DD (veio {v!r})")
            return None
        try:
            dt.date.fromisoformat(v)
        except ValueError:
            errs.append(f"{where}.{key}: data inexistente {v!r}")
            return None
        return v

    def enum(obj: dict, key: str, allowed: dict, where: str) -> str | None:
        v = obj.get(key)
        if v is None:
            errs.append(f"{where}: falta o campo obrigatório '{key}' ({' | '.join(allowed)})")
        elif v not in allowed:
            errs.append(f"{where}.{key}: '{v}' inválido (use {' | '.join(allowed)})")
        else:
            return v
        return None

    def items(key: str) -> list:
        v = p.get(key, [])
        if not isinstance(v, list):
            errs.append(f"'{key}' deve ser uma lista")
            return []
        return v

    if not isinstance(p, dict):
        raise PlanError(["o plano deve ser um objeto JSON"])

    unknown(p, TOP_KEYS, "plano")
    if p.get("schema_version") != SCHEMA_VERSION:
        errs.append(f"plano.schema_version: deve ser {SCHEMA_VERSION} (veio {p.get('schema_version')!r})")
    text(p, "id", "plano")
    if isinstance(p.get("id"), str) and not re.match(r"^[a-z0-9][a-z0-9-]*$", p["id"]):
        errs.append("plano.id: use minúsculas, dígitos e hífen (ex.: 'portal-cliente')")
    text(p, "title", "plano")
    text(p, "doc", "plano", required=False)
    text(p, "next_action", "plano", required=False)

    repo = p.get("repo")
    if repo is not None:
        if not isinstance(repo, dict):
            errs.append("plano.repo: deve ser um objeto {\"web_url\": ...}")
        else:
            unknown(repo, {"web_url"}, "plano.repo")
            text(repo, "web_url", "plano.repo")

    art = p.get("artifact")
    if art is not None:
        if not isinstance(art, dict):
            errs.append("plano.artifact: deve ser um objeto {\"url\": ...}")
        else:
            unknown(art, {"url"}, "plano.artifact")
            url = art.get("url")
            if url is not None and not (isinstance(url, str) and ARTIFACT_RE.match(url)):
                errs.append(f"plano.artifact.url: esperado https://claude.ai/artifact/<id> ou null (veio {url!r})")

    phases = items("phases")
    if not phases:
        errs.append("plano.phases: o plano precisa de pelo menos uma fase")
    ids: set[str] = set()
    for i, ph in enumerate(phases):
        where = f"phases[{i}]"
        if not isinstance(ph, dict):
            errs.append(f"{where}: deve ser um objeto")
            continue
        if isinstance(ph.get("id"), str):
            where = f"phases[{i}] ({ph['id']})"
            if ph["id"] in ids:
                errs.append(f"{where}: id repetido")
            ids.add(ph["id"])
        unknown(ph, PHASE_KEYS, where)
        text(ph, "id", where)
        text(ph, "title", where)
        text(ph, "delivers", where)
        text(ph, "notes", where, required=False)
        acc = ph.get("acceptance")
        if acc is None:
            errs.append(f"{where}: falta o campo obrigatório 'acceptance' (lista de critérios)")
        elif not (isinstance(acc, list) and acc and all(isinstance(a, str) and a.strip() for a in acc)):
            errs.append(f"{where}.acceptance: deve ser uma lista não vazia de textos")
        st = enum(ph, "status", PHASE_STATUS, where)
        s, f = date(ph, "started", where), date(ph, "finished", where)
        if st == "done" and not ph.get("finished"):
            errs.append(f"{where}: fase 'done' precisa de 'finished' (data em que fechou)")
        if st == "in_progress" and not ph.get("started"):
            errs.append(f"{where}: fase 'in_progress' precisa de 'started'")
        if st in ("next", "pending") and ph.get("finished"):
            errs.append(f"{where}: fase '{st}' não pode ter 'finished'")
        if s and f and f < s:
            errs.append(f"{where}: 'finished' ({f}) antes de 'started' ({s})")
        links = ph.get("links", [])
        if not isinstance(links, list):
            errs.append(f"{where}.links: deve ser uma lista")
            links = []
        for j, ln in enumerate(links):
            lw = f"{where}.links[{j}]"
            if not isinstance(ln, dict):
                errs.append(f"{lw}: deve ser um objeto {{kind, ref, label?}}")
                continue
            unknown(ln, LINK_KEYS, lw)
            if ln.get("kind") not in LINK_KINDS:
                errs.append(f"{lw}.kind: use {' | '.join(sorted(LINK_KINDS))} (veio {ln.get('kind')!r})")
            text(ln, "ref", lw)
            text(ln, "label", lw, required=False)
            if ln.get("kind") == "commit" and isinstance(ln.get("ref"), str) \
                    and not re.match(r"^[0-9a-f]{7,40}$", ln["ref"]):
                errs.append(f"{lw}.ref: commit deve ser um SHA (7–40 hex)")
            if ln.get("kind") == "pr" and isinstance(ln.get("ref"), str) \
                    and not re.match(r"^#?\d+$|^https?://", ln["ref"]):
                errs.append(f"{lw}.ref: PR deve ser '#123' ou uma URL")

    def phase_ref(obj: dict, where: str) -> None:
        ref = obj.get("phase")
        if ref is not None and ref not in ids:
            errs.append(f"{where}.phase: fase '{ref}' não existe")

    seen: set[str] = set()
    for i, d in enumerate(items("decisions")):
        where = f"decisions[{i}]" + (f" ({d.get('id')})" if isinstance(d, dict) and d.get("id") else "")
        if not isinstance(d, dict):
            errs.append(f"{where}: deve ser um objeto")
            continue
        unknown(d, DECISION_KEYS, where)
        text(d, "id", where)
        if d.get("id") in seen:
            errs.append(f"{where}: id repetido")
        seen.add(d.get("id"))
        text(d, "question", where)
        st = enum(d, "status", DECISION_STATUS, where)
        if st == "decided":
            text(d, "decision", where)
        date(d, "decided_on", where)
        opts = d.get("options")
        if opts is not None and not (isinstance(opts, list) and all(isinstance(o, str) for o in opts)):
            errs.append(f"{where}.options: deve ser uma lista de textos")
        phase_ref(d, where)

    for i, b in enumerate(items("blockers")):
        where = f"blockers[{i}]" + (f" ({b.get('id')})" if isinstance(b, dict) and b.get("id") else "")
        if not isinstance(b, dict):
            errs.append(f"{where}: deve ser um objeto")
            continue
        unknown(b, BLOCKER_KEYS, where)
        text(b, "id", where)
        if b.get("id") in seen:
            errs.append(f"{where}: id repetido (decisões e bloqueios compartilham ids)")
        seen.add(b.get("id"))
        text(b, "description", where)
        text(b, "owner", where, required=False)
        enum(b, "status", BLOCKER_STATUS, where)
        date(b, "since", where)
        date(b, "resolved_on", where)
        phase_ref(b, where)

    for i, it in enumerate(items("open_items")):
        where = f"open_items[{i}]"
        if not isinstance(it, dict):
            errs.append(f"{where}: deve ser um objeto {{text, status, phase?, owner?}}")
            continue
        unknown(it, ITEM_KEYS, where)
        text(it, "text", where)
        text(it, "owner", where, required=False)
        enum(it, "status", ITEM_STATUS, where)
        phase_ref(it, where)

    if errs:
        raise PlanError(errs)


# ── git ─────────────────────────────────────────────────────────────────────

def git(cwd: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def content_hash(plan: dict) -> str:
    """Hash do conteúdo, sem o bloco artifact (gravar a URL não é mudança de plano)."""
    body = {k: v for k, v in plan.items() if k != "artifact"}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def web_url_from_remote(remote: str | None) -> str | None:
    if not remote:
        return None
    m = re.match(r"^(?:git@|ssh://git@)([^:/]+)[:/](.+?)(?:\.git)?/?$", remote)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}"
    m = re.match(r"^https?://(?:[^@/]+@)?(.+?)(?:\.git)?/?$", remote)
    return f"https://{m.group(1)}" if m else None


def git_info(path: Path, plan: dict) -> dict:
    d = path.parent
    top = git(d, "rev-parse", "--show-toplevel")
    info = {"commit": None, "committed_at": None, "rel": path.name, "root": None,
            "web_url": (plan.get("repo") or {}).get("web_url"), "dirty": True}
    if not top:
        return info
    root = Path(top)
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    info.update(root=root, rel=rel, commit=git(root, "rev-parse", "HEAD"))
    info["committed_at"] = git(root, "log", "-1", "--format=%cI", "--", rel)
    info["web_url"] = info["web_url"] or web_url_from_remote(git(root, "remote", "get-url", "origin"))
    at_head = git(root, "show", f"HEAD:{rel}")
    if at_head is not None:
        try:
            info["dirty"] = content_hash(json.loads(at_head)) != content_hash(plan)
        except json.JSONDecodeError:
            pass
    return info


# ── modelo derivado ─────────────────────────────────────────────────────────

def current_phase(plan: dict) -> dict | None:
    phases = plan["phases"]
    for st in ("in_progress", "next"):
        for ph in phases:
            if ph["status"] == st:
                return ph
    return next((ph for ph in phases if ph["status"] == "pending"), None)


def open_(lst: list | None, status: str = "open") -> list:
    return [x for x in (lst or []) if x.get("status") == status]


def slug(heading: str) -> str:
    """Âncora no estilo do GitHub: minúsculas, sem pontuação, espaço vira hífen."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s, flags=re.UNICODE)
    return s.replace(" ", "-")


def find_records(doc: Path) -> dict[str, dict]:
    """Seções '## Registro — <ID> ...' do design-doc, indexadas pelo id da fase."""
    if not doc.is_file():
        return {}
    lines = doc.read_text(encoding="utf-8").splitlines()
    out: dict[str, dict] = {}
    for i, line in enumerate(lines):
        m = re.match(r"^(#{2,4})\s+(Registro\s*[—–-]\s*([A-Za-z0-9.]+).*)$", line)
        if not m:
            continue
        level, heading, pid = len(m.group(1)), m.group(2), m.group(3)
        body = []
        for nxt in lines[i + 1:]:
            h = re.match(r"^(#{1,6})\s", nxt)
            if h and len(h.group(1)) <= level:
                break
            body.append(nxt)
        out.setdefault(pid, {"heading": heading, "anchor": slug(heading), "body": "\n".join(body).strip()})
    return out


# ── HTML ────────────────────────────────────────────────────────────────────

def inline(s: str) -> str:
    """Escapa e aplica o markdown inline mínimo: `código`, **negrito**."""
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


def md_block(md: str) -> str:
    """Markdown mínimo do Registro: parágrafos e listas (com continuação de linha)."""
    out, para, items = [], [], []

    def flush() -> None:
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            items.clear()

    for line in md.splitlines():
        st = line.strip()
        if not st:
            flush()
        elif re.match(r"^[-*]\s+", st):
            if para:
                flush()
            items.append(re.sub(r"^[-*]\s+", "", st))
        elif items and line.startswith((" ", "\t")):
            items[-1] += " " + st
        elif st.startswith("|"):
            flush()
            out.append(f"<p class=\"mono\">{inline(st)}</p>")
        else:
            if items:
                flush()
            para.append(st)
    flush()
    return "\n".join(out)


def link_href(ln: dict, web: str | None, doc_dir: str, commit: str | None) -> str | None:
    kind, ref = ln["kind"], ln["ref"]
    if ref.startswith(("http://", "https://")):
        return ref
    if not web:
        return None
    if kind == "commit":
        return f"{web}/commit/{ref}"
    if kind == "pr":
        return f"{web}/pull/{ref.lstrip('#')}"
    if kind == "doc":
        path, _, frag = ref.partition("#")
        full = path if "/" in path or not doc_dir else f"{doc_dir}/{path}"
        return f"{web}/blob/{commit or 'HEAD'}/{full}" + (f"#{frag}" if frag else "")
    return None


def fmt_date(s: str | None) -> str:
    if not s:
        return ""
    try:
        d = dt.date.fromisoformat(s[:10])
    except ValueError:
        return html.escape(s)
    months = "jan fev mar abr mai jun jul ago set out nov dez".split()
    return f"{d.day:02d} {months[d.month - 1]} {d.year}"


def esc(s: object) -> str:
    return html.escape(str(s))


def render(path: Path, allow_dirty: bool = False) -> str:
    plan = load(path)
    g = git_info(path, plan)
    if g["dirty"] and not allow_dirty:
        raise PlanError([
            f"{g['rel']} tem mudanças fora do commit atual. A página é derivada do arquivo "
            "versionado: faça commit do plano antes de publicar (ou use --allow-dirty só para pré-visualizar)."
        ])
    web, commit = g["web_url"], g["commit"]
    root = g["root"] or path.parent
    doc_rel = None
    records: dict[str, dict] = {}
    if plan.get("doc"):
        doc_path = (path.parent / plan["doc"]).resolve()
        try:
            doc_rel = doc_path.relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            doc_rel = plan["doc"]
        records = find_records(doc_path)
    doc_dir = str(Path(doc_rel).parent) if doc_rel else ""
    doc_dir = "" if doc_dir == "." else doc_dir

    def doc_href(anchor: str = "") -> str | None:
        if not (web and doc_rel):
            return None
        return f"{web}/blob/{commit or 'HEAD'}/{doc_rel}" + (f"#{anchor}" if anchor else "")

    phases = plan["phases"]
    cur = current_phase(plan)
    done = sum(1 for ph in phases if ph["status"] == "done")
    live = [ph for ph in phases if ph["status"] != "dropped"]
    blockers = plan.get("blockers") or []
    open_blockers = open_(blockers)
    decisions = plan.get("decisions") or []
    open_dec = open_(decisions)
    items = open_(plan.get("open_items"))
    by_phase: dict[str, list] = {}
    for b in open_blockers:
        if b.get("phase"):
            by_phase.setdefault(b["phase"], []).append(b)

    # Linha do tempo
    steps = []
    for ph in phases:
        is_cur = cur is not None and ph["id"] == cur["id"]
        cls = f"step s-{ph['status']}" + (" is-current" if is_cur else "") + \
              (" has-block" if ph["id"] in by_phase else "")
        steps.append(
            f'<li class="{cls}"><a href="#{esc(slug(ph["id"]))}">'
            f'<span class="step-id">{esc(ph["id"])}</span>'
            f'<span class="step-title">{esc(ph["title"])}</span>'
            f'<span class="step-st">{PHASE_STATUS[ph["status"]]}</span></a></li>'
        )
    timeline = "\n".join(steps)

    # Cartões de fase
    cards = []
    for ph in phases:
        is_cur = cur is not None and ph["id"] == cur["id"]
        st = ph["status"]
        dates = []
        if ph.get("started"):
            dates.append(f"início {fmt_date(ph['started'])}")
        if ph.get("finished"):
            dates.append(f"fim {fmt_date(ph['finished'])}")
        check = "✓" if st == "done" else ""
        acc = "".join(f'<li><span class="box" aria-hidden="true">{check}</span>{inline(a)}</li>'
                      for a in ph["acceptance"])
        blocks = "".join(
            f'<p class="flag flag-block"><strong>Bloqueio {esc(b["id"])}</strong> · {inline(b["description"])}'
            + (f' <span class="muted">({esc(b["owner"])})</span>' if b.get("owner") else "") + "</p>"
            for b in by_phase.get(ph["id"], [])
        )
        links = []
        rec = records.get(ph["id"])
        if rec:
            href = doc_href(rec["anchor"])
            label = esc(rec["heading"])
            links.append(f'<a href="{esc(href)}">{label}</a>' if href else f"<span>{label}</span>")
        for ln in ph.get("links") or []:
            href = link_href(ln, web, doc_dir, commit)
            default = {"commit": ln["ref"][:7], "pr": f"PR {ln['ref'] if ln['ref'].startswith('#') else '#' + ln['ref']}"}
            label = esc(ln.get("label") or default.get(ln["kind"], ln["ref"]))
            kind = {"commit": "commit", "pr": "PR", "doc": "doc", "url": "link"}[ln["kind"]]
            item = f'<a href="{esc(href)}">{label}</a>' if href else f"<code>{label}</code>"
            links.append(f'<span class="kind">{kind}</span> {item}')
        links_html = ("<ul class=\"links\">" + "".join(f"<li>{x}</li>" for x in links) + "</ul>") if links else ""
        record_html = ""
        if rec and rec["body"]:
            record_html = (f'<details class="record"><summary>Ler o registro de {esc(ph["id"])}</summary>'
                           f'<div class="record-body">{md_block(rec["body"])}</div></details>')
        notes = f'<p class="notes">{inline(ph["notes"])}</p>' if ph.get("notes") else ""
        cards.append(f"""
<article class="phase s-{st}{' is-current' if is_cur else ''}" id="{esc(slug(ph['id']))}">
  <header class="phase-head">
    <span class="badge">{esc(ph['id'])}</span>
    <div class="phase-name">
      {'<p class="eyebrow">Fase atual</p>' if is_cur else ''}
      <h3>{inline(ph['title'])}</h3>
      <p class="dates">{' · '.join(dates) or '&nbsp;'}</p>
    </div>
    <span class="pill p-{st}">{PHASE_STATUS[st]}</span>
  </header>
  <div class="phase-body">
    <p class="delivers"><span class="lbl">Entrega</span>{inline(ph['delivers'])}</p>
    <div class="acc"><span class="lbl">Critério de aceite</span><ul>{acc}</ul></div>
    {notes}{blocks}{links_html}{record_html}
  </div>
</article>""")

    def side_list(entries: list[str], empty: str) -> str:
        if not entries:
            return f'<p class="empty">{empty}</p>'
        return "<ul class=\"side-list\">" + "".join(entries) + "</ul>"

    tag = lambda pid: f' <a class="tag" href="#{esc(slug(pid))}">{esc(pid)}</a>' if pid else ""
    blk_html = side_list([
        f'<li class="flag-block"><strong>{esc(b["id"])}</strong>{tag(b.get("phase"))}<p>{inline(b["description"])}</p>'
        + (f'<p class="muted">{esc(b["owner"])}' + (f' · desde {fmt_date(b["since"])}' if b.get("since") else "") + "</p>"
           if b.get("owner") or b.get("since") else "") + "</li>"
        for b in open_blockers
    ], "Nenhum bloqueio aberto.")
    dec_html = side_list([
        f'<li><strong>{esc(d["id"])}</strong>{tag(d.get("phase"))}<p>{inline(d["question"])}</p>'
        + ("<ul class=\"opts\">" + "".join(f"<li>{inline(o)}</li>" for o in d["options"]) + "</ul>" if d.get("options") else "")
        + "</li>"
        for d in open_dec
    ], "Nenhuma decisão em aberto.")
    item_html = side_list([
        f'<li>{inline(it["text"])}{tag(it.get("phase"))}'
        + (f' <span class="muted">· {esc(it["owner"])}</span>' if it.get("owner") else "") + "</li>"
        for it in items
    ], "Nenhuma pendência.")
    decided = [d for d in decisions if d.get("status") == "decided"]
    decided_html = ""
    if decided:
        decided_html = ('<details class="decided"><summary>Decisões tomadas (' + str(len(decided)) + ")</summary><ul class=\"side-list\">"
                        + "".join(f'<li><strong>{esc(d["id"])}</strong>{tag(d.get("phase"))}<p>{inline(d["question"])}</p>'
                                  f'<p class="answer">{inline(d["decision"])}'
                                  + (f' <span class="muted">· {fmt_date(d["decided_on"])}</span>' if d.get("decided_on") else "")
                                  + "</p></li>" for d in decided)
                        + "</ul></details>")

    source = {
        "plan_id": plan["id"],
        "plan_file": g["rel"],
        "commit": commit,
        "plan_hash": content_hash(plan),
        "dirty": g["dirty"],
        "rendered_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    doc_link = ""
    if doc_rel:
        h = doc_href()
        doc_link = f'<a href="{esc(h)}">{esc(doc_rel)}</a>' if h else f"<code>{esc(doc_rel)}</code>"
    commit_txt = (f'<a href="{esc(web)}/commit/{esc(commit)}"><code>{esc(commit[:7])}</code></a>'
                  if web and commit else f"<code>{esc((commit or 'sem git')[:7])}</code>")
    dirty_banner = ('<p class="banner">Pré-visualização com mudanças ainda não commitadas. '
                    "Não é a versão do repositório.</p>") if g["dirty"] else ""
    next_action = plan.get("next_action")
    cur_html = (f'<a href="#{esc(slug(cur["id"]))}">{esc(cur["id"])} · {inline(cur["title"])}</a>'
                f' <span class="pill p-{cur["status"]}">{PHASE_STATUS[cur["status"]]}</span>') if cur else "Plano concluído"
    pct = round(100 * done / len(live)) if live else 100

    body = f"""
{dirty_banner}
<header class="masthead">
  <p class="eyebrow">Plano em fases</p>
  <h1>{inline(plan['title'])}</h1>
  <p class="meta">{doc_link}{' · ' if doc_link else ''}atualizado em {fmt_date(g['committed_at'] or source['rendered_at'])} · commit {commit_txt}</p>
</header>

<section class="now" aria-label="Situação">
  <div class="now-main">
    <p class="lbl">Agora</p>
    <p class="now-phase">{cur_html}</p>
    {f'<p class="next"><span class="lbl">Próxima ação</span>{inline(next_action)}</p>' if next_action else ''}
  </div>
  <dl class="stats">
    <div><dt>Concluídas</dt><dd>{done}<span>/{len(live)}</span></dd></div>
    <div class="{'warn' if open_blockers else ''}"><dt>Bloqueios</dt><dd>{len(open_blockers)}</dd></div>
    <div><dt>Decisões em aberto</dt><dd>{len(open_dec)}</dd></div>
  </dl>
  <div class="progress" role="img" aria-label="{done} de {len(live)} fases concluídas"><span style="width:{pct}%"></span></div>
</section>

<nav class="timeline-wrap" aria-label="Linha do tempo das fases">
  <ol class="timeline">
{timeline}
  </ol>
</nav>

<div class="layout">
  <section class="phases" aria-label="Fases">
    <h2 class="section-h">Fases</h2>
    {''.join(cards)}
  </section>
  <aside class="side">
    <section><h2 class="section-h">Bloqueios</h2>{blk_html}</section>
    <section><h2 class="section-h">Decisões em aberto</h2>{dec_html}{decided_html}</section>
    <section><h2 class="section-h">Pendências</h2>{item_html}</section>
  </aside>
</div>

<footer class="foot">
  <p>Gerado de <code>{esc(g['rel'])}</code> no commit {commit_txt}. Esta página só mostra o que está no repositório:
  para mudar um status, edite o plano, faça commit e republique.</p>
</footer>
"""
    tpl = TEMPLATE.read_text(encoding="utf-8")
    src_json = json.dumps(source, ensure_ascii=False).replace("</", "<\\/")
    return (tpl.replace("__TITLE__", esc(plan["title"]))
               .replace("__SOURCE_JSON__", src_json)
               .replace("__BODY__", body))


# ── resumo e comparação ─────────────────────────────────────────────────────

def summary(path: Path) -> str:
    plan = load(path)
    phases = plan["phases"]
    live = [p for p in phases if p["status"] != "dropped"]
    done = sum(1 for p in phases if p["status"] == "done")
    cur = current_phase(plan)
    lines = [f"{plan['title']} — {done}/{len(live)} fases concluídas"]
    lines.append("  " + " ".join(
        f"[{p['id']}✓]" if p["status"] == "done" else
        f"[{p['id']}▶]" if cur and p["id"] == cur["id"] else
        f"[{p['id']}✗]" if p["status"] == "dropped" else f"[{p['id']}]"
        for p in phases))
    if cur:
        since = f", desde {cur['started']}" if cur.get("started") else ""
        lines.append(f"Atual: {cur['id']} · {cur['title']} ({PHASE_STATUS[cur['status']].lower()}{since})")
    if plan.get("next_action"):
        lines.append(f"Próxima ação: {plan['next_action']}")
    for b in open_(plan.get("blockers")):
        lines.append(f"Bloqueio {b['id']}" + (f" [{b['phase']}]" if b.get("phase") else "") + f": {b['description']}")
    for d in open_(plan.get("decisions")):
        lines.append(f"Decisão em aberto {d['id']}" + (f" [{d['phase']}]" if d.get("phase") else "") + f": {d['question']}")
    url = (plan.get("artifact") or {}).get("url")
    lines.append(f"Quadro: {url}" if url else "Quadro: ainda não publicado")
    return "\n".join(lines)


def read_source(live_html: str) -> dict | None:
    m = re.search(r'<script type="application/json" id="plan-source">(.*?)</script>', live_html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1).replace("<\\/", "</"))
    except json.JSONDecodeError:
        return None


def compare(path: Path, live_path: Path) -> tuple[int, str]:
    plan = load(path)
    g = git_info(path, plan)
    src = read_source(live_path.read_text(encoding="utf-8"))
    if src is None:
        return 0, ("novo: a página publicada não tem carimbo de origem (primeira publicação ou página "
                   "de outra fonte). Publique a renderização local.")
    if src.get("plan_id") != plan["id"]:
        return 1, f"erro: a página publicada é do plano '{src.get('plan_id')}', não de '{plan['id']}'. Confira artifact.url."
    root, live_c, head = g["root"], src.get("commit"), g["commit"]
    if g["dirty"]:
        return 1, "erro: o plano local tem mudanças sem commit. Faça commit antes de comparar e publicar."
    if src.get("plan_hash") == content_hash(plan) and not src.get("dirty"):
        return 0, f"igual: a página já mostra este conteúdo (commit {(live_c or '')[:7]}). Republicar é opcional."
    if not (root and live_c and head):
        return 0, "à frente: sem git para comparar; publicando a renderização local."
    if git(root, "cat-file", "-e", f"{live_c}^{{commit}}") is None:
        return 3, (f"desconhecido: a página foi publicada do commit {live_c[:7]}, que não existe neste checkout. "
                   "Rode `git fetch`; se continuar desconhecido, quem publicou ainda não deu push — peça o push "
                   "antes de republicar, senão a mudança dele some da página.")
    if subprocess.run(["git", "merge-base", "--is-ancestor", live_c, head], cwd=root).returncode == 0:
        note = " (a publicada veio de um rascunho não commitado)" if src.get("dirty") else ""
        return 0, f"à frente: o local ({head[:7]}) contém o commit publicado ({live_c[:7]}){note}. Pode publicar."
    if subprocess.run(["git", "merge-base", "--is-ancestor", head, live_c], cwd=root).returncode == 0:
        return 2, (f"atrás: a página veio de {live_c[:7]}, mais novo que o local ({head[:7]}). "
                   "Rode `git pull`, renderize de novo e compare outra vez.")
    return 2, (f"divergente: local {head[:7]} e publicada {live_c[:7]} têm commits que o outro não tem. "
               "Rode `git pull` (resolva o conflito no plano, se houver), faça commit, renderize e compare de novo.")


def set_phase(path: Path, pid: str, status: str, when: str | None) -> str:
    plan = load(path)
    day = when or dt.date.today().isoformat()
    ph = next((p for p in plan["phases"] if p["id"] == pid), None)
    if ph is None:
        raise PlanError([f"fase '{pid}' não existe (ids: {', '.join(p['id'] for p in plan['phases'])})"])
    ph["status"] = status
    if status in ("in_progress", "done") and not ph.get("started"):
        ph["started"] = day
    if status == "done":
        ph["finished"] = ph.get("finished") or day
    if status in ("next", "pending"):
        ph.pop("finished", None)
        if status == "pending":
            ph.pop("started", None)
    validate(plan)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"{pid} → {PHASE_STATUS[status]}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="plan.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "summary"):
        sub.add_parser(name).add_argument("plan", type=Path)
    r = sub.add_parser("render")
    r.add_argument("plan", type=Path)
    r.add_argument("-o", "--out", type=Path, required=True)
    r.add_argument("--allow-dirty", action="store_true")
    c = sub.add_parser("compare")
    c.add_argument("plan", type=Path)
    c.add_argument("live", type=Path)
    s = sub.add_parser("phase")
    s.add_argument("plan", type=Path)
    s.add_argument("id")
    s.add_argument("--status", required=True, choices=list(PHASE_STATUS))
    s.add_argument("--date", help="AAAA-MM-DD (padrão: hoje)")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate":
            p = load(a.plan)
            print(f"ok: {a.plan} ({len(p['phases'])} fases)")
        elif a.cmd == "summary":
            print(summary(a.plan))
        elif a.cmd == "render":
            out = render(a.plan, a.allow_dirty)
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(out, encoding="utf-8")
            print(f"ok: {a.out}")
        elif a.cmd == "compare":
            code, msg = compare(a.plan, a.live)
            print(msg)
            return code
        elif a.cmd == "phase":
            print(set_phase(a.plan, a.id, a.status, a.date))
    except PlanError as e:
        print(f"plano inválido ({len(e.errors)} erro(s)):" if len(e.errors) > 1 else "erro:", file=sys.stderr)
        for err in e.errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
