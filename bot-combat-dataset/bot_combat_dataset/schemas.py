from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any


@dataclass
class Bot:
    bot_id: str
    name: str
    team_name: Optional[str] = None
    weight_class: Optional[str] = None
    country: Optional[str] = None
    wiki_url: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    primary_weapon: Optional[str] = None
    drive_type: Optional[str] = None
    active_years: Optional[str] = None

    def to_record(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    event_id: str
    name: str
    series: str  # e.g., "BattleBots", "Robot Wars"
    season: Optional[str] = None
    location: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    source_url: Optional[str] = None

    def to_record(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Fight:
    fight_id: str
    event_id: Optional[str]
    series: str
    season: Optional[str]
    round_name: Optional[str]
    blue_bot_id: Optional[str]
    red_bot_id: Optional[str]
    blue_bot_name: Optional[str]
    red_bot_name: Optional[str]
    winner_bot_id: Optional[str]
    winner_bot_name: Optional[str]
    method: Optional[str]
    duration: Optional[str]
    referee_decision: Optional[bool]
    notes: Optional[str]
    source_url: Optional[str]

    def to_record(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Team:
    team_id: str
    name: str
    country: Optional[str] = None
    members: List[str] = field(default_factory=list)

    def to_record(self) -> Dict[str, Any]:
        return asdict(self)
