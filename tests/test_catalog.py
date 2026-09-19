from ecl.catalog import build_catalog, catalog_size


def test_catalog_has_expected_size():
    assert catalog_size() == 143
    assert len(build_catalog()) == 143


def test_skus_are_unique():
    skus = [p.sku for p in build_catalog()]
    assert len(skus) == len(set(skus))


def test_margins_are_sane():
    for p in build_catalog():
        assert 0.0 < p.unit_cost < p.msrp
        assert 0.15 <= p.gross_margin <= 0.85


def test_catalog_is_deterministic():
    a = [(p.sku, p.msrp, p.unit_cost) for p in build_catalog()]
    b = [(p.sku, p.msrp, p.unit_cost) for p in build_catalog()]
    assert a == b
