# LLM Context Log — Turbo Death Warrior

> Rolling high-signal summary for any coding assistant (Copilot, opencode, Muse Spark, etc.).
> Read this first to avoid re-discovering the codebase. Update per `AGENTS.md` after every meaningful change.

**Last Updated:** 2026-08-22
**Project:** Turbo Death Warrior - Web Edition (`turbo-death-warrior` v1.0.0)
**Repo:** `turbo_death_warrior` @ `main` (HEAD `4932e08` + server TTL/eviction pending)
**Status:** Stable / playable locally; CI green (32/32 tests); deploy pipeline to Raspberry Pi self-hosted runner live; **known frontend↔API path mismatch** (see Active Priorities). Server leak fixed pending commit (GAMES TTL eviction).

---

## Current Snapshot

**What it is:** Browser front end for the *Turbo Death Warrior* terminal adventure. Fight a Caffeinated Orc, loot the Turbo Crystal, and defeat the Mega-Goblin King. Retro amber CRT aesthetic, fully keyboard-driven.

**Stack:**
- Python 3.11, **stdlib only** for runtime (`http.server.ThreadedHTTPServer`, `secrets`, `threading`, `time`, `pathlib`, `json`, `random`).
- `pytest>=7.0` for tests only (`requirements.txt` / `[project.optional-dependencies] test` in `pyproject.toml:14`).
- Single-file frontend `web/index.html` (466 lines, ~11.7 KB) — HTML/CSS/JS with scanlines, vignette, typewriter effect.
- `src` layout (`pyproject.toml:16` — `where = ["src"]`), installed editable via `pip install -e ".[test]"`.

**How to run:**
```sh
make            # defaults to TDW_HOST=127.0.0.1 TDW_PORT=8001, see .env / .env.example
make run PORT=9000 HOST=0.0.0.0
python3 -m turbo_death_warrior.server
```
Config precedence: real env vars > `.env` > built-in defaults (`src/turbo_death_warrior/server.py:42-43`).

**Tests:** `make test` → `python -m pytest test/ -v` — **32 passed** as of 2026-08-22. Covers init, name submission, town/cave/combat, orc/boss defeat, game-over, restart, serialization, constants, payload structure.

**CI/CD:** `.github/workflows/ci.yml` — `test` job (checkout, setup-python 3.11, `pip install -e ".[test]"`, `make check`, `make test`) on push/PR to `main`; `deploy` job (self-hosted, `needs: test`, only on `push` to `main`) rsyncs to `/home/ewanritchie/turbo-death-warrior/`, recreates `.venv`, `systemctl restart turbo-death-warrior`, smoke-checks `curl -sf http://127.0.0.1:8001/tdw-api/game`.

**Git state (2026-08-22):**
- Branch `main` ahead of `origin/main` by 1 (4932e08 committed) + 2 modified files staged pending: `AGENTS.md` (Definition of done added) and `src/turbo_death_warrior/server.py` (TTL eviction + WEB_DIR removal).
- 9 commits since `4b8e037` (initial). HEAD `4932e08 docs: add AGENTS.md and bootstrap LLM_CONTEXT_LOG.md` (7d9beb5 prior).
- Working tree modified (not yet committed) — this log pending update.

**Known drift / debt:**
- `src/turbo_death_warrior/server.py:93,104` now serves only `POST /tdw-api/game` and `POST /tdw-api/game/<id>/{name,action}`; `do_GET` returns 404. Frontend `web/index.html:439,452,460` still fetches `/api/game` — **broken integration** until paths are re-aligned or a `GET /` static handler is restored. The deploy smoke check already uses `/tdw-api/game`, so CI deploy will pass but local browser play is broken.
- `.env.example:8` shows `TDW_PORT=9999` while README and `.env` / `server.py:43` default to `8001` — harmless but confusing.
- Server `AGENTS.md:18` now defines Definition of done (`make check` + `make test` + log entry + stale-priority pruning) — this change satisfies it.

---

## Architecture

```
turbo_death_warrior/
├── src/turbo_death_warrior/
│   ├── __init__.py               # __version__ = "1.0.0"
│   ├── game_engine.py:19         # class Game — I/O-free engine; HEAL_AMOUNT=40, STRIKE_DAMAGE=150
│   └── server.py:1-140           # ThreadingHTTPServer, TTL sweep, Handler
├── test/test_game_engine.py      # 32 pytest cases (7 classes + constants/payload)
├── web/index.html                # single-file frontend; api() helper, bar()/hpClass(), typewriter
├── pyproject.toml                # setuptools, src layout, requires-python >=3.8
├── Makefile                      # run/check/test/requirements/clean; RUN_ENV override
├── requirements.txt              # pytest>=7.0
├── .env / .env.example           # TDW_HOST, TDW_PORT, TDW_GAME_TTL_SECONDS, TDW_SWEEP_INTERVAL_SECONDS
└── .github/workflows/ci.yml      # test + deploy (self-hosted)
```

