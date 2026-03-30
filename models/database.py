import json
import os
import time
import random
from datetime import datetime
from tinydb import TinyDB, Query

DB_PATH = os.environ.get("DB_PATH", "data/game.json")


class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.db = TinyDB(DB_PATH)
        self.nations = self.db.table("nations")
        self.wars = self.db.table("wars")
        self.alliances = self.db.table("alliances")
        self.treaties = self.db.table("treaties")
        self.elections = self.db.table("elections")
        self.events = self.db.table("events")
        self.groups = self.db.table("groups")
        self.settings = self.db.table("settings")
        self.trade_offers = self.db.table("trade_offers")
        self.laws = self.db.table("laws")
        self.Q = Query()

        # Initialize default settings
        if not self.settings.search(self.Q.key == "game_active"):
            self.settings.insert({"key": "game_active", "value": True})
        if not self.settings.search(self.Q.key == "event_frequency"):
            self.settings.insert({"key": "event_frequency", "value": 3600})

    # ─── Settings ────────────────────────────────────
    def get_setting(self, key, default=None):
        result = self.settings.search(self.Q.key == key)
        return result[0]["value"] if result else default

    def set_setting(self, key, value):
        if self.settings.search(self.Q.key == key):
            self.settings.update({"value": value}, self.Q.key == key)
        else:
            self.settings.insert({"key": key, "value": value})

    # ─── Nation CRUD ─────────────────────────────────
    def create_nation(self, user_id, name, ideology):
        if self.nations.search(self.Q.user_id == user_id):
            return None
        nation = {
            "user_id": user_id,
            "name": name,
            "ideology": ideology,
            "created_at": datetime.now().isoformat(),
            # Resources
            "money": 10000,
            "food": 5000,
            "materials": 3000,
            "oil": 1000,
            "tech_points": 0,
            # Population
            "population": 100000,
            "happiness": 70,
            "health": 70,
            "education": 50,
            # Economy
            "tax_rate": 15,
            "gdp": 50000,
            "inflation": 2.0,
            "unemployment": 10.0,
            "factories": 5,
            "farms": 10,
            "mines": 3,
            "oil_wells": 1,
            "trade_income": 0,
            # Military
            "soldiers": 1000,
            "tanks": 10,
            "jets": 5,
            "ships": 2,
            "missiles": 0,
            "nukes": 0,
            "defense_level": 1,
            "military_tech": 1,
            "military_morale": 70,
            # Politics
            "government_type": ideology,
            "leader_title": "Presiden",
            "approval_rating": 60,
            "corruption": 20,
            "freedom_index": 50,
            "stability": 70,
            "parties": [],
            "ministers": {},
            "active_policies": [],
            # Diplomacy
            "allies": [],
            "enemies": [],
            "sanctions_from": [],
            "sanctions_to": [],
            "reputation": 50,
            # State
            "is_at_war": False,
            "war_weariness": 0,
            "turn": 0,
            "last_collect": time.time(),
            "achievements": [],
            "flags": {},
        }
        self.nations.insert(nation)
        return nation

    def get_nation(self, user_id):
        result = self.nations.search(self.Q.user_id == user_id)
        return result[0] if result else None

    def get_nation_by_name(self, name):
        result = self.nations.search(self.Q.name == name)
        return result[0] if result else None

    def update_nation(self, user_id, updates: dict):
        self.nations.update(updates, self.Q.user_id == user_id)

    def get_all_nations(self):
        return self.nations.all()

    def delete_nation(self, user_id):
        self.nations.remove(self.Q.user_id == user_id)

    # ─── Power Score ─────────────────────────────────
    def calc_power(self, nation):
        military = (
            nation["soldiers"] * 1
            + nation["tanks"] * 50
            + nation["jets"] * 100
            + nation["ships"] * 80
            + nation["missiles"] * 200
            + nation["nukes"] * 5000
        ) * (nation["military_tech"] * 0.5)
        economic = nation["gdp"] * 0.1 + nation["money"] * 0.01
        social = (
            nation["population"] * 0.001
            + nation["happiness"] * 10
            + nation["education"] * 10
        )
        return int(military + economic + social)

    # ─── Wars ────────────────────────────────────────
    def create_war(self, attacker_id, defender_id, war_name):
        war = {
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "name": war_name,
            "started_at": datetime.now().isoformat(),
            "status": "active",
            "attacker_wins": 0,
            "defender_wins": 0,
            "rounds": [],
            "total_rounds": 0,
        }
        self.wars.insert(war)
        self.update_nation(attacker_id, {"is_at_war": True})
        self.update_nation(defender_id, {"is_at_war": True})
        return war

    def get_active_wars(self, user_id=None):
        if user_id:
            return self.wars.search(
                (self.Q.status == "active")
                & ((self.Q.attacker_id == user_id) | (self.Q.defender_id == user_id))
            )
        return self.wars.search(self.Q.status == "active")

    def end_war(self, attacker_id, defender_id, winner_id):
        self.wars.update(
            {"status": "ended", "winner_id": winner_id},
            (self.Q.attacker_id == attacker_id)
            & (self.Q.defender_id == defender_id)
            & (self.Q.status == "active"),
        )
        self.update_nation(attacker_id, {"is_at_war": False, "war_weariness": 0})
        self.update_nation(defender_id, {"is_at_war": False, "war_weariness": 0})

    # ─── Alliances ───────────────────────────────────
    def create_alliance(self, name, founder_id):
        if self.alliances.search(self.Q.name == name):
            return None
        alliance = {
            "name": name,
            "founder_id": founder_id,
            "members": [founder_id],
            "created_at": datetime.now().isoformat(),
        }
        self.alliances.insert(alliance)
        return alliance

    def join_alliance(self, name, user_id):
        alliance = self.alliances.search(self.Q.name == name)
        if alliance:
            members = alliance[0]["members"]
            if user_id not in members:
                members.append(user_id)
                self.alliances.update({"members": members}, self.Q.name == name)
                return True
        return False

    def get_alliance(self, name):
        result = self.alliances.search(self.Q.name == name)
        return result[0] if result else None

    def get_user_alliance(self, user_id):
        for a in self.alliances.all():
            if user_id in a["members"]:
                return a
        return None

    # ─── Elections ───────────────────────────────────
    def create_election(self, user_id, candidates):
        election = {
            "user_id": user_id,
            "candidates": candidates,
            "votes": {c: 0 for c in candidates},
            "voters": [],
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }
        self.elections.insert(election)
        return election

    def get_active_election(self, user_id):
        result = self.elections.search(
            (self.Q.user_id == user_id) & (self.Q.status == "active")
        )
        return result[0] if result else None

    # ─── Events Log ──────────────────────────────────
    def log_event(self, event_type, target_id, description, effects=None):
        event = {
            "type": event_type,
            "target_id": target_id,
            "description": description,
            "effects": effects or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.events.insert(event)
        return event

    def get_recent_events(self, target_id=None, limit=10):
        if target_id:
            results = self.events.search(self.Q.target_id == target_id)
        else:
            results = self.events.all()
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:limit]

    # ─── Groups ──────────────────────────────────────
    def register_group(self, chat_id, title):
        if not self.groups.search(self.Q.chat_id == chat_id):
            self.groups.insert({
                "chat_id": chat_id,
                "title": title,
                "registered_at": datetime.now().isoformat(),
                "settings": {"announcements": True}
            })
        else:
            self.groups.update({"title": title}, self.Q.chat_id == chat_id)

    def get_all_groups(self):
        return self.groups.all()

    # ─── Trade Offers ────────────────────────────────
    def create_trade(self, from_id, to_id, offer, request):
        trade = {
            "from_id": from_id,
            "to_id": to_id,
            "offer": offer,
            "request": request,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        self.trade_offers.insert(trade)
        return trade

    def get_pending_trades(self, user_id):
        return self.trade_offers.search(
            (self.Q.to_id == user_id) & (self.Q.status == "pending")
        )
