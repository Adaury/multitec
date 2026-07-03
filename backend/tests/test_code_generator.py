from app.services.code_generator import next_code


def test_next_code_increments_sequentially(db_session):
    first = next_code(db_session, "TST")
    second = next_code(db_session, "TST")
    db_session.commit()
    assert first == "TST-000001"
    assert second == "TST-000002"


def test_next_code_independent_per_prefix(db_session):
    a = next_code(db_session, "AAA")
    b = next_code(db_session, "BBB")
    db_session.commit()
    assert a == "AAA-000001"
    assert b == "BBB-000001"
