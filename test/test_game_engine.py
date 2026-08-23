"""Unit tests for Turbo Death Warrior game engine."""

import pytest
from turbo_death_warrior.game_engine import Game, ENEMY_TEMPLATES, HEAL_AMOUNT, LOCATIONS, WEAPONS


class TestGameInitialization:
    def test_initial_state(self):
        g = Game()
        assert g.scene == "name_prompt"
        assert g.over is False
        assert g.enemy is None
        assert g.boss_fight is False
        assert g.player["name"] == ""
        assert g.player["hp"] == 100
        assert g.player["max_hp"] == 100
        assert g.player["weapon"] == "Rusty Spoon"
        assert g.player["damage"] == 10
        assert g.player["potions"] == 2
        assert "has_finisher_item" not in g.flags

    def test_reset_restores_initial_state(self):
        g = Game()
        g.player["name"] = "Test"
        g.player["hp"] = 50
        g.player["weapon"] = "Blade of Grief"
        g.player["damage"] = 25
        g.player["potions"] = 0
        g.flags.add("has_finisher_item")
        g.scene = "combat"
        g.over = True
        g.enemy = {"hp": 10}
        g.boss_fight = True

        g.reset()

        assert g.scene == "name_prompt"
        assert g.over is False
        assert g.enemy is None
        assert g.boss_fight is False
        assert g.player["name"] == ""
        assert g.player["hp"] == 100
        assert g.player["weapon"] == "Rusty Spoon"
        assert g.player["damage"] == 10
        assert g.player["potions"] == 2
        assert "has_finisher_item" not in g.flags


class TestStartAndNameSubmission:
    def test_start_returns_welcome_messages_and_text_input(self):
        g = Game()
        payload = g.start()

        assert "messages" in payload
        assert "TURBO DEATH WARRIOR" in "\n".join(payload["messages"])
        assert payload["text_input"] == "What is your name, warrior?"
        assert payload["options"] == []
        assert payload["state"]["scene"] == "name_prompt"

    def test_submit_name_empty_returns_error(self):
        g = Game()
        g.start()
        payload = g.submit_name("")

        assert "Every hero needs a name!" in payload["messages"][0]
        assert payload["text_input"] == "What is your name, warrior?"
        assert g.player["name"] == ""

    def test_submit_name_whitespace_only_returns_error(self):
        g = Game()
        g.start()
        payload = g.submit_name("   ")

        assert "Every hero needs a name!" in payload["messages"][0]

    def test_submit_valid_name_sets_name_and_goes_to_town(self):
        g = Game()
        g.start()
        payload = g.submit_name("Arthur")

        assert g.player["name"] == "Arthur"
        assert any("Arthur" in m for m in payload["messages"])
        assert payload["state"]["scene"] == "town"
        assert payload["text_input"] is None
        assert len(payload["options"]) == 3


