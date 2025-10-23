# tests/test_habits_repo.py
import os
from habits_repo import (
    make_engine, init_db, add_habit, list_active, list_all,
    set_active, update_completion
)

def test_add_and_filter_active(tmp_path):
    # temporary sqlite
    db_file = tmp_path / "test.db"
    engine = make_engine(str(db_file))
    init_db(engine, seed=False)

    # Arrange
    add_habit(engine, "Drink water")         # 預設 active=1, completion=0
    add_habit(engine, "Read 30 mins")
    # stop the second one
    all_rows = list_all(engine)
    assert len(all_rows) == 2
    second_id = all_rows[1]["id"]
    set_active(engine, second_id, False)

    # Act
    active = list_active(engine)

    # Assert
    assert len(active) == 1
    assert active[0]["name"] == "Drink water"
    assert active[0]["active"] == 1

def test_update_completion_persists(tmp_path):
    db_file = tmp_path / "test.db"
    engine = make_engine(str(db_file))
    init_db(engine, seed=False)

    add_habit(engine, "Run 3km")
    habit_id = list_all(engine)[0]["id"]

    update_completion(engine, habit_id, 55)
    rows = list_all(engine)
    assert rows[0]["completion"] == 55