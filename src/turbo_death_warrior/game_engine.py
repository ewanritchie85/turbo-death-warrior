"""Core game logic for Turbo Death Warrior.

A pure, I/O-free rewrite of turbo_death_warrior.py. The engine is
turn-based and every public call returns a JSON-ready dict, so it can be
driven by any front end (see server.py).
"""

import random

HEAL_AMOUNT = 40

ENEMY_TEMPLATES = {
    "raider_scout": {
        "key": "raider_scout",
        "name": "Raider Scout",
        "hp": 40,
        "dmg": 12,
        "drops": {"potions": 1, "flags": ["has_finisher_item", "avenged_raider"]},
        "win_messages": [
            "Searching the Raider Scout's body, you find a strange, faintly warm rune.",
            "OBTAINED: the Turbo Death Rune.",
            "You also find a potion among his gear.",
        ],
        "goto": "town",
    },
    "cultist": {
        "key": "cultist",
        "name": "Noothgrush Cultist",
        "hp": 35,
        "dmg": 13,
        "drops": {"flags": ["learned_plan"]},
        "win_messages": [
            "Whatever they were chanting for, it's over now.",
            "One of them was carrying maps — The High Priest's patrol routes,",
            "and something about a 'binding' at the fortress.",
        ],
        "goto": "road",
    },
    "bandit": {
        "key": "bandit",
        "name": "Bandit",
        "hp": 28,
        "dmg": 10,
        "drops": {"potions": 1, "flags": ["cleared_ambush"]},
        "win_messages": [
            "Not every fight out here means something. This",
            "one didn't. Still counts.",
        ],
        "goto": "road",
    },
    "bandit_captain": {
        "key": "bandit_captain",
        "name": "Bandit Captain",
        "hp": 60,
        "dmg": 15,
        "drops": {"potions": 2, "flags": ["defeated_captain"]},
        "win_messages": [
            "The Captain falls. Kessa doesn't gloat — that's",
            "how you know it mattered to her.",
            "Ahead, through the pass, The High Priest's fortress finally",
            "comes into view.",
            "",
            "You take the Atlantean Sword — heavier than your own,",
            "balanced like it's used to winning.",
        ],
        "goto": "fortress_gate",
    },
    "warlord_guard": {
        "key": "warlord_guard",
        "name": "The High Priest's Guard",
        "hp": 45,
        "dmg": 14,
        "drops": {},
        "win_messages": [
            "The corridor beyond is silent. Whatever's waiting",
            "for you, it already knows you're here.",
        ],
        "goto": "throne_room",
    },
    "high_priest": {
        "key": "high_priest",
        "name": "The High Priest of Doom",
        "hp": 150,
        "dmg": 22,
        "drops": {},
        "win_messages": [
            "The High Priest falls. Whatever he was — warlord,",
            "something worse — it ends here.",
            "You didn't come for the fortress, or the throne.",
            "You came for this. It's done.",
            "Thanks for playing.",
        ],
        "ending": "victory",
    },
}

WEAPONS = {
    "starting": {"name": "Rusty Spoon", "damage": 10},
    "blacksmith_upgrade": {
        "name": "Blade of Grief",
        "damage": 25,
        "obtained_from": "blacksmith",
        "flavor": [
            "'You call yourself the Turbo Death Warrior? With that spoon? Take this.'",
            "He tosses you a heavy blade.",
            "OBTAINED: Blade of Grief! (Damage increased)",
        ],
    },
    "captains_blade": {
        "name": "Atlantean Sword",
        "damage": 40,
        "obtained_from": "bandit_captain",
        "flavor": [
            "You take the Atlantean Sword — heavier than your own,",
            "balanced like it's used to winning.",
        ],
    },
}

