"""US2 (FR-003/004, SC-006/008): ghép người giám hộ bằng `/start <mã>`."""

import asyncio
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import delete, select

from hoicon.agents import texts
from hoicon.channels.updates import handle_update
from hoicon.db.models import Family, PairingCode
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import decrypt_chat_id, hmac_zalo

pytestmark = pytest.mark.integration

USER_A, USER_B, USER_C = "fixture-user-a", "fixture-user-b", "fixture-user-c"


async def start(world: Any, user: str, code: str | None, **kw: Any) -> str | None:
    kind = "start" if code else "start_no_code"
    return await handle_update(world.deps, None, world.update_payload(user, kind=kind, value=code, **kw))


async def code_rows(family: Family) -> list[PairingCode]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(PairingCode).where(PairingCode.family_id == family.id)))


async def test_valid_code_pairs_the_guardian_and_confirms_with_ai_disclosure(zalo_world: Any) -> None:
    world = zalo_world
    code = await world.make_code()
    assert await start(world, USER_A, code) == "sent"

    (member,) = await world.members()
    assert (member.family_id, member.role, member.guardian_rank) == (world.family.id, "guardian", 1)
    assert member.zalo_bot_id == world.bot_id
    assert member.zalo_user_hmac == hmac_zalo(world.bot_id, USER_A)[1]
    assert (
        decrypt_chat_id(member.zalo_chat_enc, member.zalo_user_hmac) == f"chat-of-{USER_A}"
    )  # gửi được, nhưng DB không có chữ thô
    assert USER_A not in repr([member.zalo_user_hmac, member.zalo_chat_enc])
    assert world.sent_to(USER_A) == [texts.pairing_confirmed()]  # SC-006
    assert world.sent_to(USER_A)[0].startswith("Đây là trợ lý AI HỏiCon.")
    (used,) = await code_rows(world.family)
    assert used.used_at is not None
    (row,) = await world.rows()
    assert (row.template_id, row.status, row.family_id, row.member_id) == (
        "pairing_confirmed",
        "sent",
        world.family.id,
        member.id,
    )
    assert row.incident_id is None


async def test_second_guardian_gets_rank_2_and_a_third_is_refused_without_burning_the_code(zalo_world: Any) -> None:
    world = zalo_world
    await start(world, USER_A, await world.make_code())
    await start(world, USER_B, await world.make_code())
    ranks = {m.zalo_user_hmac: m.guardian_rank for m in await world.members()}
    assert ranks == {hmac_zalo(world.bot_id, USER_A)[1]: 1, hmac_zalo(world.bot_id, USER_B)[1]: 2}

    third = await world.make_code()
    await start(world, USER_C, third)
    assert world.sent_to(USER_C) == [texts.pairing_help()]  # không xác nhận mã hợp lệ cho người thứ ba
    assert len(await world.members()) == 2
    assert [c.used_at for c in await code_rows(world.family) if c.used_at is None]  # mã chưa bị tiêu thụ