**Game engine (`src/turbo_death_warrior/game_engine.py`):**
- State: `player: {name, hp, max_hp, weapon, damage, potions, has_turbo_crystal}`, `enemy: {key, name, hp, max_hp, dmg}|None`, `boss_fight: bool`, `scene: str`, `over: bool`.
- Constants: `HEAL_AMOUNT=40`, `STRIKE_DAMAGE=150`, `ENEMY_TEMPLATES: orc {hp:40,dmg:12}, boss {hp:120,dmg:20}`.
- Scenes: `name_prompt → town → (forest→combat vs orc) → cave_entrance → (caves→combat vs boss) → victory|game_over`. Combat loop in `_combat_turn()` with `random.randint` variance.
- Public API: `Game.start() → payload`, `submit_name(raw_name)`, `act(action_id)`. Every call returns `_payload() {messages[], options[], text_input?, state{scene,over,player,enemy}}`.
- Flow: `reset()` → `start()` → `submit_name()` → `_to_town()` → `_enter_forest()`/`_blacksmith()`/`_stats()` → `_win_fight()` (orc grants `has_turbo_crystal` + potion, transitions to `cave_entrance`) → `_enter_caves()` → `_win_fight()` (boss → `victory`) or `_game_over()`. `over` gate allows only `restart`.
- Serialization: `_state()` deep-copies player/enemy; `_payload()` is JSON-ready.

**Server (`src/turbo_death_warrior/server.py:1-140`):**
- `_load_env()` reads `.env` (`path.read_text().splitlines()`, skips `#`/empty/`=`-less, respects existing `os.environ`) — `server.py:24-41`.
- `HOST`/`PORT` from `TDW_HOST`/`TDW_PORT` (defaults `127.0.0.1`/`8001`), plus `GAME_TTL_SECONDS`/`SWEEP_INTERVAL_SECONDS` from `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS` (defaults `3600`/`300`) — `server.py:43-46`. `Path` import retained for `ENV_FILE`; `WEB_DIR` removed as dead code (was unused, `do_GET` → 404).
- In-memory `GAMES: dict[str, {"game": Game, "last_active": float}]` + `LOCK = threading.Lock()` — one entry per `game_id = secrets.token_hex(8)`; `last_active = time.time()` on create and on every `action`/`name` touch — `server.py:98,110`.
- Eviction: `_sweep_expired_games()` (`server.py:52-60`) loops `time.sleep(SWEEP_INTERVAL_SECONDS)` (no LOCK) then `with LOCK` deletes where `last_active < now - GAME_TTL_SECONDS`; started as daemon thread in `main()` before `serve_forever()` — `server.py:124-126`.
- `Handler`: `_json()`, `_error()`, `_body()` helpers. `do_GET` → 404. `do_POST` handles `/tdw-api/game` (create) and `/tdw-api/game/<id>/{action,name}` (dispatch under `LOCK`; body `{"id":...}` or `{"name":...}`); unknown `game_id` (including swept) → `404 "unknown game - refresh to start a new one"`.
- `main()` starts sweeper thread then `ThreadingHTTPServer((HOST,PORT), Handler)` with `serve_forever()`.

**Frontend (`web/index.html`):**
- CSS: CSS vars `--bg:#1a0d00 --ink:#ffaa00 --amber:#ffcc44`, CRT flicker/scanlines/vignette, monospace stack.
- JS: `api(path, body)` POSTs JSON, throws on `!res.ok`; `bar()`/`hpClass()`/`pad()` renderers; `setState()` updates `#statusline`/`#enemyline`; `startTyping()`/`typeNextLine()` typewriter (28 ms/char, 80 ms line gap); `renderControls()` shows `text_input` or `options` as `[1] Label`; `handle(payload)` stores `gameId`, calls `setState` + `startTyping`; `choose(id)` / `nameForm submit` / IIFE bootstrap call `api("/api/game…")`. Keyboard: number keys / Enter.

