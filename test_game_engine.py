"""Unit tests for Turbo Death Warrior game engine."""

import pytest
from game_engine import Game, ENEMY_TEMPLATES, HEAL_AMOUNT, STRIKE_DAMAGE


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
        assert g.player["weapon"] == "Rusty Spork"
        assert g.player["damage"] == 10
        assert g.player["potions"] == 2
        assert g.player["has_turbo_crystal"] is False

    def test_reset_restores_initial_state(self):
        g = Game()
        g.player["name"] = "Test"
        g.player["hp"] = 50
        g.player["weapon"] = "Chainsaw-Sword"
        g.player["damage"] = 25
        g.player["potions"] = 0
        g.player["has_turbo_crystal"] = True
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
        assert g.player["weapon"] == "Rusty Spork"
        assert g.player["damage"] == 10
        assert g.player["potions"] == 2
        assert g.player["has_turbo_crystal"] is False


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
        assert "Rusty Spork" in "\n".join(payload["messages"])
        assert "Potions: 2" in "\n".join(payload["messages"])
        assert "Turbo Crystal: No" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "town"

    def test_visit_blacksmith_upgrades_weapon(self, game_in_town):
        payload = game_in_town.act("visit_blacksmith")

        assert "Chainsaw-Sword" in "\n".join(payload["messages"])
        assert game_in_town.player["weapon"] == "Chainsaw-Sword"
        assert game_in_town.player["damage"] == 25
        assert payload["state"]["scene"] == "town"

    def test_visit_blacksmith_twice_keeps_weapon(self, game_in_town):
        game_in_town.act("visit_blacksmith")
        payload = game_in_town.act("visit_blacksmith")

        assert "already gave you my best weapon" in "\n".join(payload["messages"])
        assert game_in_town.player["weapon"] == "Chainsaw-Sword"
        assert game_in_town.player["damage"] == 25

    def test_go_forest_starts_orc_combat(self, game_in_town):
        payload = game_in_town.act("go_forest")

        assert "WHISPERING FOREST" in "\n".join(payload["messages"])
        assert "COMBAT INITIATED" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "combat"
        assert game_in_town.enemy is not None
        assert game_in_town.enemy["key"] == "orc"
        assert game_in_town.boss_fight is False
        assert len(payload["options"]) == 2

    def test_invalid_action_in_town_returns_error(self, game_in_town):
        payload = game_in_town.act("invalid_action")

        assert "Invalid choice." in payload["messages"][0]
        assert payload["state"]["scene"] == "town"


class TestCaveEntranceActions:
    @pytest.fixture
    def game_at_cave_entrance(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.act("attack")
        while g.enemy and g.enemy["hp"] > 0:
            g.act("attack")
        return g

    def test_enter_caves_starts_boss_combat(self, game_at_cave_entrance):
        payload = game_at_cave_entrance.act("enter_caves")

        assert "THRONE OF DOOM" in "\n".join(payload["messages"])
        assert "MEGA-GOBLIN KING" in "\n".join(payload["messages"])
        assert payload["state"]["scene"] == "combat"
        assert game_at_cave_entrance.enemy is not None
        assert game_at_cave_entrance.enemy["key"] == "boss"
        assert game_at_cave_entrance.boss_fight is True
        assert len(payload["options"]) >= 2
        assert any(o["id"] == "attack" for o in payload["options"])
        assert any(o["id"] == "heal" for o in payload["options"])

    def test_flee_town_returns_to_town(self, game_at_cave_entrance):
        payload = game_at_cave_entrance.act("flee_town")

        assert "safety of Oakhaven" in "\n".join(payload["messages"])
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
        game_in_orc_combat.player["has_turbo_crystal"] = True
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
    def test_defeating_orc_grants_crystal_and_potion(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        payload = g.act("attack")

        assert g.player["has_turbo_crystal"] is True
        assert g.player["potions"] == 3
        assert "Turbo Crystal" in "\n".join(payload["messages"])
        assert "potion" in "\n".join(payload["messages"]).lower()
        assert g.scene == "cave_entrance"
        assert g.enemy is None


class TestBossCombat:
    @pytest.fixture
    def game_in_boss_combat(self):
        g = Game()
        g.start()
        g.submit_name("Hero")
        g.act("go_forest")
        g.player["damage"] = 100
        g.act("attack")
        g.act("enter_caves")
        return g

    def test_boss_has_correct_stats(self, game_in_boss_combat):
        assert game_in_boss_combat.enemy["name"] == "Mega-Goblin King"
        assert game_in_boss_combat.enemy["hp"] == 120
        assert game_in_boss_combat.enemy["dmg"] == 20
        assert game_in_boss_combat.boss_fight is True

    def test_strike_deals_massive_damage_and_consumes_crystal(self, game_in_boss_combat):
        game_in_boss_combat.player["has_turbo_crystal"] = True
        initial_hp = game_in_boss_combat.enemy["hp"]
        payload = game_in_boss_combat.act("strike")

        assert game_in_boss_combat.enemy["hp"] == 0
        assert game_in_boss_combat.player["has_turbo_crystal"] is False
        assert "TURBO DEATH STRIKE" in "\n".join(payload["messages"])

    def test_defeating_boss_ends_game_with_victory(self, game_in_boss_combat):
        game_in_boss_combat.player["damage"] = 200
        payload = game_in_boss_combat.act("attack")

        assert game_in_boss_combat.over is True
        assert game_in_boss_combat.scene == "victory"
        assert "DEFEATED THE MEGA-GOBLIN KING" in "\n".join(payload["messages"])
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
        g.act("enter_caves")
        g.player["damage"] = 200
        g.act("attack")

        assert g.over is True
        payload = g.act("restart")

        assert g.over is False
        assert g.scene == "name_prompt"
        assert g.player["name"] == ""
        assert g.player["hp"] == 100
        assert g.player["weapon"] == "Rusty Spork"
        assert payload["text_input"] == "What is your name, warrior?"


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
        assert state["enemy"]["key"] == "orc"
        assert "max_hp" in state["enemy"]


class TestConstants:
    def test_enemy_templates_structure(self):
        assert "orc" in ENEMY_TEMPLATES
        assert "boss" in ENEMY_TEMPLATES
        for tpl in ENEMY_TEMPLATES.values():
            assert "key" in tpl
            assert "name" in tpl
            assert "hp" in tpl
            assert "dmg" in tpl

    def test_heal_amount_and_strike_damage(self):
        assert HEAL_AMOUNT == 40
        assert STRIKE_DAMAGE == 150


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])