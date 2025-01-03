from __future__ import annotations

from datetime import datetime

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from pydantic import ValidationError
from tenacity import RetryError
from tzlocal import get_localzone

from pynoonlight import FailedRequestError, _send_request
from pynoonlight.dispatch import (
    SANDBOX_URL,
    Address,
    Alarm,
    AlarmData,
    Coordinates,
    Event,
    EventMeta,
    Location,
    Person,
    create_alarm,
)

from . import mock_alarm, mock_dynamic_alarm, mock_prod_alarm


class TestDispatch:
    def test__event_type_must_be_fail(self) -> None:
        with pytest.raises(ValidationError):
            Event(
                event_type="some.nonexistent.event_type",
                event_time=datetime.now(),
                meta=EventMeta(
                    attribute="smoke",
                    value="detected",
                    device_model="A123",
                    device_name="Upstairs Hallway Smoke Detector",
                    device_manufacturer="Nest",
                ),
            )

    def test__event_creation(self) -> None:
        Event(
            event_type="alarm.device.activated_alarm",
            event_time=datetime.now(),
            meta=EventMeta(
                attribute="smoke",
                value="detected",
                device_model="A123",
                device_name="Upstairs Hallway Smoke Detector",
                device_manufacturer="Nest",
            ),
        )

    def test__attribute_must_be(self) -> None:
        with pytest.raises(ValidationError):
            EventMeta(
                attribute="asdf",
                value="detected",
                device_model="A123",
                device_name="Upstairs Hallway Smoke Detector",
                device_manufacturer="Nest",
            )

    @pytest.mark.parametrize(
        "attribute_to_test",
        [
            "smoke",
            "lock",
            "contact",
            "motion",
            "network_connection",
            "water_leak",
            "freeze",
        ],
    )
    def test__value_must_be(self, attribute_to_test: str) -> None:
        with pytest.raises(ValidationError):
            EventMeta(
                attribute=attribute_to_test,
                value="some_weird_value",
                device_model="A123",
                device_name="Upstairs Hallway Smoke Detector",
                device_manufacturer="Nest",
            )

    @pytest.mark.parametrize(
        "attribute_to_test,value",
        [
            ("lock", "locked"),
            ("contact", "open"),
            ("motion", "detected"),
            ("network_connection", "lost"),
        ],
    )
    def test__value_success(self, attribute_to_test: str, value: str) -> None:
        meta = EventMeta(
            attribute=attribute_to_test,
            value=value,
            device_model="A123",
            device_name="Upstairs Hallway Smoke Detector",
            device_manufacturer="Nest",
        )

        assert meta.value == value

    def test__media_cannot_exist(self) -> None:
        with pytest.raises(ValidationError):
            EventMeta(
                attribute="smoke",
                value="detected",
                device_model="A123",
                device_name="Upstairs Hallway Smoke Detector",
                device_manufacturer="Nest",
                media="https://example.com/video_feed.mp4",
            )

    def test__media_exist_success(self) -> None:
        meta = EventMeta(
            attribute="camera",
            value="unknown",
            device_model="A456",
            device_name="Back Porch Camera",
            device_manufacturer="Amcrest",
            media="https://example.com/video_123.mp4",
        )
        assert meta.media

    async def test__create_alarm_sandbox(self) -> None:
        a: Alarm = await mock_alarm()
        assert a
        assert a.id == "test_alarm_id"
        assert a.sandbox
        assert a.owner_id == "test_owner_id"

        return

    async def test__create_alarm_fail(self) -> None:
        alarm_data = AlarmData(
            name="Test Person",
            phone="12345678901",
            pin="1234",
            location=Location(
                coordinates=Coordinates(lat=12.34567890, lng=12.34567890, accuracy=2)
            ),
        )
        with pytest.raises(FailedRequestError):
            with aioresponses() as m:
                m.post(
                    SANDBOX_URL.format(path=""),
                    status=500,
                )
                await create_alarm(alarm_data, server_token="1234567890", sandbox=True)

        return

    async def test__create_alarm_prod(self) -> None:
        a: Alarm = await mock_prod_alarm()
        assert a
        assert a.id == "test_alarm_id"
        assert a.owner_id == "test_owner_id"
        assert a.prod_url == "https://api.noonlight.com/dispatch/v1/alarms"

    async def test__cancel_alarm_sandbox(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/status")
        with aioresponses() as m:
            m.post(url, status=201)
            await a.cancel("1234")
            await a.cancel("1234")  # Should return immediately
            assert len(m._responses) == 1

    async def test__cancel_alarm_fail(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/status")
        with aioresponses() as m:
            m.post(url, status=500)
            with pytest.raises(FailedRequestError):
                await a.cancel("1234")

    async def test__update_location(self) -> None:
        a: Alarm = await mock_dynamic_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/locations")
        with aioresponses() as m:
            m.post(url, status=201)
            await a.update_location(
                Coordinates(lat=12.34566789, lng=12.34567890, accuracy=2)
            )

    async def test__update_location_fail(self) -> None:
        a: Alarm = await mock_dynamic_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/locations")
        with aioresponses() as m:
            m.post(url, status=500)
            with pytest.raises(FailedRequestError):
                await a.update_location(
                    Coordinates(lat=12.34566789, lng=12.34567890, accuracy=2)
                )

    async def test__create_events_naive_time(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/events")
        with aioresponses() as m:
            m.post(url, status=201)
            await a.create_events(
                [
                    Event(
                        event_type="alarm.device.activated_alarm",
                        event_time=datetime.now(),
                        meta=EventMeta(
                            attribute="contact",
                            value="open",
                            device_model="A502",
                            device_name="Front Door",
                            device_manufacturer="Xiaomi Aqara",
                        ),
                    )
                ]
            )

    async def test__create_events_aware_time(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/events")
        with aioresponses() as m:
            m.post(url, status=201)
            event_time = datetime.now()
            event_time = event_time.replace(tzinfo=get_localzone())

            await a.create_events(
                [
                    Event(
                        event_type="alarm.device.activated_alarm",
                        event_time=event_time,
                        meta=EventMeta(
                            attribute="contact",
                            value="open",
                            device_model="A502",
                            device_name="Front Door",
                            device_manufacturer="Xiaomi Aqara",
                        ),
                    )
                ]
            )

    async def test__create_events_fail(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/events")
        with aioresponses() as m:
            m.post(url, status=500)
            with pytest.raises(FailedRequestError):
                await a.create_events(
                    [
                        Event(
                            event_type="alarm.device.activated_alarm",
                            event_time=datetime.now(),
                            meta=EventMeta(
                                attribute="contact",
                                value="open",
                                device_model="A502",
                                device_name="Front Door",
                                device_manufacturer="Xiaomi Aqara",
                            ),
                        )
                    ]
                )

    async def test__create_people(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/people")
        with aioresponses() as m:
            m.post(url, status=201)
            await a.create_people(
                [Person(name="Test Person 2", pin="5678", phone="10987654321")]
            )

    async def test__create_people_fail(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/people")
        with aioresponses() as m:
            m.post(url, status=500)
            with pytest.raises(FailedRequestError):
                await a.create_people(
                    [Person(name="Test Person 2", pin="5678", phone="10987654321")]
                )

    async def test__update_people(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/people/test_owner_id")
        with aioresponses() as m:
            m.put(url, status=200)
            await a.update_person({"height": {"unit": "INCHES", "value": "100"}})

    async def test__update_people_fail(self) -> None:
        a: Alarm = await mock_alarm()
        url = SANDBOX_URL.format(path="/test_alarm_id/people")
        with aioresponses() as m:
            m.put(url, status=500)
            with pytest.raises(FailedRequestError):
                await a.update_person({"height": {"unit": "INCHES", "value": "100"}})

    async def test__request_with_clientsession(self) -> None:
        url = "https://example.com"
        with aioresponses() as m:
            m.get(url, status=200)
            await _send_request("GET", url, {}, {}, 200, ClientSession())

    async def test__request_with_clientsession_fail(self) -> None:
        url = "https://example.com"
        with aioresponses() as m, pytest.raises(RetryError, match="FailedRequestError"):
            m.post(url, status=500, repeat=True)
            await _send_request("POST", url, {}, {}, 200, ClientSession())

    async def test__request_with_none_values(self) -> None:
        alarm_data = AlarmData(
            name="Test",
            location=Location(
                address=Address(
                    line1="1234 Test Street",
                    state="TEST",
                    city="Test City",
                    zip="12345",
                )
            ),
            phone="12345678901",
            pin=None,
        )
        with aioresponses() as m:
            m.post(
                "https://api-sandbox.noonlight.com/dispatch/v1/alarms",
                status=201,
                payload={"id": "123", "owner_id": "123"},
            )
            await create_alarm(alarm_data, "test_token", True)
