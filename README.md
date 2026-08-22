# Turbo Death Warrior - API

Backend for the *Turbo Death Warrior* terminal adventure — an API-only
service that powers the game. Fight a Caffeinated Orc, loot the Turbo
Crystal, and take back the realm's Wi-Fi router from the Mega-Goblin King.

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

The test suite covers 32 cases across initialization, name submission, town
actions, cave entrance, combat mechanics, orc/boss defeat, game over, restart,
state serialization, constants, and payload structure.

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
│   └── test_game_engine.py      # 32 unit tests (pytest)
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