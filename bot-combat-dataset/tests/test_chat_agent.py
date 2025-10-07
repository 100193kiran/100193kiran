from bot_combat_dataset.chat.agent import RetrievalQABot
from bot_combat_dataset.normalization import build_dataframes
from bot_combat_dataset.schemas import Bot, Fight, Event


def test_retrieval_agent_answers_from_fight_context():
    bots = [Bot(bot_id="razer", name="Razer"), Bot(bot_id="hypno-disc", name="Hypno-Disc")]
    events = [Event(event_id="robot-wars-seventh-wars", name="Robot Wars: The Seventh Wars", series="Robot Wars", season="Series 7")]
    fights = [
        Fight(
            fight_id="heat-a-razer-hypno",
            event_id="robot-wars-seventh-wars",
            series="Robot Wars",
            season="Series 7",
            round_name="Heat A",
            blue_bot_id="razer",
            red_bot_id="hypno-disc",
            blue_bot_name="Razer",
            red_bot_name="Hypno-Disc",
            winner_bot_id="razer",
            winner_bot_name="Razer",
            method="KO",
            duration="1:10",
            referee_decision=False,
            notes="",
            source_url="http://example.com",
        )
    ]

    tables = build_dataframes(bots=bots, fights=fights, events=events)
    agent = RetrievalQABot(tables)

    result = agent.answer("Who defeated Hypno-Disc in Heat A?")
    assert "Razer" in result["answer"]
