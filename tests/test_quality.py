import duckdb

from ecl.quality.expectations import Suite


def _con():
    con = duckdb.connect(":memory:")
    con.execute("create table t (id integer, val double, cat varchar)")
    con.execute("insert into t values (1, 10.0, 'a'), (2, -1.0, 'a'), (2, 5.0, 'b'), (3, null, 'x')")
    return con


def test_expect_positive_counts_violations():
    con = _con()
    res = Suite("s", con).expect_positive("t", "val").run()[0]
    # -1.0 and null both violate "> 0"
    assert res.violations == 2
    assert res.success is False


def test_expect_unique_detects_duplicates():
    con = _con()
    res = Suite("s", con).expect_unique("t", ["id"]).run()[0]
    assert res.violations == 1  # id=2 duplicated


def test_expect_in_set_flags_unknown_values():
    con = _con()
    res = Suite("s", con).expect_in_set("t", "cat", ["a", "b"]).run()[0]
    assert res.violations == 1  # 'x' not allowed


def test_passing_expectation_is_success():
    con = _con()
    res = Suite("s", con).expect_not_null("t", "id").run()[0]
    assert res.violations == 0
    assert res.success is True
