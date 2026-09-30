#!/usr/bin/env python3
"""
GraphGuard codebase discovery tool.

Read-only. Produces a structural map of an existing GraphGuard repo so the
administrative/operational layer can be implemented as an extension rather
than a rewrite.

Usage:
    python3 _gg_agent/inspect_codebase.py [ROOT] [-o REPORT.md] [-j REPORT.json]

ROOT defaults to /home/user.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "dist", "build", "out", "target", ".next",
    ".nuxt", ".turbo", ".parcel-cache", "coverage", ".idea", ".vscode",
    ".egg-info", ".ipynb_checkpoints", "site-packages",
}

SKIP_FILE_SUFFIXES = {".min.js", ".map", ".lock", ".png", ".jpg", ".jpeg", ".gif",
                      ".svg", ".ico", ".woff", ".woff2", ".ttf", ".pdf", ".pyc",
                      ".parquet", ".csv", ".pkl", ".pt", ".pth", ".onnx", ".bin"}

# Module names that indicate which part of the pipeline a file belongs to.
AI_MARKERS = {
    "graphsage": ("torch_geometric", "SAGEConv", "GraphSAGE", "sage"),
    "xgboost": ("xgboost", "XGBClassifier", "XGBModel", "xgb."),
    "ews_rules": ("ews", "early_warning", "rule_engine", "EWSRule"),
    "networkx_graph": ("networkx", "nx.Graph", "nx.DiGraph", "nx.MultiDiGraph"),
    "risk_fusion": ("fusion", "risk_fusion", "multi_signal", "weighted_score",
                    "def fuse", "fuse(", "ensemble", "combine_score"),
    "feature_engineering": ("feature", "featurize", "feature_engineering"),
}

ADMIN_MARKERS = {
    "auth": ("jwt", "oauth2", "password", "bcrypt", "passlib", "authenticate", "current_user"),
    "alerts": ("alert",),
    "rfa": ("rfa", "red_flag", "redflag"),
    "cases": ("case",),
    "evidence": ("evidence", "sha256", "checksum"),
    "fraud_dna": ("fraud_dna", "dna", "pattern_signature"),
    "simulation": ("simulation", "red_team", "redteam", "digital_twin", "adversarial"),
    "audit": ("audit",),
    "reporting": ("report", "export", "pdf", "csv"),
    "config": ("config", "settings", "threshold"),
    "notifications": ("notification", "websocket", "sse", "EventSource"),
}

FRONTEND_ROUTE_RE = re.compile(
    r"""<Route[^>]*?(?:path\s*=\s*["'`]([^"'`]+)["'`])""", re.IGNORECASE
)
ROUTER_OBJ_RE = re.compile(
    r"""(?:path\s*:\s*|path\s*=\s*)["'`]([^"'`]+)["'`]""", re.IGNORECASE
)
API_CALL_RE = re.compile(
    r"""(?:fetch|axios|api|apiClient|client|request|http|instance)\s*(?:\.\s*(?:get|post|put|patch|delete)\s*)?\(?\s*["'`]([^"'`]*/(?:api|v1|v2)[^"'`]*)["'`]""",
    re.IGNORECASE,
)
# anyClient.get("/api/...") or anyClient.post(`/api/${id}`)
API_METHOD_RE = re.compile(
    r"""[A-Za-z_$][\w$]*\s*\.\s*(?:get|post|put|patch|delete)\s*\(\s*["'`](/api[^"'`]*)["'`]""",
    re.IGNORECASE,
)
API_TEMPLATE_RE = re.compile(r"""["'`](/(?:api|v1|v2)[A-Za-z0-9_\-/{}$.]*)["'`]""")
BACKEND_DECORATOR_RE = re.compile(
    r"""@(?:\w+)\.(get|post|put|patch|delete|websocket|api_route)\(\s*["']([^"']+)["']"""
)
SQLALCHEMY_BASE_HINTS = {"Base", "DeclarativeBase", "Model", "db.Model", "BaseModel"}


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for name in filenames:
            p = Path(dirpath) / name
            if any(name.endswith(s) for s in SKIP_FILE_SUFFIXES):
                continue
            if p.stat().st_size > 2_000_000:
                continue
            yield p


def rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# --------------------------------------------------------------------------
# Python analysis
# --------------------------------------------------------------------------

def analyze_python(path: Path, root: Path, report: dict) -> None:
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    relp = rel(path, root)

    if not src.strip():
        return

    low = src.lower()

    # --- AI / admin module classification (cheap text scan) ---
    for label, markers in AI_MARKERS.items():
        if any(m.lower() in low for m in markers):
            report["ai_modules"].setdefault(label, [])
            if relp not in report["ai_modules"][label]:
                report["ai_modules"][label].append(relp)

    for label, markers in ADMIN_MARKERS.items():
        if any(m.lower() in low for m in markers):
            report["admin_modules"].setdefault(label, [])
            if relp not in report["admin_modules"][label]:
                report["admin_modules"][label].append(relp)

    # --- Endpoints (text scan: works even if AST fails) ---
    for method, route in BACKEND_DECORATOR_RE.findall(src):
        report["endpoints"].append({
            "method": method.upper(),
            "path": route,
            "file": relp,
        })

    # --- AST pass: models, schemas, app objects ---
    try:
        tree = ast.parse(src)
    except SyntaxError:
        report["parse_errors"].append(relp)
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(b.attr)
            elif isinstance(b, ast.Subscript):
                bases.append(ast.unparse(b))
        base_str = ", ".join(bases)

        is_table = False
        cols = []
        tablename = None
        relationships = []
        for stmt in node.body:
            # __tablename__ = "x"
            if isinstance(stmt, ast.Assign):
                for t in stmt.targets:
                    if isinstance(t, ast.Name) and t.id == "__tablename__":
                        try:
                            tablename = ast.literal_eval(stmt.value)
                        except Exception:
                            tablename = ast.unparse(stmt.value)
            # column = Column(...)
            if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                fname = None
                if isinstance(stmt.value.func, ast.Name):
                    fname = stmt.value.func.id
                elif isinstance(stmt.value.func, ast.Attribute):
                    fname = stmt.value.func.attr
                if fname in {"Column", "mapped_column", "column", "relationship",
                              "ForeignKey"}:
                    for t in stmt.targets:
                        if isinstance(t, ast.Name):
                            if fname == "relationship":
                                relationships.append(t.id)
                            else:
                                cols.append(t.id)
                                is_table = True
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                ann = ast.unparse(stmt.annotation) if stmt.annotation else ""
                val = ast.unparse(stmt.value) if stmt.value else ""
                if "Mapped[" in ann or "mapped_column" in val or "Column(" in val:
                    cols.append(stmt.target.id)
                    is_table = True
                elif "relationship" in val:
                    relationships.append(stmt.target.id)

        is_orm = is_table or tablename is not None or (
            any(b in SQLALCHEMY_BASE_HINTS for b in bases) and bool(cols)
        )
        if is_orm:
            report["orm_models"].append({
                "name": node.name,
                "table": tablename,
                "file": relp,
                "bases": base_str,
                "columns": cols,
                "relationships": relationships,
            })

        # Pydantic models
        if any(b in {"BaseModel", "SQLModel", "Schema"} for b in bases):
            fields = []
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    fields.append(stmt.target.id)
            report["pydantic_models"].append({
                "name": node.name,
                "file": relp,
                "bases": base_str,
                "fields": fields,
            })

    # module-level assignments worth knowing (app = FastAPI(), engine, Base, ...)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in {
                    "app", "engine", "Base", "SessionLocal", "settings",
                    "router", "DATABASE_URL", "SECRET_KEY", "ALGORITHM",
                }:
                    report["app_wiring"].append({
                        "name": t.id,
                        "value": ast.unparse(node.value)[:200],
                        "file": relp,
                    })
        if isinstance(node, ast.ClassDef) and node.name in {"Settings", "Config"}:
            fields = [
                s.target.id for s in node.body
                if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
            ]
            report["settings_classes"].append({"name": node.name, "file": relp, "fields": fields})


# --------------------------------------------------------------------------
# Frontend analysis
# --------------------------------------------------------------------------

def analyze_frontend(path: Path, root: Path, report: dict) -> None:
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    relp = rel(path, root)

    # Routes declared as JSX <Route path="...">
    for m in FRONTEND_ROUTE_RE.finditer(src):
        report["frontend_routes"].append({"path": m.group(1), "file": relp})
    # Routes declared in router config objects (path: '...' next to element)
    if "element:" in src or "Component:" in src:
        for m in ROUTER_OBJ_RE.finditer(src):
            val = m.group(1)
            if val.startswith("/") and " " not in val:
                report["frontend_routes"].append({"path": val, "file": relp})

    # API calls the UI already makes -> backend contract we must not break
    seen = set()
    for m in API_CALL_RE.finditer(src):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            report["frontend_api_calls"].append({"url": url, "file": relp})
    for m in API_METHOD_RE.finditer(src):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            report["frontend_api_calls"].append({"url": url, "file": relp})
    for m in API_TEMPLATE_RE.finditer(src):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            report["frontend_api_calls"].append({"url": url, "file": relp})

    # component inventory
    name = path.stem
    report["frontend_components"].append({"name": name, "file": relp})


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def build_markdown(report: dict) -> str:
    L = []
    A = L.append
    A("# GraphGuard — Codebase Map (auto-generated, read-only)\n")
    A(f"_Generated: {datetime.now(timezone.utc).isoformat()} | Root: `{report['root']}`_\n")

    A("\n## 1. Repository layout (top level)\n")
    if report["tree"]:
        A("```")
        for line in report["tree"]:
            A(line)
        A("```\n")
    else:
        A("_No project files detected yet._\n")

    A("\n## 2. Stack signals\n")
    if report["stack"]:
        for k, v in sorted(report["stack"].items()):
            A(f"- **{k}**: {', '.join(sorted(v))}")
    else:
        A("_None detected._")
    A("")

    A("\n## 3. Existing ORM models / database schema\n")
    if report["orm_models"]:
        A("| Model | Table | File | #Cols | Relationships |")
        A("|---|---|---|---|---|")
        for m in sorted(report["orm_models"], key=lambda x: x["name"].lower()):
            A(f"| `{m['name']}` | `{m['table'] or '—'}` | `{m['file']}` | "
              f"{len(m['columns'])} | {', '.join(m['relationships']) or '—'} |")
    else:
        A("_No ORM models detected._")
    A("")

    A("\n## 4. Migrations\n")
    if report["migrations"]:
        A("```")
        for m in report["migrations"][:40]:
            A(m)
        if len(report["migrations"]) > 40:
            A(f"... (+{len(report['migrations']) - 40} more)")
        A("```\n")
    else:
        A("_No Alembic/migration directory detected._\n")

    A("\n## 5. Existing backend endpoints\n")
    if report["endpoints"]:
        by_file = defaultdict(list)
        for e in report["endpoints"]:
            by_file[e["file"]].append(f"{e['method']} {e['path']}")
        A(f"**Total: {len(report['endpoints'])}**\n")
        for f, eps in sorted(by_file.items()):
            A(f"- `{f}`")
            for ep in sorted(set(eps)):
                A(f"  - `{ep}`")
    else:
        A("_None detected._")
    A("")

    A("\n## 6. AI / research layer\n")
    if report["ai_modules"]:
        for k, files in sorted(report["ai_modules"].items()):
            A(f"- **{k}** → {', '.join('`' + f + '`' for f in sorted(files)[:8])}"
              + (f" (+{len(files) - 8} more)" if len(files) > 8 else ""))
    else:
        A("_No AI pipeline markers detected._")
    A("")

    A("\n## 7. Administrative / operational surface already present\n")
    if report["admin_modules"]:
        for k, files in sorted(report["admin_modules"].items()):
            A(f"- **{k}** → {', '.join('`' + f + '`' for f in sorted(files)[:6])}"
              + (f" (+{len(files) - 6} more)" if len(files) > 6 else ""))
    else:
        A("_None detected — this is the layer to add._")
    A("")

    A("\n## 8. Frontend routes (DO NOT break / redesign)\n")
    if report["frontend_routes"]:
        for r in sorted({(x["path"], x["file"]) for x in report["frontend_routes"]}):
            A(f"- `{r[0]}` → `{r[1]}`")
    else:
        A("_None detected._")
    A("")

    A("\n## 9. Frontend → backend contract in use\n")
    if report["frontend_api_calls"]:
        for c in sorted({(x["url"], x["file"]) for x in report["frontend_api_calls"]})[:60]:
            A(f"- `{c[0]}` → `{c[1]}`")
    else:
        A("_None detected._")
    A("")

    A("\n## 10. App wiring / config\n")
    if report["app_wiring"]:
        for w in report["app_wiring"]:
            A(f"- `{w['name']}` = `{w['value']}` — `{w['file']}`")
    else:
        A("_None detected._")
    A("")

    A("\n## 11. Entry points & dependency manifests\n")
    for f in report["manifests"]:
        A(f"- `{f}`")
    A("")

    if report["parse_errors"]:
        A("\n## 12. Files that failed to parse\n")
        for f in report["parse_errors"]:
            A(f"- `{f}`")
        A("")

    A("\n---\n")
    A("## Integration checklist (what still needs human/agent confirmation)\n")
    A("1. Auth mechanism currently present (none / JWT / session / API key)")
    A("2. DB engine + whether Alembic is initialized")
    A("3. Where the risk score is persisted (table/column)")
    A("4. Whether Alert/Account/Transaction models already exist and their PKs")
    A("5. How the frontend talks to the backend (base URL, axios instance, /api prefix)")
    A("6. Notification mechanism in the UI (polling / WS / SSE / toast only)")
    A("7. Test framework in use (pytest / vitest / jest)")
    A("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Map an existing GraphGuard codebase.")
    ap.add_argument("root", nargs="?", default="/home/user", help="Project root to scan")
    ap.add_argument("-o", "--out", default="/home/user/_gg_agent/CODEBASE_MAP.md")
    ap.add_argument("-j", "--json", default="/home/user/_gg_agent/CODEBASE_MAP.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Root {root} does not exist", file=sys.stderr)
        return 1

    report = {
        "root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tree": [],
        "stack": defaultdict(set),
        "orm_models": [],
        "pydantic_models": [],
        "endpoints": [],
        "ai_modules": {},
        "admin_modules": {},
        "frontend_routes": [],
        "frontend_api_calls": [],
        "frontend_components": [],
        "app_wiring": [],
        "settings_classes": [],
        "migrations": [],
        "manifests": [],
        "parse_errors": [],
    }

    # top-level tree (2 levels)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > 2:
            dirnames[:] = []
            continue
        indent = "  " * depth
        report["tree"].append(f"{indent}{Path(dirpath).name}/")
        if depth < 2:
            for n in sorted(filenames)[:25]:
                if not any(n.endswith(s) for s in SKIP_FILE_SUFFIXES):
                    report["tree"].append(f"{indent}  {n}")

    for p in iter_files(root):
        relp = rel(p, root)
        name = p.name.lower()
        if name in {"requirements.txt", "pyproject.toml", "setup.py", "pipfile",
                    "package.json", "alembic.ini", "docker-compose.yml",
                    "docker-compose.yaml", "dockerfile", "makefile", ".env.example",
                    "environment.yml", "poetry.lock"}:
            report["manifests"].append(relp)
        parts = relp.split("/")
        if "alembic" in parts and ("version" in parts or "versions" in parts):
            report["migrations"].append(relp)
        if "migration" in relp and p.suffix in {".py", ".sql"}:
            report["migrations"].append(relp)

        if p.suffix == ".py":
            analyze_python(p, root, report)
        elif p.suffix in {".ts", ".tsx", ".js", ".jsx", ".vue", ".svelte"}:
            analyze_frontend(p, root, report)

    # stack detection from manifests
    for mf in report["manifests"]:
        full = root / mf
        try:
            txt = full.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        for tool in ["fastapi", "flask", "django", "sqlalchemy", "alembic", "pydantic",
                     "torch", "torch_geometric", "xgboost", "networkx", "sklearn",
                     "scikit-learn", "celery", "redis", "pytest", "jwt", "passlib",
                     "bcrypt", "pandas", "numpy", "reportlab", "websockets"]:
            if tool in txt:
                report["stack"]["python"].add(tool)
        for tool in ["react", "next", "vue", "svelte", "vite", "typescript",
                     "tailwindcss", "axios", "react-router", "recharts", "d3",
                     "framer-motion", "zustand", "redux", "tanstack", "vitest", "jest",
                     "shadcn"]:
            if tool in txt:
                report["stack"]["frontend"].add(tool)
        if "package.json" in mf:
            try:
                pkg = json.loads(txt)
                for dep in list(pkg.get("dependencies", {})) + list(pkg.get("devDependencies", {})):
                    report["stack"]["frontend"].add(dep)
            except Exception:
                pass

    # normalize defaultdicts
    report["stack"] = {k: sorted(v) for k, v in report["stack"].items()}
    report["migrations"] = sorted(set(report["migrations"]))
    report["manifests"] = sorted(set(report["manifests"]))

    md = build_markdown(report)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md, encoding="utf-8")

    json_report = {k: (dict(v) if isinstance(v, defaultdict) else v)
                   for k, v in report.items()}
    Path(args.json).write_text(json.dumps(json_report, indent=2, default=str),
                               encoding="utf-8")

    print(md)
    print(f"\n[written] {args.out}")
    print(f"[written] {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
