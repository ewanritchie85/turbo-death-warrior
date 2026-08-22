# LLM Context Log — Turbo Death Warrior

> Rolling high-signal summary for any coding assistant (Copilot, opencode, Muse Spark, etc.).
> Read this first to avoid re-discovering the codebase. Update per `AGENTS.md` after every meaningful change.

**Last Updated:** 2026-08-22
**Project:** Turbo Death Warrior - API (`turbo-death-warrior` v1.0.0)
**Repo:** `turbo_death_warrior` @ `main` (HEAD `561ea9c` + web removal pending)
**Status:** Stable API-only; CI green (32/32 tests); deploy pipeline to Raspberry Pi self-hosted runner live; frontend lives in `my-website` (`js/turbo-death-warrior.js`); this repo intentionally has no `web/`.

---

## Current Snapshot

**What it is:** Backend API for the *Turbo Death Warrior* terminal adventure — I/O-free `Game` engine plus stdlib HTTP server. Fight a Caffeinated Orc, loot the Turbo Crystal, and defeat the Mega-Goblin King. Frontend is `my-website/js/turbo-death-warrior.js` (rendered via `projects.html#turbo-death-warrior`); this repo is API-only by design.

**Stack:**
- Python 3.11, **stdlib only** for runtime (`http.server.ThreadedHTTPServer`, `secrets`, `threading`, `time`, `pathlib`, `json`, `random`).
- `pytest>=7.0` for tests only (`requirements.txt` / `[project.optional-dependencies] test` in `pyproject.toml:14`).
- `src` layout (`pyproject.toml:16` — `where = ["src"]`), installed editable via `pip install -e ".[test]"`.
- No `web/` in this repo — frontend lives in `my-website` (see Architecture).

**How to run:**
```sh
make            # defaults to TDW_HOST=127.0.0.1 TDW_PORT=8001, see .env / .env.example
make run PORT=9000 HOST=0.0.0.0
python3 -m turbo_death_warrior.server
```
API-only: `GET /` → `404`; play via `my-website` or `curl -X POST http://localhost:8001/tdw-api/game`.
Config precedence: real env vars > `.env` > built-in defaults (`src/turbo_death_warrior/server.py:43-46` includes `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS`).

**Tests:** `make test` → `python -m pytest test/ -v` — **32 passed** as of 2026-08-22. Covers init, name submission, town/cave/combat, orc/boss defeat, game-over, restart, serialization, constants, payload structure.

**CI/CD:** `.github/workflows/ci.yml` — `test` job (checkout, setup-python 3.11, `pip install -e ".[test]"`, `make check`, `make test`) on push/PR to `main`; `deploy` job (self-hosted, `needs: test`, only on `push` to `main`) rsyncs to `/home/ewanritchie/turbo-death-warrior/`, recreates `.venv`, `systemctl restart turbo-death-warrior`, smoke-checks `curl -sf http://127.0.0.1:8001/tdw-api/game`.

**Git state (2026-08-22):**
- Branch `main` ahead of `origin/main` by 1 (`561ea9c` committed) + pending API-only split: `web/index.html` deleted, `README.md`/`.env.example` updated, this log pending.
- 10 commits since `4b8e037` (initial). HEAD `561ea9c fix(server): TTL eviction for GAMES, remove WEB_DIR; docs: Definition of done + context log sync`.
- Working tree modified (not yet committed) — this log + `README.md` + `.env.example` + `web/` deletion.

**Known drift / debt:**
- API-only by design: `server.py:90` `do_GET` → `404`; no `web/` frontend in this repo. Play via `my-website/js/turbo-death-warrior.js:4` (`/tdw-api`) + `projects.html:297` `#tdw-game` behind Nginx `/tdw-api` proxy. Prior `web/index.html:439` → `/api` mismatch is now moot (frontend removed).
- `.env.example` now corrected to `TDW_PORT=8001` (was `9999`) and documents `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS` — README aligned.
- Server `AGENTS.md:18` defines Definition of done (`make check` + `make test` + log entry + stale-priority pruning) — satisfied for prior TTL fix; this web-removal change satisfies it again (see new entry below).

---

## Architecture

