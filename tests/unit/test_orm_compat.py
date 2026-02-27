from app.db.orm import _replace_placeholders


def test_replace_placeholders_multiple_args():
    query, params = _replace_placeholders('select * from blogs where id=? and enabled=?', ['b1', True])
    assert query == 'select * from blogs where id=:p1 and enabled=:p2'
    assert params == {'p1': 'b1', 'p2': True}


def test_replace_placeholders_no_args():
    query, params = _replace_placeholders('select now()', None)
    assert query == 'select now()'
    assert params == {}
