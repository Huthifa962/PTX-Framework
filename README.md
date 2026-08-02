```
██████╗ ████████╗██╗  ██╗
██╔══██╗╚══██╔══╝╚██╗██╔╝
██████╔╝   ██║    ╚███╔╝
██╔═══╝    ██║    ██╔██╗
██║        ██║   ██╔╝ ██╗
╚═╝        ╚═╝   ╚═╝  ╚═╝
```

# PTX — Professional Pentesting Framework

An interactive terminal framework that unifies pentest **roadmaps, tool
documentation, cheat sheets, examples, search, and a tool launcher/installer**
into one msfconsole-style shell. PTX is a *reference and launcher* for standard,
publicly available security tooling — it organizes knowledge and drives tools
you already have installed; it does not ship exploits of its own.

> Use PTX only against systems you are explicitly authorized to test.

---

## Highlights

- **Four-level navigation** (msfconsole / Cisco-IOS style):
  `paths → roadmap phase → tools → tool`, with a context-aware prompt
  `ptx(Network Penetration Testing/Reconnaissance/nmap)>`.
- **24 domains, ~237 tools** spanning the full map — Core, Application,
  Infrastructure, Hardware, and Emerging (AI/LLM, cloud-native, CI/CD, blockchain,
  5G) — grouped in a dashboard and mapped onto the universal PTES spine.
- **100% data-driven.** No tool is hardcoded — everything loads from
  `database/**.yaml` + `database/*.json`, all produced by `build/generate.py`
  from a single taxonomy. Edit the taxonomy, regenerate, done.
- **`methodology` command** — prints the 8-phase PTES / kill-chain spine that
  underlies every path.
- **Rich, professional UI** — grouped domain dashboard, clean tables and panels,
  install status (`✔`/`✘`), `★` on the go-to tool per category, and per-tool
  authorized-scope notes. Red brand palette (green=installed, red=titles/missing).
- **Interactive shell** with persistent history and fuzzy auto-completion
  (prompt_toolkit), plus a plain fallback so PTX is scriptable/pipeable.
- **Launcher + installer** — `run` forwards args to the real binary safely
  (no shell string injection); `install`/`update` pick the right package
  manager (`apt`, `brew`, `snap`, `pip`, `pipx`, `go`, `cargo`, `git`).
- **Modular, typed, PEP 8** — every subsystem is one small module with a single
  responsibility, ready to extend toward the roadmap below.

---

## Requirements

- Python **3.13+**
- `rich`, `prompt_toolkit`, `PyYAML` (see `requirements.txt`)

## Install & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python ptx.py
```

## Commands

| Command | What it does |
|---|---|
| `help [cmd]` | List commands / show one command's help |
| `show paths [--flat]` | Grouped domain dashboard (or a flat table) |
| `show methodology` / `methodology` | Print the universal PTES / kill-chain spine |
| `show roadmap\|tools` | Display phases / tools for the current level |
| `use <index\|name>` | Descend into a path / phase / tool |
| `search <query>` | Fuzzy-search tools (name, keyword, description, alias) |
| `info` | Full data sheet for the current tool |
| `examples` / `cheatsheet` | Professional examples / quick reference |
| `workflow` | Roadmap diagram for the current path |
| `which` | Install path of the current tool |
| `run [args…]` | Launch the tool (e.g. `run -A 192.168.1.5` → `nmap -A 192.168.1.5`) |
| `install` / `update` | Install / update via the right package manager |
| `back` / `home` / `pwd` | Navigate up / to top / show location |
| `history [n]` · `banner` · `clear` · `exit` | Utilities |

Every command supports `-h` / `--help`. `use 0` and
`use "Network Penetration Testing"` both work, as do aliases (`use web`,
`use recon`).

## Project layout

```
PTX/
├── ptx.py                 # tiny entry point
├── core/                  # one module = one responsibility
│   ├── cli.py             # composition root (wires everything)
│   ├── shell.py           # prompt_toolkit REPL (+ plain fallback)
│   ├── parser.py          # tokenizing + per-command help
│   ├── navigator.py       # the 4-level state machine
│   ├── database.py        # data model + dynamic JSON/YAML loader
│   ├── renderer.py        # all Rich output
│   ├── commands.py        # command handlers / dispatcher
│   ├── search.py          # fuzzy search service
│   ├── installer.py       # package-manager aware install
│   ├── updater.py         # updates
│   ├── executor.py        # safe `run` of tool binaries
│   ├── workflow.py        # roadmap service
│   ├── history.py         # persistent history
│   ├── colors.py          # single-source color palette
│   ├── banner.py          # ASCII banner
│   ├── config.py          # paths & runtime config
│   └── utils.py           # slugify, which, fuzzy score, logging
├── build/                 # taxonomy + generator (build-time only)
│   ├── taxonomy.py        # DSL + the universal methodology spine
│   ├── d_*.py             # domain definitions, grouped by tier
│   └── generate.py        # writes the whole database/ from the taxonomy
├── database/
│   ├── paths.json         # the 24 testing domains (name, group, description)
│   ├── workflows.json     # per-domain roadmaps (phases)
│   ├── methodology.json   # the universal PTES / kill-chain spine
│   ├── aliases.json       # navigation shortcuts
│   └── <domain>/*.yaml    # generated tool definitions, one file per tool
├── templates/tool_schema.yaml
└── assets/ docs/ logs/ cache/ config/
```

## Rebuilding the database

The database is generated. To change domains, phases, or tools, edit the
taxonomy under `build/` and regenerate:

```bash
cd build && python generate.py     # rewrites paths/workflows/methodology + all YAMLs
```

Each domain folder is cleared and rewritten, so the build is idempotent.

## Adding a single tool (no rebuild needed)

1. Copy `templates/tool_schema.yaml` into the right `database/<domain>/` folder.
2. Fill in at least `name`, `binary`, `package`, `description`, and `phases`
   (phase names must match `workflows.json` for that domain). Optional
   `recommended: true` adds the `★`; `note:` adds an authorized-scope banner.
3. Relaunch PTX — it auto-discovers every `*.yaml` in each domain folder.

Adding a whole **domain** = a new entry in the `build/` taxonomy, then regenerate.

## Design notes

- **Safety by construction.** `run`/`install` execute an argument *list* with
  `shell=False`; command strings come from each tool's own YAML, never from
  concatenation. Installs always confirm `[Y/n]` first.
- **Testable core.** Navigator and parser are pure state/logic with no I/O;
  handlers talk to injected services, so each layer can be unit-tested alone.

## Roadmap (architecture is already prepared for these)

Bookmarks · Favorites · Notes · Report export (MD/JSON) · Plugins ·
Custom tool packs · Nmap XML parsing · Metasploit/Burp/BloodHound integration ·
Workspaces · Session saving · Config profiles · Remote SSH execution.

## License

MIT — see `LICENSE`.
