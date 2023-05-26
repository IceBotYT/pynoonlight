from __future__ import annotations

from aioresponses import aioresponses
from tenacity import wait_none

from pynoonlight import _send_request
from pynoonlight.dispatch import (
    SANDBOX_URL,
    Address,
    Alarm,
    AlarmData,
    Coordinates,
    Location,
    create_alarm,
)

_send_request.retry.wait = wait_none()  # type: ignore


async def mock_alarm() -> Alarm:
    alarm_data = AlarmData(
        name="Test Person",
        phone="12345678901",
        pin="1234",
        location=Location(
            address=Address(
                line1="1234 Street St", city="City", state="State", zip="12345"
            )
        ),
    )
    with aioresponses() as m:
        m.post(
            SANDBOX_URL.format(path=""),
            status=201,
            payload={"id": "test_alarm_id", "owner_id": "test_owner_id"},
        )
        a: Alarm = await create_alarm(
            data=alarm_data,
            server_token="1234567890",
            sandbox=True,
        )
        return a


async def mock_dynamic_alarm() -> Alarm:
    alarm_data = AlarmData(
        name="Test Person",
        phone="12345678901",
        pin="1234",
        location=Location(
            coordinates=Coordinates(lat=12.34567890, lng=12.34567890, accuracy=2)
        ),
    )
    with aioresponses() as m:
        m.post(
            SANDBOX_URL.format(path=""),
            status=201,
            payload={"id": "test_alarm_id", "owner_id": "test_owner_id"},
        )
        a: Alarm = await create_alarm(
            data=alarm_data,
            server_token="1234567890",
            sandbox=True,
        )
        return a


async def mock_prod_alarm() -> Alarm:
    alarm_data = AlarmData(
        name="Test Person",
        phone="12345678901",
        pin="1234",
        location=Location(
            coordinates=Coordinates(lat=12.34567890, lng=12.34567890, accuracy=2)
        ),
    )
    with aioresponses() as m:
        m.post(
            "https://api.noonlight.com/dispatch/v1/alarms",
            status=201,
            payload={"id": "test_alarm_id", "owner_id": "test_owner_id"},
        )
        a: Alarm = await create_alarm(
            data=alarm_data,
            server_token="1234567890",
            sandbox=False,
        )
        return a
