"""Core game logic for Turbo Death Warrior.

A pure, I/O-free rewrite of turbo_death_warrior.py. The engine is
turn-based and every public call returns a JSON-ready dict, so it can be
driven by any front end (see server.py).
"""

import random

HEAL_AMOUNT = 40
STRIKE_DAMAGE = 150

ENEMY_TEMPLATES = {
    "orc": {"key": "orc", "name": "Super Orc", "hp": 40, "dmg": 12},
    "boss": {"key": "boss", "name": "Mega-Goblin King", "hp": 120, "dmg": 20},
}


class Game:
    """A single playthrough. Instances are not thread-safe."""

    def __init__(self):
        self.player = {}
        self.enemy = None
        self.boss_fight = False
        self.scene = "name_prompt"
        self.over = False
        self.reset()

    def reset(self):
        self.player = {
            "name": "",
            "hp": 100,
            "max_hp": 100,
            "weapon": "Rusty Spork",
            "damage": 10,
            "potions": 2,
            "has_turbo_crystal": False,
        }
        self.enemy = None
        self.boss_fight = False
        self.scene = "name_prompt"
        self.over = False

    # ------------------------------------------------------------------
    # Public API

    def start(self):
        return self._payload(
            [
                "=" * 40,
                "        TURBO DEATH WARRIOR",
                "=" * 40,
                "Awake, Warrior. The world is in peril.",
                "The Mega-Goblin King has stolen the realm's Wi-Fi router.",
                "You must retrieve it.",
            ],
            text_input="What is your name, warrior?",
        )

    def submit_name(self, raw_name):
        name = (raw_name or "").strip()
        if not name:
            return self._payload(
                ["Every hero needs a name! Try again."],
                text_input="What is your name, warrior?",
            )
        self.player["name"] = name
        msgs = [
            f"Very well. From this day forth, you shall be known as {name}!",
            f"Go forth, {name}! Oakhaven Village awaits.",
        ]
        return self._to_town(msgs)

    def act(self, action_id):
        if self.over:
            if action_id == "restart":
                self.reset()
                return self.start()
            return self._payload([])

        scene_handlers = {
            "town": {
                "go_forest": self._enter_forest,
                "visit_blacksmith": self._blacksmith,
                "check_stats": self._stats,
            },
            "cave_entrance": {
                "enter_caves": self._enter_caves,
                "flee_town": self._flee_town,
            },
            "combat": {
                "attack": lambda: self._combat_turn("attack"),
                "heal": lambda: self._combat_turn("heal"),
                "strike": lambda: self._combat_turn("strike"),
            },
        }
        handler = scene_handlers.get(self.scene, {}).get(action_id)
        if handler is None:
            return self._payload(["Invalid choice."], self._scene_options())
        return handler()

    # ------------------------------------------------------------------
    # Locations

    def _scene_options(self):
        if self.scene == "town":
            return [
                {"id": "go_forest", "label": "Go North to the Forest"},
                {"id": "visit_blacksmith", "label": "Visit Blacksmith"},
                {"id": "check_stats", "label": "Check Stats"},
            ]
        if self.scene == "cave_entrance":
            return [
                {"id": "enter_caves", "label": "Enter the Doom Caves (Boss Fight)"},
                {"id": "flee_town", "label": "Run back to town"},
            ]
        if self.scene == "combat":
            return self._combat_options()
        return []

    def _to_town(self, msgs):
        self.scene = "town"
        msgs += [
            "",
            "=== OAKHAVEN VILLAGE ===",
            "You are in a muddy village square. To the north lies the Whispering Forest.",
            "To the east is the Blacksmith.",
        ]
        return self._payload(msgs, self._scene_options())

    def _blacksmith(self):
        msgs = [
            "",
            "=== THE BLACKSMITH ===",
            "The burly blacksmith scowls at you.",
        ]
        if self.player["weapon"] == "Rusty Spork":
            msgs += [
                "'You call yourself the Turbo Death Warrior? With that spork? Take this.'",
                "He tosses you a heavy blade.",
                "OBTAINED: Chainsaw-Sword! (Damage increased)",
            ]
            self.player["weapon"] = "Chainsaw-Sword"
            self.player["damage"] = 25
        else:
            msgs.append("'I already gave you my best weapon. Go kill something.'")
        return self._to_town(msgs)

    def _stats(self):
        p = self.player
        msgs = [
            "",
            "--- YOUR STATS ---",
            f"Name: {p['name']}",
            f"HP: {p['hp']}/{p['max_hp']}",
            f"Weapon: {p['weapon']} (Damage: ~{p['damage']})",
            f"Potions: {p['potions']}",
            f"Turbo Crystal: {'Yes' if p['has_turbo_crystal'] else 'No'}",
        ]
        return self._to_town(msgs)

    def _enter_forest(self):
        msgs = [
            "",
            "=== WHISPERING FOREST ===",
            "The trees are thick and block out the sun.",
            "Suddenly, a Super Orc jumps out from behind a bush!",
            "",
            "--- COMBAT INITIATED: SUPER ORC ---",
        ]
        self._start_combat("orc")
        return self._payload(msgs, self._combat_options())

    def _enter_caves(self):
        msgs = [
            "",
            "=== THE THRONE OF DOOM ===",
            "You step into a massive cavern. On a throne of skulls sits the MEGA-GOBLIN KING.",
            "'So, the so-called Turbo Death Warrior arrives,' he sneers.",
            "",
            "--- COMBAT INITIATED: MEGA-GOBLIN KING ---",
        ]
        self._start_combat("boss")
        return self._payload(msgs, self._combat_options())

    def _flee_town(self):
        return self._to_town(["You sprint back to the safety of Oakhaven Village."])

    # ------------------------------------------------------------------
    # Combat

    def _start_combat(self, key):
        tpl = ENEMY_TEMPLATES[key]
        self.enemy = dict(tpl, max_hp=tpl["hp"])
        self.boss_fight = key == "boss"
        self.scene = "combat"

    def _combat_options(self):
        options = [
            {"id": "attack", "label": "Attack"},
            {"id": "heal", "label": f"Heal - Drink Potion ({self.player['potions']} left)"},
        ]
        if self.boss_fight and self.player["has_turbo_crystal"]:
            options.append(
                {"id": "strike", "label": "USE TURBO DEATH STRIKE (Requires Crystal)"}
            )
        return options

    def _combat_turn(self, action):
        p = self.player
        e = self.enemy
        msgs = []

        if action == "attack":
            dmg = random.randint(p["damage"] - 3, p["damage"] + 5)
            e["hp"] -= dmg
            msgs.append(f"You slash with your {p['weapon']} for {dmg} damage!")
        elif action == "heal":
            if p["potions"] > 0:
                p["hp"] = min(p["max_hp"], p["hp"] + HEAL_AMOUNT)
                p["potions"] -= 1
                msgs.append(f"You chug a potion and recover {HEAL_AMOUNT} HP.")
            else:
                msgs.append(
                    "You reach for a potion, but your flask is empty! You wasted your turn!"
                )
        elif action == "strike":
            if self.boss_fight and p["has_turbo_crystal"]:
                msgs.append("You channel the unstable energy of the Turbo Crystal...")
                e["hp"] -= STRIKE_DAMAGE
                p["has_turbo_crystal"] = False
                msgs.append(
                    f"BOOOOOOM! You unleash the TURBO DEATH STRIKE for {STRIKE_DAMAGE} damage!"
                )
            else:
                msgs.append("You wave your hands mysteriously. Nothing happens!")
        else:
            msgs.append("Invalid choice. You stumble and miss your turn!")

        if e["hp"] <= 0:
            e["hp"] = 0
            return self._win_fight(msgs)

        e_dmg = random.randint(e["dmg"] - 2, e["dmg"] + 4)
        p["hp"] -= e_dmg
        msgs.append(f"{e['name']} strikes you for {e_dmg} damage!")

        if p["hp"] <= 0:
            p["hp"] = 0
            return self._game_over(msgs)

        return self._payload(msgs, self._combat_options())

    def _win_fight(self, msgs):
        key = self.enemy["key"]
        name = self.enemy["name"]
        msgs.append(f"\nYou defeated the {name}!")

        if key == "orc":
            self.player["has_turbo_crystal"] = True
            self.player["potions"] += 1
            msgs += [
                "Searching the Orc's body, you find a weird glowing rock.",
                "OBTAINED: Turbo Crystal!",
                "You also found a potion!",
                "",
                "=== DOOM CAVES ENTRANCE ===",
                "A dark, gaping hole in the mountain lies before you. "
                "It smells like sulfur and goblin sweat.",
            ]
            self.enemy = None
            self.boss_fight = False
            self.scene = "cave_entrance"
            return self._payload(msgs, self._scene_options())

        self.over = True
        self.scene = "victory"
        msgs += [
            "*** YOU HAVE DEFEATED THE MEGA-GOBLIN KING! ***",
            "The realm is safe. You truly are the TURBO DEATH WARRIOR.",
            "Thanks for playing!",
        ]
        return self._payload(msgs, [{"id": "restart", "label": "Play Again"}])

    def _game_over(self, msgs):
        self.over = True
        self.scene = "game_over"
        msgs += [
            "\n*** YOU HAVE DIED. The realm is doomed. ***",
            "GAME OVER",
        ]
        return self._payload(msgs, [{"id": "restart", "label": "Try Again"}])

    # ------------------------------------------------------------------
    # Serialization

    def _state(self):
        return {
            "scene": self.scene,
            "over": self.over,
            "player": dict(self.player),
            "enemy": dict(self.enemy) if self.enemy else None,
        }

    def _payload(self, messages, options=None, text_input=None):
        return {
            "messages": messages,
            "options": options or [],
            "text_input": text_input,
            "state": self._state(),
        }