async def test_lowest_free_rank_is_reused(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(2)  # còn trống hạng 1
    await start(world, USER_A, await world.make_code())
    mine = [m for m in await world.members() if m.zalo_user_hmac == hmac_zalo(world.bot_id, USER_A)[1]]
    assert mine[0].guardian_rank == 1


async def test_bad_codes_all_get_the_same_generic_reply_and_reveal_nothing(zalo_world: Any) -> None:
    world = zalo_world
    expired = await world.make_code(expires_in=timedelta(minutes=-1))
    used = await world.make_code(used=True)
    for user, code in (("u-unknown", "000000"), ("u-expired", expired), ("u-used", used), ("u-nocode", None)):
        await start(world, user, code)
    replies = {user: world.sent_to(user) for user in ("u-unknown", "u-expired", "u-used", "u-nocode")}
    assert all(r == [texts.pairing_help()] for r in replies.values())  # SC-008: không phân biệt sai/hết hạn/đã dùng
    assert await world.members() == []
    rows = await world.rows()
    assert len(rows) == 4 and all(
        r.family_id is None and r.status == "sent" for r in rows
    )  # tin trả lời vẫn tính hạn mức


async def test_expired_code_stays_rejected_even_if_never_used(zalo_world: Any) -> None:
    world = zalo_world
    code = await world.make_code(expires_in=timedelta(minutes=-15))
    await start(world, USER_A, code)
    assert await world.members() == []
    assert [c.used_at for c in await code_rows(world.family)] == [None]


async def test_same_zalo_pairing_again_creates_no_duplicate(zalo_world: Any) -> None:
    world = zalo_world
    await start(world, USER_A, await world.make_code())
    await start(world, USER_A, await world.make_code())  # mã mới, cùng Zalo, cùng gia đình
    await start(world, USER_A, "000000")  # mã cũ/sai khi đã ghép
    await start(world, USER_A, None)
    assert len(await world.members()) == 1
    assert world.sent_to(USER_A) == [texts.pairing_confirmed(), *[texts.pairing_already()] * 3]
    assert all(c.used_at is not None for c in (await code_rows(world.family))[:2])


async def test_zalo_already_in_another_family_is_not_moved(zalo_world: Any) -> None:
    world = zalo_world
    await start(world, USER_A, await world.make_code())
    async with get_sessionmaker().begin() as session:
        other = Family(display_name="Gia đình khác", region="bac", is_demo=True)
        session.add(other)
    try:
        code = await world.make_code(family=other)
        await start(world, USER_A, code)
        assert world.sent_to(USER_A)[-1] == texts.pairing_already()  # không lộ mã của gia đình kia hợp lệ
        (member,) = await world.members()
        assert member.family_id == world.family.id
        assert [c.used_at for c in await code_rows(other)] == [None]  # mã của gia đình kia không bị tiêu thụ
    finally:
        async with get_sessionmaker().begin() as session:
            await session.execute(delete(Family).where(Family.id == other.id))


async def test_redelivered_update_pairs_once_and_replies_once(zalo_world: Any) -> None:
    world = zalo_world
    code = await world.make_code()
    payload = world.update_payload(USER_A, kind="start", value=code, message_id="fixture-msg-same")
    for attempt in (1, 2, 3):
        await handle_update(world.deps, None, payload, attempt)
    assert len(await world.members()) == 1 and len(world.client.sent) == 1 and len(await world.rows()) == 1


async def test_one_code_cannot_pair_two_people_at_once(zalo_world: Any) -> None:
    world = zalo_world
    code = await world.make_code()
    results = await asyncio.gather(start(world, USER_A, code), start(world, USER_B, code))
    assert results == ["sent", "sent"]  # cả hai đều nhận được câu trả lời
    assert len(await world.members()) == 1  # nhưng chỉ một người được ghép
    replies = world.sent_to(USER_A) + world.sent_to(USER_B)
    assert sorted(replies) == sorted([texts.pairing_confirmed(), texts.pairing_help()])


async def test_unpaired_person_sending_a_choice_is_pointed_to_pairing(zalo_world: Any) -> None:
    world = zalo_world
    await handle_update(world.deps, None, world.update_payload("u-stranger", kind="choice", value="1"))
    assert world.sent_to("u-stranger") == [texts.pairing_help()]  # không ai ngoài người đã ghép được chạm vào sự cố
    await handle_update(world.deps, None, world.update_payload("u-stranger", kind="other"))
    assert world.sent_to("u-stranger")[-1] == texts.pairing_help()


async def test_member_row_holds_no_raw_zalo_identifiers(zalo_world: Any) -> None:
    world = zalo_world
    await start(world, USER_A, await world.make_code())
    (member,) = await world.members()
    dumped = " ".join(str(v) for v in vars(member).values())
    assert USER_A not in dumped and f"chat-of-{USER_A}" not in dumped


async def seed_start_attempts(world: Any, user: str, count: int, *, minutes_ago: int = 1) -> None:
    """`count` job `zalo_update` loại start của người này đã được xếp cách đây `minutes_ago` phút."""
    from sqlalchemy import func

    from hoicon.db.ids import new_id
    from hoicon.db.models import Job

    payload = world.update_payload(user, kind="start", value="000000")
    async with get_sessionmaker().begin() as session:
        for _ in range(count):
            session.add(
                Job(
                    kind="zalo_update",
                    payload=payload,
                    idempotency_key=f"zalo:{world.bot_id}:seed-{new_id()}",
                    created_at=func.now() - timedelta(minutes=minutes_ago),
                    done_at=func.now(),
                )
            )


async def test_too_many_start_attempts_stop_the_code_being_checked(zalo_world: Any) -> None:
    """Chống dò mã 6 số: quá 10 lần thử trong 15 phút ⇒ ngay cả mã ĐÚNG cũng không được xét (và không bị tiêu thụ)."""
    world = zalo_world
    code = await world.make_code()
    await seed_start_attempts(world, USER_A, 11)
    await start(world, USER_A, code)
    assert world.sent_to(USER_A) == []  # im lặng luôn: kẻ dò mã không nhận được phản hồi nào (kể cả câu hướng dẫn)
    assert await world.members() == []
    assert [c.used_at for c in await code_rows(world.family)] == [None]
    # người khác không bị ảnh hưởng
    await start(world, USER_B, code)
    assert world.sent_to(USER_B) == [texts.pairing_confirmed()]


async def test_old_attempts_are_forgiven_after_the_window(zalo_world: Any) -> None:
    world = zalo_world
    await seed_start_attempts(world, USER_A, 30, minutes_ago=16)
    await seed_start_attempts(world, USER_A, 10)  # đúng ngưỡng cho phép (kể cả job hiện tại thì job test không xếp)
    await start(world, USER_A, await world.make_code())
    assert world.sent_to(USER_A) == [texts.pairing_confirmed()]


async def test_bot_wide_cap_stops_code_guessing_with_many_accounts(zalo_world: Any) -> None:
    """Nhiều tài khoản Zalo thay nhau dò: quá 100 lần thử mã trong 15 phút trên CẢ BOT thì không mã nào được xét."""
    world = zalo_world
    for index in range(12):  # 12 người × 9 lần = 108 lần thử, mỗi người vẫn dưới giới hạn 10 lần/người
        await seed_start_attempts(world, f"fixture-spammer-{index}", 9)
    code = await world.make_code()
    await start(world, USER_A, code)
    assert await world.members() == []
    assert [c.used_at for c in await code_rows(world.family)] == [None]  # mã đúng cũng không được xét lúc này
    assert world.sent_to(USER_A) == [texts.pairing_help()]  # người lạ mới chỉ nhận một câu hướng dẫn chung


async def test_chatty_unpaired_sender_stops_getting_replies_so_quota_is_not_burned(zalo_world: Any) -> None:
    world = zalo_world
    payload = world.update_payload("fixture-chatty", kind="other")
    await seed_other_updates(world, "fixture-chatty", 11)
    await handle_update(world.deps, None, payload)
    assert world.sent_to("fixture-chatty") == []  # không đốt hạn mức 3.000 tin/tháng cho người nhắn linh tinh
    await handle_update(world.deps, None, world.update_payload("fixture-quiet", kind="other"))
    assert world.sent_to("fixture-quiet") == [texts.pairing_help()]  # người khác vẫn được trả lời bình thường


async def seed_other_updates(world: Any, user: str, count: int) -> None:
    from sqlalchemy import func

    from hoicon.db.ids import new_id
    from hoicon.db.models import Job

    payload = world.update_payload(user, kind="other")
    async with get_sessionmaker().begin() as session:
        for _ in range(count):
            session.add(
                Job(
                    kind="zalo_update",
                    payload=payload,
                    idempotency_key=f"zalo:{world.bot_id}:seed-{new_id()}",
                    created_at=func.now() - timedelta(minutes=5),
                    done_at=func.now(),
                )
            )


async def test_a_confirmed_pairing_is_never_silenced_even_for_a_busy_sender(zalo_world: Any) -> None:
    world = zalo_world
    await seed_other_updates(world, USER_A, 30)  # đã nhắn rất nhiều (không phải mã)
    await start(world, USER_A, await world.make_code())
    assert world.sent_to(USER_A) == [texts.pairing_confirmed()]  # xác nhận ghép luôn được gửi


async def test_only_guardians_can_answer(zalo_world: Any) -> None:
    """Người có Zalo nhưng không phải người giám hộ (vai trò khác) không được dùng đường trả lời 1/2/3."""
    from sqlalchemy import update

    from hoicon.db.models import Member

    world = zalo_world
    await start(world, USER_A, await world.make_code())
    async with (
        get_sessionmaker().begin() as session
    ):  # giả lập dữ liệu tương lai (spec 020) có người 'protected' gắn Zalo
        await session.execute(
            update(Member).where(Member.zalo_bot_id == world.bot_id).values(role="protected", guardian_rank=None)
        )
    payload = world.update_payload(USER_A, kind="choice", value="1")
    await handle_update(world.deps, None, payload)
    assert world.sent_to(USER_A)[-1] == texts.pairing_help()  # không được nhận diện là người giám hộ
