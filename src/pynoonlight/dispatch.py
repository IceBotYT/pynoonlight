"""The dispatch API."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Union

import aiohttp
from pydantic import BaseModel, field_validator, model_validator
from tenacity import RetryError
from typing_extensions import Self

from . import FailedRequestError, _send_request

SANDBOX_URL = "https://api-sandbox.noonlight.com/dispatch/v1/alarms{path}"
PRODUCTION_URL = "https://api.noonlight.com/dispatch/v1/alarms{path}"
_LOGGER = logging.getLogger(__name__)


class Address(BaseModel):
    """
    Used for static alarms (e.g. a fire or a security alarm).

    Args:
        line1 (str): Line 1 of the address
        line2 (str, optional): Line 2 of the address. Optional.
        city (str): The city where the alarm occured
        state (str): The state where the alarm occured
        zip (str): The ZIP code where the alarm occured
    """

    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    zip: str


class Coordinates(BaseModel):
    """
    Used for dynamic alarms when the user is constantly changing location.

    Args:
        lat (float): Latitude of the alarm
        lon (float): Longitude of the alarm
        accuracy (int): Accuracy of the GPS in meters
    """

    lat: float
    lng: float
    accuracy: int


class Workflow(BaseModel):
    """
    From Noonlight: Optional workflow ID. This will be provided to you by the Noonlight team for certain use cases.

    Args:
        id (str): The workflow ID provided to you by the Noonlight team.
    """

    id: str


class Services(BaseModel):
    """
    Requested services for an alarm.

        police (bool): Police requested
        fire (bool): Fire department requested
        medical (bool): Medical personnel requested
        other (bool): Other authorities requested
    """

    police: Union[bool, None] = None
    fire: Union[bool, None] = None
    medical: Union[bool, None] = None
    other: Union[bool, None] = None


class Instructions(BaseModel):
    """
    From Noonlight: Instructions relayed to the dispatchers. Currently, the only allowed type is entry.

    Args:
        entry (str): Instructions on how to enter the area of the alarm.
    """

    entry: str


class Location(BaseModel):
    """
    The location of the alarm.
    At least one argument is required.

    Args:
        address (Address): The address of the alarm.
        coordinates (Coordinates): The coordinates of the alarm.
    """

    address: Optional[Address] = None
    coordinates: Optional[Coordinates] = None


class AlarmData(BaseModel):
    """
    Alarm data passed on to Noonlight dispatchers.

    Args:
        name (str): Name of the alarm owner.
        phone (str): Verified phone number of the alarm owner.
        pin (str, optional): PIN used to cancel the alarm. Optional.
        owner_id (str, optional): Owner ID of the alarm, generated automatically if missing. Optional.
        location (Location): Location of the alarm. This matters the most!
        workflow (Workflow, optional): See Workflow. Optional.
        services (Services, optional): See Services. Optional.
        instructions (Instructions, optional): See Instructions. Optional.
    """

    name: str
    phone: str
    pin: Optional[str] = None
    owner_id: Optional[str] = None
    location: Location
    workflow: Optional[Workflow] = None
    services: Optional[Services] = None
    instructions: Optional[Instructions] = None


class Event(BaseModel):
    """
    An event that occurs during an alarm.
    This could be a smoke detector being cleared, a door being opened, a water leak being detected, etc.

    Args:
        event_type (str): Must be one of 'alarm.device.activated_alarm', 'alarm.person.activated_alarm', 'alarm.device.value_changed'
        event_time (datetime): The time the event occured. (if the datetime object is naive, it will be treated as if it is in local time zone)
        meta (EventMeta): The metadata of the event (see EventMeta)
    """

    event_type: str
    event_time: Union[datetime, str]
    meta: EventMeta

    @field_validator("event_type")
    @classmethod
    def event_type_must_be(cls, v: str) -> str:
        if v in {
            "alarm.device.activated_alarm",
            "alarm.person.activated_alarm",
            "alarm.device.value_changed",
        }:
            return v
        else:
            raise ValueError(
                "must be one of 'alarm.device.activated_alarm', 'alarm.person.activated_alarm', 'alarm.device.value_changed'"
            )


class EventMeta(BaseModel):
    """
    Metadata of an event to be used in Event.
    See [here](https://docs.noonlight.com/reference/post_alarms-alarm-id-events-1).
    """

    attribute: str
    value: str
    device_id: Optional[str] = None
    device_model: str
    device_name: str
    device_manufacturer: str
    media: Optional[str] = None

    @field_validator("attribute", mode="before")
    @classmethod
    def attribute_must_be(cls, v: str) -> str:
        if v in {
            "smoke",
            "camera",
            "lock",
            "contact",
            "motion",
            "network_connection",
            "water_leak",
            "freeze",
        }:
            return v
        else:
            raise ValueError(
                "must be one of 'smoke', 'camera', 'lock', 'contact', 'motion', 'network_connection', 'water_leak', 'freeze'"
            )

    @model_validator(mode="after")
    def media_cannot_exist_if(self) -> Self:
        attribute = self.attribute or None
        if attribute == "camera" or not self.media and self.media is None:
            return self
        else:
            raise ValueError("cannot be used when attribute is not 'camera'")

    @model_validator(mode="after")
    def value_must_be(self) -> Self:
        try:
            attribute = self.attribute
        except KeyError:
            attribute = None
        if attribute is not None:
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
            if self.value not in value_should_be[attribute]:
                raise ValueError(
                    f"must be one of {','.join(value_should_be[attribute])}"
                )
        return self


class Person(BaseModel):
    """
    A person that is added to the alarm.

    Args:
        name (str): The name of the person.
        pin (str): Their PIN to cancel the alarm.
        phone (str): The phone number of the person.
    """

    name: str
    pin: str
    phone: str


class Alarm:
    """
    Class for Alarms.

    Danger:
        **DO NOT INSTANTIATE THIS CLASS TO CREATE AN ALARM. USE `create_alarm()` INSTEAD.**
    """

    id: str
    sandbox: bool
    active: bool = True
    static: bool
    owner_id: str
    prod_url: str
    _token: str
    _session: Optional[aiohttp.ClientSession]

    def __init__(
        self,
        alarm_id: str,
        sandbox: bool,
        owner_id: str,
        token: str,
        prod_url: Optional[str],
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.id = alarm_id
        self.sandbox = sandbox
        self.owner_id = owner_id
        self._token = token
        self._session = session

        if prod_url:
            self.prod_url = prod_url

    async def cancel(self, pin: Optional[str]) -> None:
        """Cancel an alarm.

        Args:
            pin (str, optional): PIN used to cancel the alarm. Optional.

        Raises:
            FailedRequestError: Raised when the request to cancel the alarm fails.
        """
        if not self.active:
            return  # Already canceled :)

        url = (
            SANDBOX_URL.format(path=f"/{self.id}/status")
            if self.sandbox
            else f"{self.prod_url}/{self.id}/status"
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
            await _send_request("POST", url, headers, payload, 201, self._session)
        except RetryError as e:
            raise FailedRequestError from e

        self.active = False

        return

    async def update_location(self, coordinates: Coordinates) -> None:
        """Update the location of the alarm.

        Args:
            coordinates (Coordinates): The new coordinates of the alarm.

        Raises:
            FailedRequestError: Raised when the request to update the coordinates fails.
        """
        url = (
            SANDBOX_URL.format(path=f"/{self.id}/locations")
            if self.sandbox
            else f"{self.prod_url}/{self.id}/locations"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        payload = coordinates.model_dump()

        try:
            await _send_request("POST", url, headers, payload, 201, self._session)
        except RetryError as e:
            raise FailedRequestError from e

        return

    async def create_events(self, events: list[Event]) -> None:
        """Create new events that started the alarm or occured during the alarm.

        Args:
            events (list[Event]): See Event.

        Raises:
            FailedRequestError: Raised when the request to create the event(s) has failed.
        """
        event_dicts: list[dict[str, Any]] = []
        for event in events:
            event.event_time = str(event.event_time).replace(" ", "T")
            event_dicts.append(event.model_dump())

        for event_dict in event_dicts:
            if event_dict["meta"]["device_id"] is None:
                del event_dict["meta"]["device_id"]
            if event_dict["meta"]["media"] is None:
                del event_dict["meta"]["media"]

        url = (
            SANDBOX_URL.format(path=f"/{self.id}/events")
            if self.sandbox
            else f"{self.prod_url}/{self.id}/events"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        try:
            await _send_request("POST", url, headers, event_dicts, 201, self._session)
        except RetryError as e:
            raise FailedRequestError from e

        return

    async def create_people(self, people: list[Person]) -> None:
        """Add new people to the alarm.

        Args:
            people (list[Person]): A list of people to add to the alarm

        Raises:
            FailedRequestError: Raised when the request to add the people failed.
        """
        people_dicts = [person.model_dump() for person in people]
        url = (
            SANDBOX_URL.format(path=f"/{self.id}/people")
            if self.sandbox
            else f"{self.prod_url}/{self.id}/people"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        try:
            await _send_request("POST", url, headers, people_dicts, 201, self._session)
        except RetryError as e:
            raise FailedRequestError from e

        return

    async def update_person(self, person_data: dict[str, Any]) -> None:
        """Update the alarm owner. You may only update the alarm owner right now.

        Args:
            person_data (dict[str, Any]): See [here](https://docs.noonlight.com/reference/put_alarms-alarm-id-people-person-id)

        Raises:
            FailedRequestError: Raised when the request to update the alarm owner fails.
        """
        url = (
            SANDBOX_URL.format(path=f"/{self.id}/people/{self.owner_id}")
            if self.sandbox
            else f"{self.prod_url}/{self.id}/people/{self.owner_id}"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        try:
            await _send_request("PUT", url, headers, person_data, 200, self._session)
        except RetryError as e:
            raise FailedRequestError from e

        return


async def create_alarm(
    data: AlarmData,
    server_token: str,
    sandbox: bool = True,
    client_session: Optional[aiohttp.ClientSession] = None,
) -> Alarm:
    """Create a new alarm.

    Args:
        data (AlarmData): Data for the alarm. See AlarmData.
        server_token (str): Your server token. Make sure it matches the sandbox or production token you have!
        sandbox (bool, optional): Set to False if this is a real alarm. Defaults to True.
        prod_url (str, optional): The URL of the production environment (must have https:// and must end in noonlight.com). Optional.
        client_session (aiohttp.ClientSession, optional): The client session used for requests in aiohttp

    Raises:
        InvalidURLError: Raised when the production URL provided is invalid.
        FailedRequestError: Raised when the request to create the alarm fails

    Returns:
        Alarm: The alarm
    """
    if sandbox:
        url = SANDBOX_URL.format(path="")
    else:
        url = PRODUCTION_URL.format(path="")

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {server_token}",
    }

    payload = data.model_dump()

    # Remove all values that are None
    def iterate(dictionary: dict[str, Any]) -> None:
        for key, val in dictionary.copy().items():
            if isinstance(val, dict):
                iterate(val)
            else:
                if val == "" or val is None or val is False:
                    del dictionary[key]

    iterate(payload)
    iterate(payload)

    try:
        response = await _send_request(
            "POST", url, headers, payload, 201, client_session
        )
        response_data = await response.json()
    except RetryError as e:
        raise FailedRequestError from e

    return Alarm(
        alarm_id=response_data["id"],
        sandbox=sandbox,
        owner_id=response_data["owner_id"],
        token=server_token,
        prod_url=url,
        session=client_session,
    )