LOCATIONS = {
    "town": {
        "on_enter": [
            "",
            "=== OAKHAVEN VILLAGE ===",
            "Oakhaven is rebuilding, slowly. Ash still clings to the thatch.",
            "To the north lies the Burzum Forest.",
            "To the east is the Blacksmith.",
        ],
        "options": [
            {"id": "go_forest", "label": "Go North to the Forest", "goto": "forest", "hide_if": "avenged_raider"},
            {"id": "visit_blacksmith", "label": "Visit Blacksmith", "action": "_blacksmith"},
            {"id": "check_stats", "label": "Check Stats", "action": "_stats"},
            {"id": "depart_road", "label": "Take the road east", "goto": "road", "show_if": "avenged_raider"},
        ],
    },
    "forest": {
        "on_enter": [
            "",
            "=== BURZUM FOREST ===",
            "The trees are thick and block out the sun.",
            "Smoke still hangs faintly between the trees here. One of the warband's scouts never made it back to report — you can guess why.",
            "",
            "--- COMBAT INITIATED: RAIDER SCOUT ---",
        ],
        "auto_encounter": "raider_scout",
        "options": [],
    },
    "road": {
        "on_enter": [
            "",
            "=== THE ROAD ===",
            "The road east is empty and too quiet. Somewhere ahead, Kessa Vane runs",
            "the last honest trading post before The High Priest's territory begins — if",
            "'honest' is the word.",
        ],
        "options": [
            {"id": "explore_ruins", "label": "Explore the ruins off the road", "hide_if": "learned_plan", "encounter": "cultist", "messages": [
                "",
                "=== THE RUINS ===",
                "Cultists in ash-grey robes are chanting over something in the rubble.",
                "They don't stop when they see you.",
            ]},
            {"id": "clear_ambush", "label": "Investigate the wrecked cart", "hide_if": "cleared_ambush", "encounter": "bandit", "messages": [
                "",
                "=== AMBUSH ===",
                "A bandit steps out from behind a wrecked cart. Not everyone out here",
                "serves The High Priest — some just took advantage of the chaos.",
            ]},
            {"id": "visit_trading_post", "label": "Visit the trading post", "show_if": "learned_plan", "hide_if": "recruited_ally", "action": "_trading_post"},
            {"id": "confront_the_pass", "label": "Push on through the mountain pass", "show_if": "recruited_ally", "encounter": "bandit_captain", "messages": [
                "",
                "=== THE PASS ===",
                "The pass is the only way through — and the Captain guarding it",
                "clearly enjoys that fact.",
            ]},
        ],
    },
    "fortress_gate": {
        "on_enter": [
            "",
            "=== THE FORTRESS GATE ===",
            "The gates are unguarded — which is worse than if they weren't.",
            "The High Priest knows you're coming.",
        ],
        "options": [
            {"id": "enter_fortress", "label": "Enter the fortress", "encounter": "warlord_guard", "messages": [
                "",
                "=== THE CORRIDOR ===",
                "A single guard stands between you and the throne room.",
                "He doesn't look worried. That's about to change.",
                "",
                "--- COMBAT INITIATED: THE HIGH PRIEST'S GUARD ---",
            ]},
        ],
    },
    "throne_room": {
        "on_enter": [
            "",
            "=== THE THRONE ROOM ===",
            "The High Priest doesn't rise from the throne. \"Oakhaven's last son,\"",
            "he says, almost gently. \"Come to die where your father",
            "should have run.\"",
            "",
            "--- COMBAT INITIATED: THE HIGH PRIEST OF DOOM ---",
        ],
        "auto_encounter": "high_priest",
        "options": [],
    },
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
            "potions": 2,
        }
        self._weapon_id = "starting"
        self._apply_weapon(self._weapon_id)
        self.flags = set()
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
                "You wake to smoke and silence.",
                "",
                "Oakhaven burned in the night. The warband came without warning, took",
                "what they wanted, and left the rest in ash — including the man who",
                "raised you.",
                "",
                "You buried what you could. Then you picked up whatever weapon was left",
                "standing, and went looking for the one who gave the order: The High Priest of Doom,",
                "who they say commands both soldiers and something worse.",
                "",
                "This is not a rescue. It's a reckoning.",
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
            f"Go forth, {name}! Oakhaven awaits — what's left of it.",
        ]
        return self._goto("town", msgs)

    def act(self, action_id):
        if self.over:
            if action_id == "restart":
                self.reset()
                return self.start()
            # Game has ended but action is not restart - give a helpful response
            if self.scene == "victory":
                label = "Play Again"
            else:  # game_over
                label = "Try Again"
            return self._payload(
                ["The game has ended. Choose Restart to play again."],
                [{"id": "restart", "label": label}],
            )

        if self.scene == "combat":
            handler = {
                "attack": lambda: self._combat_turn("attack"),
                "heal": lambda: self._combat_turn("heal"),
                "strike": lambda: self._combat_turn("strike"),
            }.get(action_id)
            if handler is None:
                return self._payload(["Invalid choice."], self._combat_options())
            return handler()

        option = self._find_option(action_id)
        if option is None:
            return self._payload(["Invalid choice."], self._scene_options())

        return self._dispatch_option(option)

    # ------------------------------------------------------------------
    # Location navigation (data-driven)

    def _scene_options(self):
        if self.scene == "combat":
            return self._combat_options()
        loc = LOCATIONS.get(self.scene)
        if not loc:
            return []
        options = []
        for opt in loc.get("options", []):
            if "show_if" in opt and opt["show_if"] not in self.flags:
                continue
            if "hide_if" in opt and opt["hide_if"] in self.flags:
                continue
            options.append({"id": opt["id"], "label": opt["label"]})
        return options

    def _find_option(self, action_id):
        loc = LOCATIONS.get(self.scene)
        if not loc:
            return None
        for opt in loc.get("options", []):
            if opt["id"] == action_id:
                if "show_if" in opt and opt["show_if"] not in self.flags:
                    return None
                if "hide_if" in opt and opt["hide_if"] in self.flags:
                    return None
                return opt
        return None

    def _dispatch_option(self, option):
        if "action" in option:
            method = getattr(self, option["action"])
            return method()
        if "goto" in option:
            return self._goto(option["goto"], option.get("messages"))
        if "encounter" in option:
            msgs = option.get("messages", [])
            self._start_combat(option["encounter"])
            return self._payload(msgs, self._combat_options())
        return self._payload(["Invalid choice."], self._scene_options())

    def _goto(self, location_id, extra_msgs=None):
        loc = LOCATIONS.get(location_id)
        if not loc:
            return self._payload(["Invalid location."], self._scene_options())

        self.scene = location_id
        msgs = list(extra_msgs) if extra_msgs else []
        msgs.extend(loc.get("on_enter", []))

        if "auto_encounter" in loc:
            self._start_combat(loc["auto_encounter"])
            return self._payload(msgs, self._combat_options())

        return self._payload(msgs, self._scene_options())

    def _apply_weapon(self, weapon_id):
        """Apply a weapon by ID, updating internal tracking and player dict."""
        weapon = WEAPONS[weapon_id]
        self._weapon_id = weapon_id
        self.player["weapon"] = weapon["name"]
        self.player["damage"] = weapon["damage"]

    # ------------------------------------------------------------------
    # Location-specific actions (kept as-is)

    def _blacksmith(self):
        msgs = [
            "",
            "=== THE BLACKSMITH ===",
            "The burly blacksmith scowls at you.",
        ]

        # Find the first blacksmith-obtainable weapon we don't already have
        next_weapon = None
        for w_id, w_data in WEAPONS.items():
            if w_data.get("obtained_from") == "blacksmith" and w_id != self._weapon_id:
                next_weapon = (w_id, w_data)
                break

        if next_weapon:
            w_id, w_data = next_weapon
            msgs.extend(w_data["flavor"])
            self._apply_weapon(w_id)
        else:
            msgs.append("'I already gave you my best weapon. Go kill something.'")

        return self._goto("town", msgs)

    def _stats(self):
        p = self.player
        msgs = [
            "",
            "--- YOUR STATS ---",
            f"Name: {p['name']}",
            f"HP: {p['hp']}/{p['max_hp']}",
            f"Weapon: {p['weapon']} (Damage: ~{p['damage']})",
            f"Potions: {p['potions']}",
            f"Turbo Death Rune: {'Yes' if 'has_finisher_item' in self.flags else 'No'}",
        ]
        return self._goto("town", msgs)

    def _trading_post(self):
        msgs = [
            "",
            "Kessa Vane doesn't look up from sharpening a knife that's",
            "already sharp enough.",
            "",
            "\"You're the one from Oakhaven. Heard about it.\" A pause.",
            "\"Heard you're going after The High Priest, too. Alone. With that.\"",
            "(she nods at your weapon) \"Bold. Stupid. Bold.\"",
            "",
            "She stands. \"I've got my own reasons to want him dead. Try",
            "not to get me killed before I get the chance.\"",
        ]
        self.flags.add("recruited_ally")
        return self._goto("road", msgs)

    # ------------------------------------------------------------------
    # Combat

    def _start_combat(self, key):
        tpl = ENEMY_TEMPLATES[key]
        self.enemy = dict(tpl, max_hp=tpl["hp"])
        self.boss_fight = key == "high_priest"
        self.scene = "combat"

    def _combat_options(self):
        options = [
            {"id": "attack", "label": "Attack"},
            {"id": "heal", "label": f"Heal - Drink Potion ({self.player['potions']} left)"},
        ]
        if self.boss_fight and "has_finisher_item" in self.flags:
            options.append(
                {"id": "strike", "label": "USE TURBO DEATH (Requires Turbo Death Rune)"}
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
            if self.boss_fight and "has_finisher_item" in self.flags:
                dmg = random.randint(90, 130)
                msgs.append("You channel the strange heat of the Turbo Death Rune...")
                e["hp"] -= dmg
                self.flags.discard("has_finisher_item")
                msgs.append(
                    f"BOOOOOOM! You unleash TURBO DEATH for {dmg} damage!"
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
        tpl = ENEMY_TEMPLATES[key]

        msgs.append(f"\nYou defeated the {name}!")

        drops = tpl.get("drops", {})
        if "potions" in drops:
            self.player["potions"] += drops["potions"]
        for flag in drops.get("flags", []):
            self.flags.add(flag)

        msgs.extend(tpl.get("win_messages", []))

        # Bandit Captain grants Atlantean Sword weapon
        if key == "bandit_captain":
            self._apply_weapon("captains_blade")

        self.boss_fight = False

        if "goto" in tpl:
            self.enemy = None
            return self._goto(tpl["goto"], msgs)

        if "ending" in tpl:
            self.over = True
            self.scene = tpl["ending"]
            return self._payload(msgs, [{"id": "restart", "label": "Play Again"}])

        return self._payload(msgs, self._scene_options())

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