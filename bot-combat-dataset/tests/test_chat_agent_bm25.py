from bot_combat_dataset.chat.agent import RetrievalQABot, RetrievalQAConfig
from bot_combat_dataset.normalization import build_dataframes
from bot_combat_dataset.schemas import Bot, Fight, Event


def test_bm25_retrieval_finds_correct_fight():
    bots = [
        Bot(bot_id="razer", name="Razer"),
        Bot(bot_id="chaos-2", name="Chaos 2"),
    ]
    events = [Event(event_id="robot-wars-seventh-wars", name="Robot Wars: The Seventh Wars", series="Robot Wars", season="Series 7")]
    fights = [
        Fight(
            fight_id="semi-razer-chaos2",
            event_id="robot-wars-seventh-wars",
            series="Robot Wars",
            season="Series 7",
            round_name="Semi",
            blue_bot_id="razer",
            red_bot_id="chaos-2",
            blue_bot_name="Razer",
            red_bot_name="Chaos 2",
            winner_bot_id="chaos-2",
            winner_bot_name="Chaos 2",
            method="UD",
            duration="3:00",
            referee_decision=True,
            notes="Judges' decision",
            source_url="http://example.com",
        )
    ]

    tables = build_dataframes(bots=bots, fights=fights, events=events)
    cfg = RetrievalQAConfig(retriever="bm25")
    agent = RetrievalQABot(tables, cfg)

    result = agent.answer("Who won the semi between Razer and Chaos 2?")
    assert "Chaos 2" in result["answer"]
