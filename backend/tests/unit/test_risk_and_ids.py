import itertools

from hoicon.db.ids import new_id
from hoicon.domain.risk import RiskLevel, raise_only


def test_raise_only_never_lowers_below_floor() -> None:
    for floor, proposed in itertools.product(RiskLevel, repeat=2):
        result = raise_only(floor, proposed)
        assert result.rank >= floor.rank
        assert result.rank == max(floor.rank, proposed.rank)


def test_raise_only_ignores_missing_proposals() -> None:
    assert raise_only(RiskLevel.HIGH, None, RiskLevel.LOW) is RiskLevel.HIGH


def test_new_id_is_uuid7_and_time_ordered() -> None:
    ids = [new_id() for _ in range(200)]
    assert all(i.version == 7 and i.variant == "specified in RFC 4122" for i in ids)
    timestamps = [i.int >> 80 for i in ids]
    assert timestamps == sorted(timestamps)
    assert len(set(ids)) == len(ids)
