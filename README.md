# Turbo Death Warrior - API

Backend for the *Turbo Death Warrior* terminal adventure — an API-only
service that powers the game. Three-act narrative: wake to find Oakhaven
burned, track the warband east on the Road (meeting Kessa Vane, clearing
ruins and ambushes, earning the Atlantean Sword from the Bandit Captain),
then breach the Fortress and confront the High Priest of Doom. The Turbo
Death Rune grants a devastating randomized finisher in boss fights.

The frontend lives in the portfolio site (`my-website/js/turbo-death-warrior.js`
rendered via `projects.html#turbo-death-warrior`); this repo is intentionally
API-only and has no bundled `web/` frontend.

Standard library only. No dependencies for the game itself; only `pytest` for
the test suite.

## Quick Start

```sh
make            # starts the API server on http://localhost:8001
```

or without make:

```sh
python3 -m turbo_death_warrior.server
```

The server is API-only (no static frontend — `GET /` returns `404`). The
game is played via the portfolio site (`my-website` → `projects.html`), or
against the API directly:

```sh
curl -X POST http://localhost:8001/tdw-api/game | jq
```

Stop with `Ctrl+C`.

## Make Targets

| Target        | Description                                            |
|---------------|--------------------------------------------------------|
| `run`         | Start the web server (default target)                  |
| `requirements`| Install Python dependencies (`pytest`)                 |
| `check`       | Byte-compile the Python sources as a sanity check      |
| `test`        | Run the test suite (depends on `requirements`)         |
| `clean`       | Remove caches (`__pycache__`, `.pytest_cache`)         |

Useful variables (all optional):

```sh
make run PORT=9000              # serve on a different port
make run HOST=0.0.0.0           # allow other devices on your LAN to play
```

Configuration is centralized in `.env` (see `.env.example`):

```sh
TDW_HOST=127.0.0.1              # 0.0.0.0 to allow LAN access
TDW_PORT=8001
TDW_GAME_TTL_SECONDS=3600       # idle seconds before game evicted
TDW_SWEEP_INTERVAL_SECONDS=300  # how often sweep runs
```

Precedence: command-line / real environment variables beat `.env`,
which beats the built-in defaults.

## Running Tests

```sh
make test
```

Or manually:

```sh
pip install -r requirements.txt
python -m pytest test/ -v
```

The test suite covers 53 cases across initialization, name submission, town
actions, road/fortress combat, enemy defeats (Raider Scout, Noothgrush Cultist,
Bandit, Bandit Captain, The High Priest's Guard, The High Priest of Doom),
game over, restart, state serialization, constants, and payload structure.

## CI / GitHub Actions

A workflow (`.github/workflows/ci.yml`) runs on every push and PR to `main`:

1. Sets up Python 3.11 with pip caching
2. Runs `make requirements`
3. Runs `make check`
4. Runs `make test`

## Project Structure

```
turbo_death_warrior/
├── src/
│   └── turbo_death_warrior/
│       ├── __init__.py
│       ├── game_engine.py       # I/O-free rewrite of the game logic
│       └── server.py            # stdlib HTTP server on port 8001 (API-only)
├── test/
│   └── test_game_engine.py      # 53 unit tests (pytest)
├── Makefile
├── requirements.txt             # pytest for test suite
├── .env                         # local config (not committed)
├── .env.example                 # config template
└── README.md
```

Frontend lives in `my-website` (`js/turbo-death-warrior.js` + `projects.html`), not here — this repo is API-only by design.

## API Overview

All endpoints speak JSON. The server holds one `Game` per ID in memory (TTL-evicted via `TDW_GAME_TTL_SECONDS`).

| Method | Path                        | Purpose                        |
|--------|-----------------------------|--------------------------------|
| POST   | `/tdw-api/game`             | Create a game, returns `game_id` |
| POST   | `/tdw-api/game/<id>/name`   | Submit player name             |
| POST   | `/tdw-api/game/<id>/action` | Perform a choice (`{"id": "attack"}`) |
| GET    | `/`                         | `404` (no frontend — use `my-website`) |

Each response contains `messages`, `options`, optional `text_input`,
and a `state` snapshot (player, enemy, scene, over).

## Game Mechanics (Brief)

**Act 1 — Oakhaven & Burzum Forest:** Name your warrior, visit the Blacksmith
for the *Blade of Grief* (25 dmg), then enter the *Burzum Forest* to defeat
the *Raider Scout* and claim the *Turbo Death Rune* (+1 potion).

**Act 2 — The Road:** Take the road east to the *Trading Post* where *Kessa Vane*
offers alliance. Clear *Ruins* (cultists) and *Ambush* (bandits), earn
*learned_plan* and *cleared_ambush* flags. Visit the Trading Post to recruit
Kessa (*recruited_ally*). Push through the *Mountain Pass* to defeat the
*Bandit Captain* and claim the *Atlantean Sword* (40 dmg).

**Act 3 — The Fortress:** Enter the *Fortress Gate*, defeat the *High Priest's Guard*
in the corridor, auto-enter the *Throne Room* to face the *High Priest of Doom*.
With the *Turbo Death Rune*, unleash **TURBO DEATH** (randomized 90–130 damage)
to finish the fight.

**Items & Flags:** Weapons (`Rusty Spoon` → `Blade of Grief` → `Atlantean Sword`),
consumable potions (heal 40 HP), flags track progression (`avenged_raider`,
`has_finisher_item`, `learned_plan`, `cleared_ambush`, `recruited_ally`,
`defeated_captain`). The *Turbo Death Rune* flag (`has_finisher_item`) enables
the *Turbo Death* finisher (90–130 dmg) in boss fights.