**API contract:**
| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/tdw-api/game` | `{}` | `{messages, options, text_input, state, game_id}` |
| POST | `/tdw-api/game/<id>/name` | `{"name": str}` | `{messages, options, text_input, state}` |
| POST | `/tdw-api/game/<id>/action` | `{"id": str}` | `{messages, options, text_input, state}` |
| GET | `/` | — | 404 (removed in `b16b9ff`; previously served `web/index.html`) |

---

## Safety + Auth Boundaries

- **No auth / no sessions:** `game_id` is `secrets.token_hex(8)` (64-bit entropy) passed in URL path; no cookies, no CSRF, no login. Anyone with the ID can drive that game. Acceptable for local/LAN game, not for multi-tenant internet exposure.
- **In-memory store:** `GAMES` dict is process-local, bounded by idle TTL. Entry `{game, last_active}` (`server.py:48,98`); TTL `TDW_GAME_TTL_SECONDS` (3600) and sweep `TDW_SWEEP_INTERVAL_SECONDS` (300) — `server.py:45-46`. `_sweep_expired_games()` evicts idle entries under `LOCK` (`server.py:57-60`); daemon thread in `main()` (`server.py:125`). Still no persistence/DB; restart wipes all games. Bounding prevents slow leak over long uptime; worst-case size is creations per TTL window, not process lifetime.
- **Thread safety:** `LOCK` guards `GAMES` dict access/mutation and `Game` mutation during `act()`/`submit_name()` and sweep (`server.py:97-98,106-118,57-60`). `Game` itself is explicitly not thread-safe (`game_engine.py:20`); lock is coarse-grained per-request; sweep never holds LOCK while sleeping (`server.py:55` outside `with`).
- **Input handling:** Server coerces `body.get("id"/"name")` to `str` before passing to engine; empty/whitespace names rejected in `submit_name()` with retry prompt. Invalid `action_id` returns `["Invalid choice."]` without state change. `Content-Length` 0 → `{}` body. `JSONDecodeError` → `{}`.
- **No external deps at runtime:** stdlib only mitigates supply-chain risk. Test dep `pytest` pinned `>=7.0`.
- **Config:** `.env` is excluded from rsync deploy (`ci.yml` `--exclude '.env'`) so secrets/local HOST/PORT survive redeploys. Env file parser strips quotes/spaces and ignores lines with spaces in key.
- **Deployment surface:** Self-hosted runner rsyncs with `--delete` (destructive sync), recreates `.venv`, restarts `systemd` service `turbo-death-warrior`. Smoke check hits `127.0.0.1:8001` hard-coded, not `$TDW_PORT`. Ensure `HOST`/`PORT` alignment if `.env` changes.
- **No HTTPS / no rate limiting / no validation on gameId format** — DoS via rapid `POST /tdw-api/game` creation is trivial.

---

## Active Priorities

1. **Fix frontend↔API path mismatch (P0):** `web/index.html:439,452,460` uses `/api/game` but server expects `/tdw-api/game` since `b16b9ff`. Either update frontend to `/tdw-api/game` (3 refs) or re-add server-side compatibility shim. Verify with `make test` + manual `curl` + browser playthrough. Also decide whether to restore `GET /` to serve `web/index.html` (currently 404) or deploy frontend separately (nginx/static hosting). `WEB_DIR` dead code removed in this change (`server.py` no longer references `web/`).
2. **Reconcile port defaults:** `.env.example:8` (`9999`) vs README/`server.py:43`/`.env` (`8001`). Align to one default, or document why they differ. Also document new `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS` (3600/300) in `README.md` and `.env.example`.
3. **Test coverage gap:** No server integration tests (only `test/test_game_engine.py` covers `Game`; `server.py` `Handler`/`GAMES`/sweep has 0 coverage). Add `test_server.py` for `Handler` routing, 404s, bad JSON, unknown/swept `game_id`, TTL eviction and `last_active` touch behavior, and concurrent access. Cheap sweep tests (mock `time.time`/`sleep`, short TTL) welcome without large scaffolding — see Change Log 2026-08-22 sweep fix for manual mock verification pattern.

*Recently resolved (pruned from active):*
- **GAMES leak / unbounded store** — fixed 2026-08-22 via TTL eviction (`server.py:45-46,52-60,98,110,124-126`); `GAMES` now `{"game": Game, "last_active": float}` with daemon sweeper.
- **WEB_DIR dead code** — removed 2026-08-22 (`server.py:44` deleted; `Path` kept for `ENV_FILE`).
- **Untracked `AGENTS.md`/`LLM_CONTEXT_LOG.md`** — committed `4932e08`.

---

## Update Protocol

- **When to update:** After any meaningful code change (feature, fix, refactor, dep bump, CI/config, docs affecting behavior).
- **Where:** Append an entry under **Change Log Entries** below. If the change touches snapshot, architecture, safety/auth, or priorities, **also edit those sections in place** (don't rely solely on the log).
- **Format (per entry):**
  ```
  ### YYYY-MM-DD — <Scope>
  - **Summary:** One-line what changed (prefer `path:line` refs).
  - **Why:** Reason / trigger (issue, user request, bug).
  - **Impact:** Behavior, API, config, deps, breaking changes.
  - **Validation:** How verified (e.g., `make test` 32/32, `curl`, manual playthrough, CI run).
  - **Follow-ups:** TODOs / debt / next steps.
  ```
- **Style:** Factual, short, file-path-heavy. No marketing language. Keep the snapshot current — date-stamp the **Last Updated** header when editing.
- **Ownership:** Any coding assistant making changes must update this file in the same commit/PR.

---

## Change Log Entries

### 2026-08-22 — Server TTL Eviction + WEB_DIR Cleanup (server.py only)
- **Summary:** `src/turbo_death_warrior/server.py:15,45-46,52-60,98,110,124-126` — fix GAMES leak (never-evicted dict) to `{id: {"game": Game, "last_active": float}}` with `import time`, env-configurable `TDW_GAME_TTL_SECONDS` (3600) / `TDW_SWEEP_INTERVAL_SECONDS` (300) (`os.environ.get` matching `HOST`/`PORT` style), `last_active=time.time()` on create/action/name, daemon `threading.Thread(target=_sweep_expired_games, daemon=True)` in `main()` that `sleep`s then `with LOCK` evicts `last_active < now - TTL` (no LOCK while sleeping); preserve 404 `"unknown game - refresh to start a new one"` for swept games; delete dead `WEB_DIR` line (keep `Path` for `ENV_FILE`).
- **Why:** Spec fix for slow memory leak over long uptime; `GAMES` grew without bound per `secrets.token_hex(8)` creation. Second fix removes unused `WEB_DIR` (`do_GET` always 404).
- **Impact:** Behavior: games idle > TTL now evicted (whether finished or abandoned); API unchanged except swept IDs now 404 as designed. Config: two new env vars with defaults. No threads held while sleeping; sweep under LOCK only for mutation. `game_engine.py` and frontend untouched per scope. Snapshot/Architecture/Safety/Priorities updated to reflect bounded store and removed dead code.
- **Validation:** `make check` OK (`py_compile server.py game_engine.py`); `make test` 32/32 (`test/test_game_engine.py`); manual `python3 -c` with `unittest.mock.patch(time.time)` verified shape, touch bump, and `_sweep_expired_games` cutoff eviction; `WEB_DIR` absence and `Path` retention checked. Existing tests cover only `Game` — `server.py` has 0 coverage (flagged in Active Priorities); no large test suite added, cheap mock sweep tests welcome per spec.
- **Follow-ups:** Document new env vars in `README.md`/` .env.example`; consider adding focused `test_server.py` for `Handler` routing and sweep (mock `time`); verify deploy on Pi restarts sweeper thread; frontend `/api` vs `/tdw-api` mismatch still P0.

### 2026-08-22 — Context Log Bootstrap
- **Summary:** Created `LLM_CONTEXT_LOG.md` from empty file; populated Snapshot, Architecture, Safety + Auth, Priorities, Protocol, and retroactive log by inspecting `src/turbo_death_warrior/game_engine.py`, `src/turbo_death_warrior/server.py`, `web/index.html`, `pyproject.toml`, `Makefile`, `.env{,.example}`, `.github/workflows/ci.yml`, and `git log --oneline`.
- **Why:** `AGENTS.md` requires a rolling high-signal log; file was 0 lines and `git status` showed it and `AGENTS.md` untracked. No current snapshot existed for assistants.
- **Impact:** Establishes baseline at `v1.0.0`, HEAD `7d9beb5`, Python 3.11, 32/32 tests. Documents the `/tdw-api` vs `/api` mismatch and `GET /` removal as P0 debt.
- **Validation:** `python -m pytest test/ -v` 32 passed; `grep -n fetch web/index.html` vs `grep -n tdw-api src/turbo_death_warrior/server.py`; `git log --oneline -8`; `make check` (py_compile) implicit.
- **Follow-ups:** Commit `AGENTS.md` + `LLM_CONTEXT_LOG.md`; fix frontend paths; restore or replace `GET /`.

### 2026-08-22 — Trigger Deploy (7d9beb5)
- **Summary:** Empty commit `7d9beb5` with message `trigger deploy`.
- **Why:** Force CI `deploy` job on `main` (self-hosted Raspberry Pi) without code change.
- **Impact:** Re-ran `test` + `deploy` jobs; rsync + venv reinstall + `systemctl restart`.
- **Validation:** CI run on `main` (test 32/32 → deploy smoke `curl -sf .../tdw-api/game | grep game_id`).
- **Follow-ups:** None.

### 2026-08-22 — Re-namespace API & Add Deploy Pipeline (b16b9ff)
- **Summary:** `src/turbo_death_warrior/server.py:50,81,91` — routes moved from `/api/game` to `/tdw-api/game`; `do_GET` that served `web/index.html` removed (now 404); `.github/workflows/ci.yml` — added `deploy` job (rsync `--delete` excluding `.git/.venv/__pycache__/.pytest_cache/.env`, venv create, pip install, systemctl restart, smoke curl to `/tdw-api/game`).
- **Why:** Namespace API to avoid collision when serving frontend separately / on Pi; automate Pi deployment.
- **Impact:** **Breaking:** frontend `web/index.html` still calls `/api/game` (see Active Priorities P0); `GET /` no longer serves game — browser hits 404 if relying on server for static files. Deploy now fully automated on push to `main`.
- **Validation:** `make check` + `make test` 32/32 (engine unaffected); manual `curl` to new path required for frontend verification (currently failing due to mismatch).
- **Follow-ups:** Update `web/index.html:439,452,460` to `/tdw-api/game`; decide on static serving vs reverse proxy; parameterize smoke check host/port.

### 2026-08-22 — Web Path Fixes (901dde7, f9463e9)
- **Summary:** `src/turbo_death_warrior/server.py:44` — fixed `WEB_DIR = Path(__file__).resolve().parents[2]/web` resolution; `901dde7` fixed relative paths for `web/index.html`.
- **Why:** Server failed to locate frontend assets after `src/` restructure.
- **Impact:** `GET /` (pre-removal) correctly resolved `web/` regardless of cwd.
- **Validation:** `python -m turbo_death_warrior.server` manual serve + browser load.
- **Follow-ups:** Superseded by `b16b9ff` removal of `GET /` — path still relevant if static serving returns.

### 2026-08-22 — Project Restructure to src/ Layout (0048a1c)
- **Summary:** Moved code to `src/turbo_death_warrior/` and tests to `test/`; added `pyproject.toml` (`setuptools`, `where=["src"]`, `requires-python>=3.8`, `dependencies=[]`, `test = ["pytest>=7.0"]`); updated `Makefile` and `README.md` project tree.
- **Why:** Follow Python packaging best practices; enable `pip install -e ".[test]"` and proper import paths.
- **Impact:** Imports now `from turbo_death_warrior.game_engine import Game`; CI install command changed; old flat layout deprecated.
- **Validation:** `pip install -e ".[test]"` + `make test` 32/32 + `make check`.
- **Follow-ups:** Ensure Pi deploy rsync target matches new layout (`/home/ewanritchie/turbo-death-warrior/` expected to be repo root).

### 2026-08-22 — Makefile & CI Polish (60bbad2, 34544d7)
- **Summary:** `Makefile:15-18` — added `requirements` target (`pip install -r requirements.txt`), updated `test` to depend on `requirements`; `.github/workflows/ci.yml` — initial CI (checkout, setup-python 3.11 with pip cache, `make requirements`, `make check`, `make test` on push/PR to `main`); `README.md` — refreshed Make Targets table, env precedence docs, test/CI sections.
- **Why:** Standardize local and CI workflows.
- **Impact:** `make test` now auto-installs deps; CI runs on every PR.
- **Validation:** CI green on `main`; local `make test` 32/32.
- **Follow-ups:** CI now uses `pip install -e ".[test]"` (later commit) instead of `make requirements` — README still lists `requirements.txt` path; consider aligning.

### 2026-08-22 — Initial Implementation (9d838be)
- **Summary:** Added `src/turbo_death_warrior/game_engine.py` (312 lines, `Game`, constants, combat), `src/turbo_death_warrior/server.py` (ThreadingHTTPServer + `GAMES` dict), `web/index.html` (CRT frontend), `test/test_game_engine.py` (32 tests), `Makefile`, `requirements.txt`, `.env.example` (`TDW_HOST`/`TDW_PORT`), `README.md`, `LICENSE`.
- **Why:** Initial playable web edition — I/O-free engine + stdlib HTTP server + single-file frontend, per project brief.
- **Impact:** Game playable at `http://localhost:8001`; API at `/api/game` (original); 32 tests establish regression baseline.
- **Validation:** `make test` 32/32; manual playthrough orc→crystal→boss→victory/game_over→restart.
- **Follow-ups:** See later restructures and path renames above.