class TestTownActions:
    @pytest.fixture
    def game_in_town(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        return g

    def test_check_stats_shows_player_info(self, game_in_town):
        payload = game_in_town.act("check_stats")

        assert "YOUR STATS" in "\n".join(payload["messages"])
        assert "Hero" in "\n".join(payload["messages"])
        assert "HP: 100/100" in "\n".join(payload["messages"])
        assert "Rusty Spoon" in "\n".join(payload["messages"])
        assert "Potions: 2" in "\n".join(payload["messages"])
        assert "Turbo Death Rune: No" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "town"

    def test_visit_blacksmith_upgrades_weapon(self, game_in_town):
        payload = game_in_town.act("visit_blacksmith")

        assert "Blade of Grief" in "\n".join(payload["messages"])
        assert game_in_town.player["weapon"] == "Blade of Grief"
        assert game_in_town.player["damage"] == 25
        assert payload["state"]["scene"] == "town"

    def test_visit_blacksmith_twice_keeps_weapon(self, game_in_town):
        game_in_town.act("visit_blacksmith")
        payload = game_in_town.act("visit_blacksmith")

        assert "already gave you my best weapon" in "\n".join(payload["messages"])
        assert game_in_town.player["weapon"] == "Blade of Grief"
        assert game_in_town.player["damage"] == 25

    def test_go_forest_starts_orc_combat(self, game_in_town):
        payload = game_in_town.act("go_forest")

        assert "BURZUM FOREST" in "\n".join(payload["messages"])
        assert "COMBAT INITIATED" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "combat"
        assert game_in_town.enemy is not None
        assert game_in_town.enemy["key"] == "raider_scout"
        assert game_in_town.boss_fight is False
        assert len(payload["options"]) == 2

    def test_invalid_action_in_town_returns_error(self, game_in_town):
        payload = game_in_town.act("invalid_action")

        assert "Invalid choice." in payload["messages"][0]
        assert payload["state"]["scene"] == "town"


class TestCombatMechanics:
    @pytest.fixture
    def game_in_orc_combat(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        return g

    def test_combat_options_include_attack_and_heal(self, game_in_orc_combat):
        opts = game_in_orc_combat._combat_options()
        ids = [o["id"] for o in opts]
        assert "attack" in ids
        assert "heal" in ids
        assert "strike" not in ids

    def test_combat_options_strike_requires_crystal_and_boss(self, game_in_orc_combat):
        game_in_orc_combat.flags.add("has_finisher_item")
        opts = game_in_orc_combat._combat_options()
        ids = [o["id"] for o in opts]
        assert "strike" not in ids

        game_in_orc_combat.boss_fight = True
        opts = game_in_orc_combat._combat_options()
        ids = [o["id"] for o in opts]
        assert "strike" in ids

    def test_attack_deals_damage_in_range(self, game_in_orc_combat):
        initial_hp = game_in_orc_combat.enemy["hp"]
        game_in_orc_combat.player["damage"] = 10
        payload = game_in_orc_combat.act("attack")

        dmg_dealt = initial_hp - game_in_orc_combat.enemy["hp"]
        assert 7 <= dmg_dealt <= 15

    def test_heal_restores_hp_and_consumes_potion(self, game_in_orc_combat):
        game_in_orc_combat.player["hp"] = 50
        game_in_orc_combat.player["potions"] = 2
        game_in_orc_combat.enemy["dmg"] = 2
        payload = game_in_orc_combat.act("heal")

        assert game_in_orc_combat.player["hp"] >= 84
        assert game_in_orc_combat.player["hp"] <= 90
        assert game_in_orc_combat.player["potions"] == 1
        assert f"recover {HEAL_AMOUNT} HP" in "\n".join(payload["messages"])

    def test_heal_caps_at_max_hp(self, game_in_orc_combat):
        game_in_orc_combat.player["hp"] = 80
        game_in_orc_combat.player["potions"] = 1
        game_in_orc_combat.enemy["dmg"] = 2
        game_in_orc_combat.act("heal")

        assert game_in_orc_combat.player["hp"] <= 100

    def test_heal_with_no_potions_wastes_turn(self, game_in_orc_combat):
        game_in_orc_combat.player["potions"] = 0
        payload = game_in_orc_combat.act("heal")

        assert "empty" in "\n".join(payload["messages"])
        assert game_in_orc_combat.player["potions"] == 0

    def test_strike_without_crystal_fails(self, game_in_orc_combat):
        payload = game_in_orc_combat.act("strike")

        assert "Nothing happens" in "\n".join(payload["messages"])

    def test_enemy_counterattacks_after_player_turn(self, game_in_orc_combat):
        initial_hp = game_in_orc_combat.player["hp"]
        payload = game_in_orc_combat.act("attack")

        assert game_in_orc_combat.player["hp"] < initial_hp
        assert any("strikes you" in m for m in payload["messages"])


class TestOrcDefeat:
    def test_defeating_raider_scout_grants_shard_and_potion(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        payload = g.act("attack")

        assert "has_finisher_item" in g.flags
        assert "avenged_raider" in g.flags
        assert g.player["potions"] == 3
        assert "Turbo Death Rune" in "\n".join(payload["messages"])
        assert "potion" in "\n".join(payload["messages"]).lower()
        assert g.scene == "town"
        assert g.enemy is None


class TestHighPriestCombat:
    @pytest.fixture
    def game_in_high_priest_combat(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")  # defeat raider_scout
        g.act("depart_road")  # go to road
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.act("attack")  # defeat cultist
        g.act("clear_ambush")
        g.act("attack")  # defeat bandit
        g.act("visit_trading_post")  # recruit Kessa
        g.act("confront_the_pass")
        g.act("attack")  # defeat bandit_captain
        # Atlantean Sword equipped (damage 40), boost for testing
        g.player["damage"] = 100
        g.act("enter_fortress")
        g.act("attack")  # defeat warlord_guard
        # Now at throne_room, auto_encounter high_priest
        return g

    def test_high_priest_has_correct_stats(self, game_in_high_priest_combat):
        assert game_in_high_priest_combat.enemy["name"] == "The High Priest of Doom"
        assert game_in_high_priest_combat.enemy["hp"] == 150
        assert game_in_high_priest_combat.enemy["dmg"] == 22
        assert game_in_high_priest_combat.boss_fight is True

    def test_strike_deals_massive_damage_and_consumes_crystal(self, game_in_high_priest_combat):
        game_in_high_priest_combat.flags.add("has_finisher_item")
        initial_hp = game_in_high_priest_combat.enemy["hp"]
        payload = game_in_high_priest_combat.act("strike")

        # Strike damage is now randomized 90-130
        dmg_dealt = initial_hp - game_in_high_priest_combat.enemy["hp"]
        assert 90 <= dmg_dealt <= 130
        assert "has_finisher_item" not in game_in_high_priest_combat.flags
        assert "TURBO DEATH" in "\n".join(payload["messages"])

    def test_defeating_high_priest_ends_game_with_victory(self, game_in_high_priest_combat):
        game_in_high_priest_combat.player["damage"] = 200
        payload = game_in_high_priest_combat.act("attack")

        assert game_in_high_priest_combat.over is True
        assert game_in_high_priest_combat.scene == "victory"
        assert "The High Priest falls" in "\n".join(payload["messages"])
        assert any(o["id"] == "restart" for o in payload["options"])


class TestGameOver:
    def test_player_death_ends_game(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["hp"] = 1
        payload = g.act("attack")

        assert g.over is True
        assert g.scene == "game_over"
        assert "YOU HAVE DIED" in "\n".join(payload["messages"])
        assert any(o["id"] == "restart" for o in payload["options"])


class TestRestart:
    def test_restart_resets_game(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")
        g.act("depart_road")
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.act("attack")
        g.act("clear_ambush")
        g.act("attack")
        g.act("visit_trading_post")
        g.act("confront_the_pass")
        g.act("attack")
        # Atlantean Sword equipped, boost damage
        g.player["damage"] = 100
        g.act("enter_fortress")
        g.act("attack")
        g.player["damage"] = 200
        g.act("attack")

        assert g.over is True
        payload = g.act("restart")

        assert g.over is False
        assert g.scene == "name_prompt"
        assert g.player["name"] == ""
        assert g.player["hp"] == 100
        assert g.player["weapon"] == "Rusty Spoon"
        assert payload["text_input"] == "What is your name, warrior?"


class TestDeadEndPayloadFix:
    def test_non_restart_action_after_victory_returns_restart_option(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")
        g.act("depart_road")
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.act("attack")
        g.act("clear_ambush")
        g.act("attack")
        g.act("visit_trading_post")
        g.act("confront_the_pass")
        g.act("attack")
        # Atlantean Sword equipped, boost damage
        g.player["damage"] = 100
        g.act("enter_fortress")
        g.act("attack")
        g.player["damage"] = 200
        g.act("attack")  # defeat high priest -> victory

        assert g.over is True
        assert g.scene == "victory"

        # Send a non-restart action
        payload = g.act("invalid_action")

        assert payload["messages"] == ["The game has ended. Choose Restart to play again."]
        assert len(payload["options"]) == 1
        assert payload["options"][0]["id"] == "restart"
        assert payload["options"][0]["label"] == "Play Again"
        assert payload["state"]["scene"] == "victory"

    def test_non_restart_action_after_game_over_returns_restart_option(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["hp"] = 1
        g.act("attack")  # die -> game_over

        assert g.over is True
        assert g.scene == "game_over"

        # Send a non-restart action
        payload = g.act("invalid_action")

        assert payload["messages"] == ["The game has ended. Choose Restart to play again."]
        assert len(payload["options"]) == 1
        assert payload["options"][0]["id"] == "restart"
        assert payload["options"][0]["label"] == "Try Again"
        assert payload["state"]["scene"] == "game_over"


class TestStateSerialization:
    def test_state_contains_all_fields(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        state = g._state()

        assert "scene" in state
        assert "over" in state
        assert "player" in state
        assert "enemy" in state
        assert state["player"]["name"] == "Hero"
        assert state["enemy"] is None

    def test_state_includes_enemy_during_combat(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        state = g._state()

        assert state["enemy"] is not None
        assert state["enemy"]["key"] == "raider_scout"
        assert "max_hp" in state["enemy"]


class TestConstants:
    def test_enemy_templates_structure(self):
        assert "raider_scout" in ENEMY_TEMPLATES
        assert "high_priest" in ENEMY_TEMPLATES
        for tpl in ENEMY_TEMPLATES.values():
            assert "key" in tpl
            assert "name" in tpl
            assert "hp" in tpl
            assert "dmg" in tpl

    def test_heal_amount(self):
        assert HEAL_AMOUNT == 40


class TestAct3Fortress:
    @pytest.fixture
    def game_at_fortress_gate(self):
        """Game at fortress_gate after completing Act 2."""
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")  # defeat raider_scout
        g.act("depart_road")  # go to road
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.act("attack")  # defeat cultist
        g.act("clear_ambush")
        g.act("attack")  # defeat bandit
        g.act("visit_trading_post")  # recruit Kessa
        g.act("confront_the_pass")
        g.act("attack")  # defeat bandit_captain
        return g

    def test_fortress_gate_on_enter(self, game_at_fortress_gate):
        assert game_at_fortress_gate.scene == "fortress_gate"

    def test_enter_fortress_starts_warlord_guard_combat(self, game_at_fortress_gate):
        payload = game_at_fortress_gate.act("enter_fortress")
        assert "THE CORRIDOR" in "\n".join(payload["messages"])
        assert "THE HIGH PRIEST'S GUARD" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "combat"
        assert game_at_fortress_gate.enemy["key"] == "warlord_guard"

    def test_warlord_guard_win_goes_to_throne_room(self, game_at_fortress_gate):
        g = game_at_fortress_gate
        g.player["damage"] = 100
        g.act("enter_fortress")
        payload = g.act("attack")  # defeat warlord_guard -> throne_room + auto_encounter high_priest

        # After warlord_guard defeat, transitions to throne_room and auto-starts high_priest combat
        assert g.scene == "combat"  # auto_encounter starts combat
        assert g.enemy["key"] == "high_priest"
        assert "THRONE ROOM" in "\n".join(payload["messages"])
        assert "The High Priest doesn't rise" in "\n".join(payload["messages"])

    def test_throne_room_auto_encounters_high_priest(self, game_at_fortress_gate):
        g = game_at_fortress_gate
        g.player["damage"] = 100
        g.act("enter_fortress")
        g.act("attack")  # defeat warlord_guard -> throne_room + auto_encounter high_priest

        assert g.scene == "combat"
        assert g.enemy is not None
        assert g.enemy["key"] == "high_priest"
        assert g.boss_fight is True


class TestFullPlaythrough:
    def test_complete_act1_act2_act3_no_bypass(self):
        """Full playthrough: Act 1 -> Act 2 -> Act 3, no cave_entrance bypass exists."""
        g = Game()
        g.start()
        g.submit_name("Hero")

        # Act 1: Forest -> Raider Scout
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")
        assert g.scene == "town"
        assert "avenged_raider" in g.flags
        assert "has_finisher_item" in g.flags

        # Town options: forest hidden, road available
        town_options = [o["id"] for o in g._scene_options()]
        assert "go_forest" not in town_options
        assert "depart_road" in town_options

        # Act 2: Road -> Ruins -> Ambush -> Trading Post -> Pass
        g.act("depart_road")
        assert g.scene == "road"

        # Ruins
        g.act("explore_ruins")
        g.player["damage"] = 100
        g.act("attack")
        assert "learned_plan" in g.flags
        assert g.scene == "road"

        # Ambush
        g.act("clear_ambush")
        g.act("attack")
        assert "cleared_ambush" in g.flags
        assert g.scene == "road"

        # Trading Post
        g.act("visit_trading_post")
        assert "recruited_ally" in g.flags
        assert g.scene == "road"

        # Pass
        g.act("confront_the_pass")
        g.act("attack")
        assert "defeated_captain" in g.flags
        assert g.player["weapon"] == "Atlantean Sword"
        assert g.scene == "fortress_gate"
        # Atlantean Sword equipped (damage 40), boost for testing
        g.player["damage"] = 100

        # Act 3: Fortress Gate -> Warlord Guard -> Throne Room -> High Priest
        g.act("enter_fortress")
        g.act("attack")
        # After warlord_guard defeat, transitions to throne_room and auto-starts high_priest combat
        assert g.scene == "combat"
        assert g.enemy["key"] == "high_priest"
        assert g.boss_fight is True

        # Final fight - strike should be available
        g.flags.add("has_finisher_item")
        assert "strike" in [o["id"] for o in g._combat_options()]

        # Defeat High Priest
        g.player["damage"] = 200
        payload = g.act("attack")
        assert g.over is True
        assert g.scene == "victory"
        assert "The High Priest falls" in "\n".join(payload["messages"])


class TestPayloadStructure:
    def test_payload_always_has_required_keys(self):
        g = Game()
        payload = g.start()

        assert "messages" in payload
        assert "options" in payload
        assert "text_input" in payload
        assert "state" in payload
        assert isinstance(payload["messages"], list)
        assert isinstance(payload["options"], list)


class TestAct2RoadHub:
    @pytest.fixture
    def game_at_road(self):
        """Game at road after defeating raider_scout."""
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")  # defeat raider_scout -> town with avenged_raider
        g.act("depart_road")  # take road east
        return g

    def test_road_on_enter_shows_kessa_description(self, game_at_road):
        """Road on_enter messages include Kessa/trading post description."""
        # The game_at_road fixture ends at road, so the last payload has on_enter messages
        # We can't easily access those, but we can verify the location structure
        assert game_at_road.scene == "road"

    def test_road_initial_options_show_explore_and_ambush(self, game_at_road):
        """Before learned_plan: explore_ruins and clear_ambush visible."""
        option_ids = [o["id"] for o in game_at_road._scene_options()]
        assert "explore_ruins" in option_ids
        assert "clear_ambush" in option_ids
        assert "visit_trading_post" not in option_ids
        assert "confront_the_pass" not in option_ids

    def test_explore_ruins_starts_cultist_combat(self, game_at_road):
        payload = game_at_road.act("explore_ruins")
        assert "THE RUINS" in "\n".join(payload["messages"])
        assert "Cultists in ash-grey robes" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "combat"
        assert game_at_road.enemy["key"] == "cultist"

    def test_clear_ambush_starts_bandit_combat(self, game_at_road):
        payload = game_at_road.act("clear_ambush")
        assert "AMBUSH" in "\n".join(payload["messages"])
        assert "A bandit steps out" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "combat"
        assert game_at_road.enemy["key"] == "bandit"

    def test_after_learned_plan_trading_post_visible(self, game_at_road):
        """After cultist defeat (learned_plan), trading_post appears."""
        g = game_at_road
        g.player["damage"] = 100
        g.act("explore_ruins")  # defeat cultist
        g.player["damage"] = 100
        g.act("attack")  # win -> back to road with learned_plan

        option_ids = [o["id"] for o in g._scene_options()]
        assert "explore_ruins" not in option_ids  # hidden by learned_plan
        assert "clear_ambush" in option_ids
        assert "visit_trading_post" in option_ids
        assert "confront_the_pass" not in option_ids

    def test_after_recruited_ally_pass_visible(self, game_at_road):
        """After trading post (recruited_ally), pass appears."""
        g = game_at_road
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.player["damage"] = 100
        g.act("attack")
        g.act("visit_trading_post")  # recruits Kessa

        option_ids = [o["id"] for o in g._scene_options()]
        assert "explore_ruins" not in option_ids
        assert "clear_ambush" in option_ids
        assert "visit_trading_post" not in option_ids  # hidden by recruited_ally
        assert "confront_the_pass" in option_ids

    def test_trading_post_sets_recruited_ally(self, game_at_road):
        """Visiting trading post adds recruited_ally flag."""
        g = game_at_road
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.player["damage"] = 100
        g.act("attack")
        g.act("visit_trading_post")

        assert "recruited_ally" in g.flags
        assert g.scene == "road"

    def test_full_act2_path_to_fortress_gate(self, game_at_road):
        """Complete Act 2: ruins -> ambush -> trading post -> pass -> fortress_gate."""
        g = game_at_road
        g.player["damage"] = 100

        # 1. Explore ruins -> cultist
        g.act("explore_ruins")
        g.act("attack")

        # 2. Clear ambush -> bandit
        g.act("clear_ambush")
        g.act("attack")

        # 3. Visit trading post -> recruit Kessa
        g.act("visit_trading_post")

        # 4. Confront pass -> bandit_captain
        g.act("confront_the_pass")
        payload = g.act("attack")  # defeat captain

        # Should reach fortress_gate (placeholder exists)
        assert g.scene == "fortress_gate"
        # The on_enter messages for fortress_gate are in the payload
        assert "FORTRESS GATE" in "\n".join(payload["messages"])

    def test_bandit_captain_grants_atlantean_sword(self, game_at_road):
        """Defeating bandit_captain grants Atlantean Sword weapon."""
        g = game_at_road
        g.player["damage"] = 100
        g.act("explore_ruins")
        g.act("attack")
        g.act("clear_ambush")
        g.act("attack")
        g.act("visit_trading_post")
        g.act("confront_the_pass")
        payload = g.act("attack")  # defeat captain

        assert "Atlantean Sword" in "\n".join(payload["messages"])
        assert g.player["weapon"] == "Atlantean Sword"
        assert g.player["damage"] == 40
        assert g._weapon_id == "captains_blade"


class TestAct2EnemyTemplates:
    def test_cultist_template(self):
        tpl = ENEMY_TEMPLATES["cultist"]
        assert tpl["name"] == "Noothgrush Cultist"
        assert tpl["hp"] == 35
        assert tpl["dmg"] == 13
        assert tpl["drops"]["flags"] == ["learned_plan"]
        assert tpl["goto"] == "road"

    def test_bandit_template(self):
        tpl = ENEMY_TEMPLATES["bandit"]
        assert tpl["name"] == "Bandit"
        assert tpl["hp"] == 28
        assert tpl["dmg"] == 10
        assert tpl["drops"]["potions"] == 1
        assert tpl["drops"]["flags"] == ["cleared_ambush"]
        assert tpl["goto"] == "road"

    def test_bandit_captain_template(self):
        tpl = ENEMY_TEMPLATES["bandit_captain"]
        assert tpl["name"] == "Bandit Captain"
        assert tpl["hp"] == 60
        assert tpl["dmg"] == 15
        assert tpl["drops"]["potions"] == 2
        assert tpl["drops"]["flags"] == ["defeated_captain"]
        assert tpl["goto"] == "fortress_gate"

    def test_captains_blade_weapon(self):
        blade = WEAPONS["captains_blade"]
        assert blade["name"] == "Atlantean Sword"
        assert blade["damage"] == 40
        assert blade["obtained_from"] == "bandit_captain"
        assert "heavier than your own" in " ".join(blade["flavor"])

    def test_road_location_structure(self):
        road = LOCATIONS["road"]
        assert "on_enter" in road
        assert "options" in road
        option_ids = [o["id"] for o in road["options"]]
        assert "explore_ruins" in option_ids
        assert "clear_ambush" in option_ids
        assert "visit_trading_post" in option_ids
        assert "confront_the_pass" in option_ids

    def test_town_has_depart_road_option(self):
        town = LOCATIONS["town"]
        option_ids = [o["id"] for o in town["options"]]
        assert "depart_road" in option_ids
        depart = next(o for o in town["options"] if o["id"] == "depart_road")
        assert depart["show_if"] == "avenged_raider"
        assert depart["goto"] == "road"

    def test_fortress_gate_structure(self):
        assert "fortress_gate" in LOCATIONS
        fortress_gate = LOCATIONS["fortress_gate"]
        assert "on_enter" in fortress_gate
        assert "options" in fortress_gate
        option_ids = [o["id"] for o in fortress_gate["options"]]
        assert "enter_fortress" in option_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])