# Turbo Death Warrior - Web Edition

A browser front end for the *Turbo Death Warrior* terminal adventure.
Fight a Caffeinated Orc, loot the Turbo Crystal, and take back the realm's
Wi-Fi router from the Mega-Goblin King - now with HP bars and zero typing
`1` into a console.

Standard library only. No dependencies, no install step.

## Quick Start

```sh
make            # starts the server on http://localhost:8001
```

or without make:

```sh
python3 server.py
```

Then open <http://localhost:8001> in your browser. Stop with `Ctrl+C`.

## Make Targets

| Target   | Description                                          |
|----------|------------------------------------------------------|
| `run`    | Start the web server (default target)                |
| `check`  | Byte-compile the Python sources as a sanity check    |
| `clean`  | Remove caches (`__pycache__`, `.pyc`)                |

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

## How to Play

1. Enter your name when prompted.
2. In **Oakhaven Village**, visit the Blacksmith first - the Rusty Spork
   will not get it done.
3. Head **north** to the Whispering Forest and defeat the Caffeinated Orc
   to obtain the Turbo Crystal (+1 potion).
4. At the **Doom Caves Entrance**, enter and face the Mega-Goblin King.
5. Unleash the **Turbo Death Strike** while you hold the crystal.
6. If things go badly, drink potions - attacking and healing are your only
   other options. Death is permanent until you click *Try Again*.

You can farm the forest for extra crystals/potions before the boss, just
like in the CLI version.

## Project Structure

```
turbo_death_warrior/
├── turbo_death_warrior.py   # original CLI game (still playable)
├── game_engine.py           # I/O-free rewrite of the game logic
├── server.py                # stdlib HTTP server on port 8001
├── web/
│   └── index.html           # single-file frontend (HTML/CSS/JS)
├── Makefile
├── requirements.txt         # intentionally empty: stdlib only
├── .env                     # local config (not committed)
├── .env.example             # config template
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
