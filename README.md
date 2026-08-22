# Turbo Death Warrior - Web Edition

A browser front end for the *Turbo Death Warrior* terminal adventure.
Fight a Caffeinated Orc, loot the Turbo Crystal, and take back the realm's
Wi-Fi router from the Mega-Goblin King - now with a retro amber CRT terminal
aesthetic and fully keyboard-driven controls.

Standard library only. No dependencies for the game itself; only `pytest` for
the test suite.

## Quick Start

```sh
make            # starts the server on http://localhost:8001
```

or without make:

```sh
python3 -m turbo_death_warrior.server
```

Then open <http://localhost:8001> in your browser. Stop with `Ctrl+C`.

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
│       └── server.py            # stdlib HTTP server on port 8001
├── test/
│   └── test_game_engine.py      # 32 unit tests (pytest)
├── web/
│   └── index.html               # single-file frontend (HTML/CSS/JS)
├── Makefile
├── requirements.txt             # pytest for test suite
├── .env                         # local config (not committed)
├── .env.example                 # config template
└── README.md
```

## API Overview

All endpoints speak JSON. The server holds one `Game` per ID in memory.

| Method | Path                        | Purpose                        |
|--------|-----------------------------|--------------------------------|
| GET    | `/`                         | Serve the frontend             |
| POST   | `/api/game`                 | Create a game, returns `game_id` |
| POST   | `/api/game/<id>/name`       | Submit player name             |
| POST   | `/api/game/<id>/action`     | Perform a choice (`{"id": "attack"}`) |

Each response contains `messages`, `options`, optional `text_input`,
and a `state` snapshot (player, enemy, scene, over).