```
turbo_death_warrior/  (API-only, no web/)
├── src/turbo_death_warrior/
│   ├── __init__.py               # __version__ = "1.0.0"
│   ├── game_engine.py:19         # class Game — I/O-free engine; HEAL_AMOUNT=40, STRIKE_DAMAGE=150
│   └── server.py:1-140           # ThreadingHTTPServer, TTL sweep, Handler (API-only, GET / → 404)
├── test/test_game_engine.py      # 32 pytest cases (7 classes + constants/payload)
├── pyproject.toml                # setuptools, src layout, requires-python >=3.8
├── Makefile                      # run/check/test/requirements/clean; RUN_ENV override
├── requirements.txt              # pytest>=7.0
├── .env / .env.example           # TDW_HOST, TDW_PORT, TDW_GAME_TTL_SECONDS, TDW_SWEEP_INTERVAL_SECONDS
└── .github/workflows/ci.yml      # test + deploy (self-hosted)

# Frontend lives in my-website (separate repo): js/turbo-death-warrior.js + projects.html#turbo-death-warrior
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

**Frontend (my-website, not this repo):**
- `my-website/js/turbo-death-warrior.js:1-301` — namespaced `tdw*` controller (mirrors old `web/index.html` logic: `tdwApi`→`fetch(TDW_API_BASE+"/tdw-api"+path)`, `tdwBar`/`tdwHpClass`/`tdwPad`, `tdwSetState` → `#tdw-statusline`/`#tdw-enemyline`, typewriter `tdwStartTyping`/`tdwTypeNextLine` 28ms/80ms, `tdwRenderControls` → `#tdw-choices`/`#tdw-nameform`, `tdwHandle`/`tdwChoose`/`tdwInit` injecting `#tdw-game` at `turbo-death-warrior.js:199-227`, `initTurboDeathWarrior()` called from `js/functions.js:33` on `#turbo-death-warrior.active`). `my-website/projects.html:19,297` loads script and hosts `<div id="tdw-game">`. CSS uses `tdw-*` prefixed vars mirroring old amber CRT. This repo has no frontend — API-only.
- Historical: `web/index.html` (466 lines, single-file) was removed in this change; see Change Log "API-only split". Prior API contract `GET /` served it until `b16b9ff` removed handler → `404`.

**API contract (this repo):**
| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/tdw-api/game` | `{}` | `{messages, options, text_input, state, game_id}` |
| POST | `/tdw-api/game/<id>/name` | `{"name": str}` | `{messages, options, text_input, state}` |
| POST | `/tdw-api/game/<id>/action` | `{"id": str}` | `{messages, options, text_input, state}` |
| GET | `/` | — | 404 (API-only — frontend is `my-website`) |

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

1. **Test coverage gap:** No server integration tests (only `test/test_game_engine.py` covers `Game`; `server.py` `Handler`/`GAMES`/sweep has 0 coverage). Add `test_server.py` for `Handler` routing, 404s, bad JSON, unknown/swept `game_id`, TTL eviction and `last_active` touch behavior, and concurrent access. Cheap sweep tests (mock `time.time`/`sleep`, short TTL) welcome without large scaffolding — see Change Log 2026-08-22 sweep fix for manual mock verification pattern.

*Recently resolved (pruned from active):*
- **Frontend split (API-only)** — 2026-08-22 backend is API-only by design; `web/index.html` deleted, frontend is `my-website/js/turbo-death-warrior.js:1` + `projects.html:19,297` (`/tdw-api` via Nginx). Prior `web/index.html` → `/api` mismatch now moot (intentional separation, not a bug).
- **Port defaults + new env vars** — 2026-08-22 `.env.example` corrected `TDW_PORT 9999→8001` and now documents `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS`; `README.md:53` aligned.
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

### 2026-08-22 — API-only Split: Remove web/ Frontend, Backend Stays Separate (README + .env.example + web deletion)
- **Summary:** Deleted `web/index.html` (466 lines) and `web/` dir; this repo is now API-only by design — frontend lives solely in `my-website/js/turbo-death-warrior.js:1` + `projects.html:19,297` (via `js/functions.js:33` `initTurboDeathWarrior()`). Updated `README.md:1-122` to API title/description, Quick Start to `curl -X POST /tdw-api/game` (no `GET /` browser open), Project Structure to remove `web/`, API Overview to `POST /tdw-api/game` (+ `GET / →404` note) and to document TTL eviction, plus Config snippet now includes `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS`; fixed `.env.example:8` `TDW_PORT 9999→8001` and added `TDW_GAME_TTL_SECONDS=3600`/`TDW_SWEEP_INTERVAL_SECONDS=300`. Synced `LLM_CONTEXT_LOG.md:6-111` (Snapshot what-it-is/stack/how-to-run/git-state/known-drift, Architecture tree/frontend note, API contract, Priorities pruning).
- **Why:** User decision to keep `turbo_death_warrior` as backend-only project/repo, `my-website` as sole frontend — eliminates duplication (`web/index.html` vs `my-website/js/turbo-death-warrior.js` shared ~90% logic but diverged `/api` vs `/tdw-api` at `web/index.html:439` vs `turbo-death-warrior.js:4`) and resolves stale P0 "frontend↔API mismatch" as intentional separation, not a bug.
- **Impact:** Breaking for local `web/` users: no static frontend served (`server.py:90` already `404`); play via `my-website` or direct `/tdw-api` curl. Repo smaller, single source of truth for frontend. Docs now match reality (API-only). No `server.py`/`game_engine.py` behavior change.
- **Validation:** `rm -rf web` + `git status` shows `D web/index.html`; `grep -r web/index` confirms no refs remain in `README.md`/`.env.example`/`server.py`; `make check` OK (`py_compile` both modules); `make test` 32/32 (`test/test_game_engine.py`); manual `cat README.md`/`cat .env.example` verification.
- **Follow-ups:** Consider cross-repo doc link from `my-website` to this API; no further `web/` maintenance needed.

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

