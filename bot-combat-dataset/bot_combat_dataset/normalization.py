from __future__ import annotations

from typing import Iterable, Dict, Any, List, Tuple
import pandas as pd

from .schemas import Bot, Fight, Event, Team


def records_to_dataframe(records: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(list(records))


def build_dataframes(
    *,
    bots: Iterable[Bot] = (),
    fights: Iterable[Fight] = (),
    events: Iterable[Event] = (),
    teams: Iterable[Team] = (),
) -> Dict[str, pd.DataFrame]:
    df_bots = records_to_dataframe(bot.to_record() for bot in bots)
    df_fights = records_to_dataframe(fight.to_record() for fight in fights)
    df_events = records_to_dataframe(event.to_record() for event in events)
    df_teams = records_to_dataframe(team.to_record() for team in teams)

    # Basic normalization: enforce column order for readability
    if not df_bots.empty:
        bot_cols = [
            "bot_id",
            "name",
            "team_name",
            "weight_class",
            "country",
            "primary_weapon",
            "drive_type",
            "active_years",
            "aliases",
            "wiki_url",
            "notes",
        ]
        df_bots = df_bots.reindex(columns=bot_cols)

    if not df_fights.empty:
        fight_cols = [
            "fight_id",
            "event_id",
            "series",
            "season",
            "round_name",
            "heat",
            "episode",
            "blue_bot_id",
            "red_bot_id",
            "blue_bot_name",
            "red_bot_name",
            "winner_bot_id",
            "winner_bot_name",
            "method",
            "duration",
            "referee_decision",
            "notes",
            "source_url",
        ]
        df_fights = df_fights.reindex(columns=fight_cols)

    if not df_events.empty:
        event_cols = [
            "event_id",
            "name",
            "series",
            "season",
            "location",
            "date_start",
            "date_end",
            "source_url",
        ]
        df_events = df_events.reindex(columns=event_cols)

    if not df_teams.empty:
        team_cols = ["team_id", "name", "country", "members"]
        df_teams = df_teams.reindex(columns=team_cols)

    return {
        "bots": df_bots,
        "fights": df_fights,
        "events": df_events,
        "teams": df_teams,
    }


def export_to_excel(
    dataframes: Dict[str, pd.DataFrame], excel_path: str
) -> None:
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for name, df in dataframes.items():
            # Ensure there is at least one row so Excel has headers
            if df.empty:
                df = df.head(0)
            df.to_excel(writer, sheet_name=name, index=False)


def export_to_parquet(
    dataframes: Dict[str, pd.DataFrame], directory: str
) -> List[str]:
    written_paths: List[str] = []
    for name, df in dataframes.items():
        path = f"{directory.rstrip('/')}/{name}.parquet"
        df.to_parquet(path, index=False)
        written_paths.append(path)
    return written_paths
