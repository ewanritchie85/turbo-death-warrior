# LLM Context Log — Turbo Death Warrior

> Rolling high-signal summary for any coding assistant (Copilot, opencode, Muse Spark, etc.).
> Read this first to avoid re-discovering the codebase. Update per `AGENTS.md` after every meaningful change.

**Last Updated:** 2026-08-23
**Project:** Turbo Death Warrior - API (`turbo-death-warrior` v1.0.0)
**Repo:** `turbo_death_warrior` @ `main` (HEAD `561ea9c` + web removal pending)
**Status:** Stable API-only; CI green (53/53 tests); deploy pipeline to Raspberry Pi self-hosted runner live; frontend lives in `my-website` (`js/turbo-death-warrior.js`); this repo intentionally has no `web/`.

---

## Current Snapshot

**What it is:** Backend API for the *Turbo Death Warrior* terminal adventure — I/O-free `Game` engine plus stdlib HTTP server. Three-act structure: Act 1 (Oakhaven → Burzum Forest → Raider Scout), Act 2 (The Road → Ruins/Ambush → Trading Post with Kessa Vane → Mountain Pass with Bandit Captain), Act 3 (Fortress Gate → The High Priest's Guard → Throne Room with The High Priest of Doom). Core mechanics: Turbo Death Rune (grants randomized 90-130 damage Turbo Death in boss fights), Atlantean Sword (40 damage, earned from Bandit Captain), potion-based healing (40 HP). Frontend is `my-website/js/turbo-death-warrior.js` (rendered via `projects.html#turbo-death-warrior`); this repo is API-only by design.

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

**Tests:** `make test` → `python -m pytest test/ -v` — **53 passed** as of 2026-08-23. Covers init, name submission, town/road/fortress/combat, Raider Scout/cultist/bandit/Bandit Captain/Warlord Guard/Malgrim defeat, game-over, restart, dead-end payload fix, full playthrough, serialization, constants, payload structure.

**CI/CD:** `.github/workflows/ci.yml` — `test` job (checkout, setup-python 3.11, `pip install -e ".[test]"`, `make check`, `make test`) on push/PR to `main`; `deploy` job (self-hosted, `needs: test`, only on `push` to `main`) rsyncs to `/home/ewanritchie/turbo-death-warrior/`, recreates `.venv`, `systemctl restart turbo-death-warrior`, smoke-checks `curl -sf http://127.0.0.1:8001/tdw-api/game`.

**Git state (2026-08-22):**
- Branch `main` ahead of `origin/main` by 1 (`561ea9c` committed) + pending API-only split: `web/index.html` deleted, `README.md`/`.env.example` updated, this log pending.
- 10 commits since `4b8e037` (initial). HEAD `561ea9c fix(server): TTL eviction for GAMES, remove WEB_DIR; docs: Definition of done + context log sync`.
- Working tree modified (not yet committed) — this log + `README.md` + `.env.example` + `web/` deletion.

**Known drift / debt:**
- API-only by design: `server.py:90` `do_GET` → `404`; no `web/` frontend in this repo. Play via `my-website/js/turbo-death-warrior.js:4` (`/tdw-api`) + `projects.html:297` `#tdw-game` behind Nginx `/tdw-api` proxy. Prior `web/index.html:439` → `/api` mismatch is now moot (frontend removed).
- `.env.example` now corrected to `TDW_PORT=8001` (was `9999`) and documents `TDW_GAME_TTL_SECONDS`/`TDW_SWEEP_INTERVAL_SECONDS` — README aligned.
- Server `AGENTS.md:18` defines Definition of done (`make check` + `make test` + log entry + stale-priority pruning) — satisfied for prior TTL fix; this web-removal change satisfies it again (see new entry below).
- **Engine data is now table-driven:** location/enemy/weapon data lives in `LOCATIONS`, `ENEMY_TEMPLATES`, `WEAPONS` dicts; new narrative content can be added primarily by extending these tables rather than writing new code paths. The farming-loop exploit (fixed in Step 2) and dead-end post-game payload bug (fixed in Step 5) are both resolved.
- **Potion economy analysis (Step D):** Required-path potion count (5 total: 2 starting + 1 Raider Scout + 2 Bandit Captain) yields ~200 HP healing vs ~142 HP expected damage across 5 required fights. Player enters final fight with ~27 HP and 5 potions, uses ~3 in Malgrim fight, leaving 2 unused. Economy is tight but functional — meaningful resource pressure without blocking progress. Optional ambush (Bandit) adds +1 potion for ~11 HP cost (net positive). **No rebalance needed.**

---

## Architecture

```
turbo_death_warrior/  (API-only, no web/)
├── src/turbo_death_warrior/
│   ├── __init__.py               # __version__ = "1.0.0"
│   ├── game_engine.py:19         # class Game — I/O-free engine; HEAL_AMOUNT=40
│   └── server.py:1-140           # ThreadingHTTPServer, TTL sweep, Handler (API-only, GET / → 404)
├── test/test_game_engine.py      # 53 pytest cases (11 classes + constants/payload)
├── pyproject.toml                # setuptools, src layout, requires-python >=3.8
├── Makefile                      # run/check/test/requirements/clean; RUN_ENV override
├── requirements.txt              # pytest>=7.0
├── .env / .env.example           # TDW_HOST, TDW_PORT, TDW_GAME_TTL_SECONDS, TDW_SWEEP_INTERVAL_SECONDS
└── .github/workflows/ci.yml      # test + deploy (self-hosted)

# Frontend lives in my-website (separate repo): js/turbo-death-warrior.js + projects.html#turbo-death-warrior
```

**Game engine (`src/turbo_death_warrior/game_engine.py`):**
- State: `player: {name, hp, max_hp, weapon, damage, potions}`, `flags: set()` (avenged_raider, has_finisher_item, learned_plan, cleared_ambush, recruited_ally, defeated_captain), `enemy: {key, name, hp, max_hp, dmg}|None`, `boss_fight: bool`, `scene: str`, `over: bool`, `_weapon_id: str`.
- Constants: `HEAL_AMOUNT=40`.
- Tables:
  - `LOCATIONS` (6): `name_prompt`, `town` (Oakhaven Village), `forest` (Burzum Forest), `road` (The Road), `fortress_gate` (Fortress Gate), `throne_room` (Throne Room).
  - `ENEMY_TEMPLATES` (6): `raider_scout` (Raider Scout, hp 40, dmg 12, drops Turbo Death Rune + potion, flags avenged_raider/has_finisher_item), `cultist` (Noothgrush Cultist, hp 35, dmg 13, drops learned_plan), `bandit` (Bandit, hp 28, dmg 10, drops cleared_ambush + potion), `bandit_captain` (Bandit Captain, hp 60, dmg 15, drops defeated_captain + 2 potions, grants Atlantean Sword), `warlord_guard` (The High Priest's Guard, hp 45, dmg 14), `high_priest` (The High Priest of Doom, hp 150, dmg 22, ending: victory).
  - `WEAPONS` (3): `starting` (Rusty Spoon, 10 dmg), `blacksmith_upgrade` (Blade of Grief, 25 dmg, obtained_from: blacksmith), `captains_blade` (Atlantean Sword, 40 dmg, obtained_from: bandit_captain).
- Scenes: `name_prompt → town → (forest→combat vs raider_scout) → town → (road→cultist/bandit→trading_post→bandit_captain) → fortress_gate → (corridor→warlord_guard) → throne_room → (auto_encounter high_priest) → victory|game_over`.
- Public API: `Game.start() → payload`, `submit_name(raw_name)`, `act(action_id)`. Every call returns `_payload() {messages[], options[], text_input?, state{scene,over,player,enemy}}`.
- Key mechanics: Turbo Death Rune flag (`has_finisher_item`) enables Turbo Death (randomized 90-130 dmg) in boss fights; single-flag `show_if`/`hide_if` gating chains Act 2 options (learned_plan → recruited_ally); `_win_fight()` generic over `ENEMY_TEMPLATES` drops/win_messages/goto/ending.
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

### 2026-08-23 — Step E: Narrative Naming Pass (game_engine.py + test_game_engine.py + LLM_CONTEXT_LOG.md)
- **Summary:** Applied exact rename mapping across `game_engine.py` (ENEMY_TEMPLATES, WEAPONS, LOCATIONS, combat messages, opening crawl, stats, trading post) and `test_game_engine.py` (all assertions): "Captain's Blade" → "Atlantean Sword", "Rusty Spork" → "Rusty Spoon", "Chainsaw-Sword" → "Blade of Grief", "Bloodstone Shard" → "Turbo Death Rune", "Bloodstone Strike" → "Turbo Death", "Malgrim"/"Malgrim the Ashbringer" → "The High Priest of Doom" (ENEMY_TEMPLATES key "malgrim" → "high_priest", `_start_combat()` boss_fight check updated), "Whispering Forest" → "Burzum Forest", "Ash Cultist" → "Noothgrush Cultist". Updated `_start_combat()` boss_fight check to `key == "high_priest"`. Updated `LLM_CONTEXT_LOG.md` Current Snapshot and Architecture to new names.
- **Why:** Step E — narrative naming pass to establish final intended theme/terminology after Acts 1-3 complete.
- **Impact:** Pure renaming — public API payload shape unchanged. All internal identifiers and display text updated. **Verified Turbo Death option appears correctly in final fight** (confirms boss_fight key rename works). All 53 tests pass.
- **Validation:** `make check` OK; `make test` 53/53; verified Turbo Death option appears in High Priest fight, Atlantean Sword granted on Bandit Captain defeat.
- **Follow-ups:** None — narrative overhaul complete.

### 2026-08-23 — Step D: Verification & Cleanup (LLM_CONTEXT_LOG.md only)
- **Summary:** `LLM_CONTEXT_LOG.md` — rewrote **Current Snapshot** and **Architecture** sections to reflect the final three-act game (Act 1: Oakhaven/Forest/Raider Scout; Act 2: Road/Kessa Vane/Cultist/Bandit/Bandit Captain/Captain's Blade; Act 3: Fortress Gate/Warlord Guard/Throne Room/Malgrim the Ashbringer). Documented full location/enemy/weapon tables, Bloodstone Shard/Strike mechanic, Kessa Vane as named recurring character, Captain's Blade. Added potion economy analysis to **Known Gaps**: 5 potions (200 HP) vs ~142 HP expected damage across 5 required fights — tight but functional, no rebalance needed. Flagged one in-story "Turbo Death Warrior" reference in blacksmith dialogue (`game_engine.py:104`).
- **Why:** Step D (final) of the narrative overhaul — verification pass and context log sync after Acts 1-3 complete.
- **Impact:** Documentation only — no code changes. Public API payload shape unchanged. All 53 tests pass.
- **Validation:** `make check` OK; `make test` 53/53; potion economy trace verified (5 potions, ~142 HP damage, ~3 used in final fight, 2 leftover).
- **Follow-ups:** None — content overhaul complete. Engine ready for future narrative expansions via table extensions.

### 2026-08-23 — Act 3 Content Addition: Fortress, Malgrim, Cleanup (game_engine.py + test_game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py` — removed obsolete `LOCATIONS["cave_entrance"]` (bypassed Act 2); fixed `ENEMY_TEMPLATES["raider_scout"]["goto"]` to "town"; added Act 3 locations: `fortress_gate` (real, with `enter_fortress` → `warlord_guard`), `throne_room` (auto_encounter: `malgrim`); added ENEMY_TEMPLATES: `warlord_guard` (hp 45, dmg 14, goto: `throne_room`), `malgrim` (renamed from `boss`, name "Malgrim the Ashbringer", hp 150, dmg 22, new `win_messages`, ending: `victory`); updated `_start_combat()` boss_fight check to `key == "malgrim"`; added `_win_fight()` special case for `bandit_captain` granting `captains_blade`. `test/test_game_engine.py` — removed `TestCaveEntranceActions`, `TestFarmingLoopFix` (obsolete); added `TestMalgrimCombat`, `TestAct3Fortress`, `TestFullPlaythrough`; updated `TestRestart`, `TestDeadEndPayloadFix`, `TestConstants` for new enemy keys and flow.
- **Why:** Step C of 4-step narrative overhaul — completes Act 3 (fortress/Malgrim), retires obsolete Act 1-era `cave_entrance` shortcut that bypassed Act 2, and fixes the `boss_fight` string comparison for the renamed final boss.
- **Impact:** Content + cleanup — public API payload shape unchanged. Old `cave_entrance` location and `boss` enemy key removed; `raider_scout` goto fixed to "town" so Act 2 cannot be skipped. All 53 tests pass.
- **Validation:** `make check` OK; `make test` 53/53; verified full playthrough Act 1→2→3 with no bypass, Malgrim fight shows Bloodstone Strike option, `captains_blade` granted on bandit_captain defeat.
- **Follow-ups:** Step D (full manual/scripted playthrough verification) pending.

### 2026-08-23 — Act 2 Content Addition: Road Hub, Kessa Vane, Cultists, Bandits, Captain's Blade (game_engine.py + test_game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py` — added `depart_road` option to town (show_if: `avenged_raider`, goto: `road`); new `LOCATIONS["road"]` with on_enter (Kessa Vane trading post intro) and four options chained via single-flag gating: `explore_ruins` (encounter: `cultist`, hide_if: `learned_plan`), `clear_ambush` (encounter: `bandit`, hide_if: `cleared_ambush`), `visit_trading_post` (action: `_trading_post`, show_if: `learned_plan`, hide_if: `recruited_ally`), `confront_the_pass` (encounter: `bandit_captain`, show_if: `recruited_ally`). Added `_trading_post()` method granting `recruited_ally` flag. Added three ENEMY_TEMPLATES: `cultist` (drops `learned_plan`), `bandit` (drops `cleared_ambush` + potion), `bandit_captain` (drops `defeated_captain` + 2 potions, goto: `fortress_gate`). Added `captains_blade` weapon (40 dmg, `obtained_from: "bandit_captain"`) granted in `_win_fight()` special case for bandit_captain. Added placeholder `fortress_gate` location — `_goto()` already returns graceful "Invalid location." payload for unknown locations, but placeholder added for clean resolution. `test/test_game_engine.py` — added `TestAct2RoadHub` (8 tests for flag-chain option visibility, trading post, full path) and `TestAct2EnemyTemplates` (7 tests for templates/weapons/locations).
- **Why:** Step B of 4-step narrative overhaul — adds Act 2 (road) content using existing table-driven architecture. Single-flag gating chain (learned_plan → recruited_ally) works within engine's show_if/hide_if single-flag limit.
- **Impact:** Content only — public API payload shape unchanged. New location/enemy/weapon entries follow established patterns. All 51 tests pass (35 original + 16 new). `fortress_gate` placeholder resolves gracefully; Step C will flesh it out.
- **Validation:** `make check` OK; `make test` 51/51; verified flag-chain option visibility (explore/ambush → trading_post → pass), trading post sets recruited_ally, full Act 2 path reaches fortress_gate, Captain's Blade weapon granted with flavor messages.
- **Follow-ups:** Step C (Act 3: fortress/Malgrim, boss→malgrim rename) and Step D (full playthrough verification) pending.

### 2026-08-23 — Act 1 Content Overhaul: Opening, Raider Scout, Bloodstone Shard, Randomized Strike (game_engine.py + test_game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py` — replaced opening crawl in `start()` with new narrative text; updated `LOCATIONS["town"]["on_enter"]` and `["forest"]["on_enter"]` descriptions; renamed ENEMY_TEMPLATES key `"orc"` → `"raider_scout"` (name "Raider Scout", same hp/dmg) with new `win_messages` about the Bloodstone Shard; changed flag `"defeated_orc"` → `"avenged_raider"` in drops and all `LOCATIONS["town"]` gating (`hide_if`/`show_if`); updated `_stats()` display to "Bloodstone Shard: Yes/No"; updated `_combat_options()` strike label to "USE BLOODSTONE STRIKE (Requires Bloodstone Shard)"; updated `_combat_turn()` strike messages and randomized damage to `random.randint(90, 130)` (removed unused `STRIKE_DAMAGE` constant). `test/test_game_engine.py` — updated all assertions for new enemy key, flag name, narrative text, and randomized strike damage bounds.
- **Why:** Step A of 4-step narrative overhaul (Acts 1-3) — establishes new story (Malgrim, warband, Bloodstone Shard) and renames/core mechanics for Act 1 content. Uses existing LOCATIONS/ENEMY_TEMPLATES/WEAPONS/flags architecture from refactor.
- **Impact:** Content only — public API payload shape unchanged. Enemy key/flag changes are internal; tests updated. Removed dead `STRIKE_DAMAGE` constant. All 35 tests pass.
- **Validation:** `make check` OK; `make test` 35/35; verified new opening crawl, town/forest descriptions, raider_scout combat, Bloodstone Shard naming, and 90-130 strike damage range.
- **Follow-ups:** Steps B (Act 2: road/Kessa/bandits/cultists), C (Act 3: fortress/Malgrim boss rename), D (full playthrough verification) pending.

### 2026-08-23 — Game Engine Refactor Step 5: Dead-End Post-Game Payload Fix (game_engine.py + test_game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py:161-172` — fixed `act()` when `self.over` is True and action is not "restart": previously returned empty `_payload([])`, now returns a short message + correct restart option. Uses "Play Again" label for `victory` scene, "Try Again" for `game_over` (matching existing labels in `_win_fight()` and `_game_over()`). `test/test_game_engine.py` — added `TestDeadEndPayloadFix` with two tests (victory and game_over paths).
- **Why:** Step 5 (final) of the data-driven refactor — fixes the known "dead-end payload" bug from Known Gaps where post-game non-restart actions gave frontend nothing to render.
- **Impact:** Behavioral fix only — public API payload shape unchanged (still `messages`, `options`, `text_input`, `state`). Now always returns a helpful message and the restart button instead of empty payload. All 35 tests pass.
- **Validation:** `make check` OK; `make test` 35/35 (33 original + 2 new dead-end tests).
- **Follow-ups:** Refactor complete. Engine ready for new narrative content via LOCATIONS/ENEMY_TEMPLATES/WEAPONS tables.

### 2026-08-23 — Game Engine Refactor Step 4: WEAPONS Data-Driven Blacksmith (game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py:42-56,108-114,235-256` — added module-level `WEAPONS` dict with `starting` (Rusty Spork, 10 dmg) and `blacksmith_upgrade` (Chainsaw-Sword, 25 dmg, `obtained_from: "blacksmith"`, `flavor` lines copied verbatim from old `_blacksmith()`). Added `self._weapon_id` in `reset()` (separate from `self.player` to keep serialized shape unchanged) and `_apply_weapon(weapon_id)` helper that syncs `self._weapon_id` and `self.player["weapon"]/["damage"]`. Rewrote `_blacksmith()` to find first unowned `obtained_from: "blacksmith"` weapon, apply it via `_apply_weapon()`, and emit its `flavor` lines; fallback message unchanged for "already have best weapon".
- **Why:** Step 4 of the data-driven refactor — replaces hardcoded single blacksmith upgrade with a declarative table supporting future tiers/sources. Internal tracking moved to `self._weapon_id` so `self.player` key set (`name, hp, max_hp, potions, weapon, damage`) and `_state()` payload shape are unchanged.
- **Impact:** Internal only — **verified byte-for-byte identical `_blacksmith()` message output** for both first visit (3 flavor lines + town banner) and subsequent visits (fallback message + town banner). All 33 tests pass.
- **Validation:** `make check` OK; `make test` 33/33; manual diff of message lists before/after confirms zero delta; `self.player.keys()` unchanged.
- **Follow-ups:** Step 5 (dead-end post-game payload fix) still pending; then refactor complete and ready for new narrative content.

### 2026-08-23 — Game Engine Refactor Step 3: ENEMY_TEMPLATES Data-Driven Win Handling (game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py:13-36,303-322` — extended `ENEMY_TEMPLATES` entries with `drops` (potions/flags), `win_messages`, and either `goto` (orc → cave_entrance) or `ending` (boss → victory). Rewrote `_win_fight()` to be generic: looks up template by key, appends defeat message, applies drops, extends win_messages, then dispatches via `goto` (calling `_goto()` which reuses `LOCATIONS["cave_entrance"]["on_enter"]`) or `ending` branch. Removed duplicated cave entrance banner from orc win_messages — now sourced from LOCATIONS.
- **Why:** Step 3 of the data-driven refactor — eliminates hardcoded `if key == "orc"` branching in `_win_fight()`, makes enemy win behavior fully declarative.
- **Impact:** Internal only — public API payload shape unchanged. **Verified byte-for-byte identical message sequences** for both orc win (7 messages: defeat line, 3 loot lines, blank, 2 cave entrance banner lines) and boss win (4 messages: defeat line, 3 victory lines). All 33 tests pass.
- **Validation:** `make check` OK; `make test` 33/33; manual diff of message lists before/after confirms zero delta.
- **Follow-ups:** Refactor steps 4-5 pending: (4) `WEAPONS` table for blacksmith, (5) dead-end payload fix. ENEMY_TEMPLATES now declarative; LOCATIONS handles navigation; flags handle state.

### 2026-08-23 — Game Engine Refactor Step 2: LOCATIONS Data-Driven Navigation + Farming Loop Fix (game_engine.py + test_game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py` — added module-level `LOCATIONS` dict (town, forest, cave_entrance) with `on_enter` messages and declarative options (`goto`, `encounter`, `action`, `show_if`/`hide_if` gating on flags). Replaced `_scene_options()` if/elif chain and per-location methods (`_to_town`, `_enter_forest`, `_enter_caves`, `_flee_town`) with generic `_goto()`, `_dispatch_option()`, `_find_option()`. Added `defeated_orc` flag in `_win_fight()` orc branch; town's `go_forest` now `hide_if: "defeated_orc"`, new `return_to_caves` option `show_if: "defeated_orc"` with `goto: "cave_entrance"`. `test/test_game_engine.py` — added `TestFarmingLoopFix.test_defeated_orc_removes_forest_option_adds_return_to_caves`; all 33 tests pass.
- **Why:** Step 2 of the data-driven refactor — migrates town/forest/cave_entrance navigation to a declarative table, and fixes the previously-known farming-loop exploit (defeating orc, fleeing to town, re-entering forest to re-fight orc for infinite crystals/potions).
- **Impact:** Internal structure only — public API payload shape unchanged; all message text, option labels, and scene names for existing content preserved byte-for-byte. Farming loop fixed: after orc defeat, town no longer offers forest, offers direct return to caves instead. `defeated_orc` flag persists across restarts only until game reset.
- **Validation:** `make check` OK; `make test` 33/33 (32 original + 1 new farming-loop test).
- **Follow-ups:** Refactor steps 3-5 pending: (3) `ENEMY_TEMPLATES` overhaul, (4) `WEAPONS` table, (5) dead-end payload fix. "Known Gaps" farming-loop item resolved.

### 2026-08-23 — Game Engine Refactor Step 1: Replace ad-hoc Boolean with Generic Flags Set (game_engine.py + test_game_engine.py)
- **Summary:** `src/turbo_death_warrior/game_engine.py:30-39,204,244-248,159` — added `self.flags = set()` in `reset()`; replaced `player["has_turbo_crystal"]` bool with `"has_finisher_item" in self.flags` across `_win_fight()` (orc branch, flag add), `_combat_options()` (flag check for strike option), `_combat_turn()` strike branch (flag check + `discard` after use), and `_stats()` (display "Special Item: Yes/No" sourced from flags). Updated messages to generic naming ("Special Item", "Finishing Move"). `test/test_game_engine.py` — updated assertions to check `flags` set and generic message text; same coverage.
- **Why:** First step of a planned refactor toward data-driven locations/enemies/weapons to support upcoming content expansion. Narrative-specific naming (turbo crystal, Mega-Goblin King, Oakhaven Village) is placeholder and will be replaced wholesale once the new plot is finalized; this step uses neutral internal names so no narrative touch-ups needed later.
- **Impact:** Internal representation only — public API payload shape unchanged (`messages`, `options`, `text_input`, `state`). `has_turbo_crystal` no longer in `player` dict; `_state()` still serializes `player` dict (now without that key). Flags set is internal, never leaks to payload. All 32 tests pass.
- **Validation:** `make check` OK; `make test` 32/32.
- **Follow-ups:** Refactor steps 2-5 pending: (2) add `defeated_orc` flag to fix farming loop, (3) introduce `LOCATIONS` data table, (4) introduce `ENEMY_TEMPLATES` overhaul, (5) introduce `WEAPONS` table. All narrative names remain placeholder pending plot redesign.

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

