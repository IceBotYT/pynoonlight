from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Union
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, validator
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential
from tzlocal import get_localzone_name

SANDBOX_URL = "https://api-sandbox.noonlight.com/dispatch/v1/alarms{path}"
_LOGGER = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(max=10))
async def _send_request(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Union[dict[Any, Any], list[dict[Any, Any]]],
    expected_code: int,
) -> requests.Response:
    response = requests.request(method, url, headers=headers, json=payload)
    if response.status_code != expected_code:
        raise FailedRequestError(response.text)
    return response


class FailedRequestError(Exception):
    """Exception for when we fail to reach Noonlight."""


class InvalidURLError(Exception):
    """Exception for when an invalid URL is received."""


class Address(BaseModel):
    line1: str
    line2: Optional[str]
    city: str
    state: str
    zip: str


class Coordinates(BaseModel):
    lat: float
    lng: float
    accuracy: int


class Workflow(BaseModel):
    id: str


class Services(BaseModel):
    police: bool
    fire: bool
    medical: bool
    other: bool


class Instructions(BaseModel):
    entry: str


class AlarmData(BaseModel):
    name: str
    phone: str
    pin: Optional[str]
    owner_id: Optional[str]
    location: Union[Address, Coordinates]
    workflow: Optional[Workflow]
    services: Optional[Services]
    instructions: Optional[Instructions]


class Event(BaseModel):
    event_type: str
    event_time: Union[datetime, str]
    meta: EventMeta

    @validator("event_type")
    def event_type_must_be(cls, v: str) -> str:
        if v not in [
            "alarm.device.activated_alarm",
            "alarm.person.activated_alarm",
            "alarm.device.value_changed",
        ]:
            raise ValueError(
                "must be one of 'alarm.device.activated_alarm', 'alarm.person.activated_alarm', 'alarm.device.value_changed'"
            )
        return v


class EventMeta(BaseModel):
    attribute: str
    value: str
    device_id: Optional[str]
    device_model: str
    device_name: str
    device_manufacturer: str
    media: Optional[str]

    @validator("attribute", pre=True)
    def attribute_must_be(cls, v: str) -> str:
        if v not in [
            "smoke",
            "camera",
            "lock",
            "contact",
            "motion",
            "network_connection",
            "water_leak",
            "freeze",
        ]:
            raise ValueError(
                "must be one of 'smoke', 'camera', 'lock', 'contact', 'motion', 'network_connection', 'water_leak', 'freeze'"
            )

        print("done")
        return v

    @validator("value")
    def value_must_be(cls, v: str, values: dict[str, str]) -> Optional[str]:
        try:
            attribute = values["attribute"]
        except KeyError:
            attribute = None
        value_should_be = {
            "smoke": ["detected", "clear"],
            "camera": ["unknown"],
            "lock": ["locked", "unlocked", "door_open", "door_closed"],
            "contact": ["open", "closed"],
            "motion": ["detected", "cleared"],
            "water_leak": ["detected", "cleared"],
            "freeze": ["detected", "cleared"],
            "network_connection": ["lost", "established"],
        }
        if attribute is not None:
            if v not in value_should_be[attribute]:
                raise ValueError(
                    f"must be one of {','.join(value_should_be[attribute])}"
                )
            return v

        return None

    @validator("media")
    def media_cannot_exist_if(cls, v: str, values: dict[str, str]) -> Optional[str]:
        attribute = values["attribute"] or None
        if attribute != "camera" and (v != "" or v is not None):
            raise ValueError("cannot be used when attribute is not 'camera'")
        return v


class Person(BaseModel):
    name: str
    pin: str
    phone: str


