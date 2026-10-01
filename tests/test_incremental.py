from datetime import date
from etl.config import Settings
from etl.pipeline import choose_start

SETTINGS = Settings("unused", "unused")


def test_first_load_and_forced_full():
    assert choose_start(None,None,date(2024,7,1),SETTINGS) == (date(2000,1,1),True)
    assert choose_start(date(2024,6,30),date(2024,6,30),date(2024,7,1),SETTINGS,True)[1]


def test_overlap_is_based_on_last_observation_not_wall_clock():
    assert choose_start(date(2024,6,1),date(2024,6,15),date(2024,7,1),SETTINGS) == (date(2024,3,3),False)


def test_periodic_full_refresh():
    assert choose_start(date(2024,6,30),date(2024,5,1),date(2024,7,1),SETTINGS) == (date(2000,1,1),True)
