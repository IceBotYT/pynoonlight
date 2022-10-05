"""The tasks API."""

from __future__ import annotations

from typing import Dict, List, Optional, Union

import validators  # type: ignore # does not have types
from pydantic import BaseModel, root_validator, validator
from tenacity import RetryError

from . import FailedRequestError, _send_request

SANDBOX_URL = "https://api-sandbox.noonlight.com/tasks/v1/verifications"
PRODUCTION_URL = "https://api.noonlight.com/tasks/v1/verifications"


class PointOfInterest(BaseModel):
    """A point of interest in an image.
    The coordinate system for the points_of_interest field has the origin starting at the top left of the image.
    The positive x-axis moves right, and the positive y-axis moves down.
    Coordinates and distances must be non-negative integers.

    Args:
        x (int): The x coordinate, in pixels, for the top left corner of the bounding box. Must be a non-negative integer.
        dx (int): The distance from the x field, in pixels, for the bounding box. Must be a non-negative integer.
        y (int): The y coordinate, in pixels, for the top left corner of the bounding box. Must be a non-negative integer.
        dy (int): The distance from the y field, in pixels, for the bounding box. Must be a non-negative integer.
    """

    x: int
    dx: int
    y: int
    dy: int

    @root_validator()
    def verify_values(cls, values: dict[str, int]) -> dict[str, int]:
        if any(elem < 0 for elem in values.values()):
            raise ValueError("all dictionary values must be non-negative")
        return values


class Image(BaseModel):
    """An image that is provided to the verifier

    Args:
        url (str): The URL of the image
        media_type (str): The media type of the image, must be one of image/jpeg, image/png, or image/jpg
        points_of_interest (list[PointOfInterest]): A list of `PointOfInterest` objects
    """

    url: str
    media_type: str
    points_of_interest: List[PointOfInterest]

    @validator("url")
    def url_valid(cls, v: str) -> str:
        result = validators.url(v)

        if isinstance(result, validators.ValidationFailure):
            raise ValueError("must be a valid URL")

        return v

    @validator("media_type")
    def media_type_valid(cls, v: str) -> str:
        if v in {"image/jpeg", "image/png", "image/jpg"}:
            return v
        else:
            raise ValueError("must be one of 'image/jpeg', 'image/png', 'image/jpg'")


class Video(BaseModel):
    """A video that is provided to the verifier

    Args:
        url (str): The URL of the video
        media_type (str): The media type of the video. For MP4 videos, the alllowed type is video/mp4. For HLS, use application/x-mpegURL.
    """

    url: str
    media_type: str

    @validator("url")
    def url_valid(cls, v: str) -> str:
        result = validators.url(v)

        if isinstance(result, validators.ValidationFailure):
            raise ValueError("must be a valid URL")

        return v

    @validator("media_type")
    def media_type_valid(cls, v: str) -> str:
        if v in {"video/mp4", "application/x-mpegURL"}:
            return v
        else:
            raise ValueError("must be one of 'video/mp4', 'application/x-mpegURL'")


class VerificationData(BaseModel):
    """Data for the verifier

    Args:
        id (str, optional): The ID of the task. If not provided, it will be auto-generated.
        owner_id (str, optional): The end-user's account ID.
        location_id (str, optional): The location ID of the camera or device.
        device_id (str, optional): The device ID of the camera or device.
        prompt (str): The text displayed to the verifier. They will select `yes` or `no` in response to this prompt.
        expiration (int): The amount of time, in seconds, allotted to complete the verification task.
        attachments (Union[list[Image], Video]): The attachment shown to the verifier.
        webhook_url (str, optional): The webhook that will be invoked when the verification is complete. If none is provided, it will use the preconfigured webhook.
    """

    id: Optional[str]
    owner_id: Optional[str]
    location_id: Optional[str]
    device_id: Optional[str]
    prompt: str
    expiration: int
    attachments: Union[List[Image], Video]
    webhook_url: Optional[str]


class TaskResponse(BaseModel):
    id: str
    prompt: str
    expiration: Dict[str, int]
    attachments: Union[List[Dict[str, Union[str, Dict[str, float]]]], Dict[str, str]]
    webhook_url: str


async def create_task(
    data: VerificationData,
    server_token: str,
    sandbox: bool = True,
) -> str:
    """Create a verification request to verify a piece of media with a prompt

    Args:
        data (VerificationData): See VerificationData
        server_token (str): Your server token that matches the sandbox or prod environment
        sandbox (bool, optional): Set to False if this is a real task. Defaults to True.
        prod_url (str, optional): URL for your production environment. Required if sandbox is set to True. Defaults to None.

    Raises:
        FailedRequestError: Raised when the request to create the task fails.
        InvalidURLError: Raised when the production URL is invalid

    Returns:
        str: The task ID for the given task
    """
    if sandbox:
        url = SANDBOX_URL
    else:
        url = PRODUCTION_URL

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {server_token}",
    }

    payload = data.dict()
    payload["expiration"] = {"timeout": data.expiration}

    try:
        response = await _send_request(
            "POST", url=url, headers=headers, payload=payload, expected_code=201
        )
    except RetryError as e:
        raise FailedRequestError from e

    response_data = TaskResponse(**await response.json())
    return response_data.id