class Alarm:
    id: str
    sandbox: bool
    active: bool = True
    static: bool
    owner_id: str
    prod_url: str
    _token: str

    def __init__(
        self,
        alarm_id: str,
        sandbox: bool,
        owner_id: str,
        token: str,
        prod_url: Optional[str],
    ) -> None:
        self.id = alarm_id
        self.sandbox = sandbox
        self.owner_id = owner_id
        self._token = token

        if prod_url:
            parsed_url = urlparse(prod_url)

            self.prod_url = f"https://{parsed_url.netloc}/dispatch/v1/alarms"

    async def cancel(self, pin: Optional[str]) -> None:
        if not self.active:
            return  # Already canceled :)

        url = (
            SANDBOX_URL.format(path=f"/{self.id}/status")
            if self.sandbox
            else self.prod_url + f"/{self.id}/status"
        )
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        payload = (
            {"status": "CANCELED", "pin": pin}
            if pin is not None
            else {"status": "CANCELED"}
        )

        try:
            await _send_request("POST", url, headers, payload, 201)
        except RetryError as e:
            raise FailedRequestError from e

        self.active = False

        return

    async def update_location(self, coordinates: Coordinates) -> None:
        url = (
            SANDBOX_URL.format(path=f"/{self.id}/locations")
            if self.sandbox
            else self.prod_url + f"/{self.id}/locations"
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        payload = coordinates.dict()

        try:
            await _send_request("POST", url, headers, payload, 201)
        except RetryError as e:
            raise FailedRequestError from e

        return

    async def create_events(self, events: list[Event]) -> None:
        event_dicts: list[dict[str, Any]] = []
        for _, event in enumerate(events):
            if isinstance(event.event_time, datetime) and (
                event.event_time.tzinfo is None
                or event.event_time.tzinfo.utcoffset(event.event_time) is None
            ):
                _LOGGER.warning(
                    "Event time does not include time zone information, treating as if it is local time zone."
                )
                tz = get_localzone_name()
                event.event_time = event.event_time.strftime(
                    "%m/%d/%Y, %-I:%M:%S %p " + tz
                )
            elif isinstance(event.event_time, datetime):
                event.event_time = event.event_time.strftime(
                    "%m/%d/%Y, %-I:%M:%S %p %Z"
                )
            event_dicts.append(event.dict())

        url = (
            SANDBOX_URL.format(path=f"/{self.id}/events")
            if self.sandbox
            else self.prod_url + f"/{self.id}/events"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        try:
            await _send_request("POST", url, headers, event_dicts, 201)
        except RetryError as e:
            raise FailedRequestError from e

        return

    async def create_people(self, people: list[Person]) -> None:
        people_dicts = []
        for _, person in enumerate(people):
            people_dicts.append(person.dict())

        url = (
            SANDBOX_URL.format(path=f"/{self.id}/people")
            if self.sandbox
            else self.prod_url + f"/{self.id}/people"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        try:
            await _send_request("POST", url, headers, people_dicts, 201)
        except RetryError as e:
            raise FailedRequestError from e

        return

    async def update_person(self, person_data: dict[str, Any]) -> None:
        url = (
            SANDBOX_URL.format(path=f"/{self.id}/people")
            if self.sandbox
            else self.prod_url + f"/{self.id}/people"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        try:
            await _send_request("PUT", url, headers, person_data, 200)
        except RetryError as e:
            raise FailedRequestError from e

        return


async def create_alarm(
    data: AlarmData,
    server_token: str,
    sandbox: bool = True,
    prod_url: Optional[str] = None,
) -> Alarm:
    if sandbox or not prod_url:
        url = SANDBOX_URL.format(path="")
    else:
        # Validate the prod URL
        parsed_url = urlparse(prod_url)

        if parsed_url.scheme != "https":
            raise InvalidURLError("Invalid or missing URL scheme (expected https)")

        if not parsed_url.netloc.endswith(".noonlight.com"):
            raise InvalidURLError("Invalid domain (expected ending with noonlight.com)")
        url = f"https://{parsed_url.netloc}/dispatch/v1/alarms"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {server_token}",
    }

    payload = data.dict()

    try:
        response = await _send_request("POST", url, headers, payload, 201)
    except RetryError as e:
        raise FailedRequestError from e

    response_data = response.json()
    alarm = Alarm(
        alarm_id=response_data["id"],
        sandbox=sandbox,
        owner_id=response_data["owner_id"],
        token=server_token,
        prod_url=prod_url,
    )

    return alarm
