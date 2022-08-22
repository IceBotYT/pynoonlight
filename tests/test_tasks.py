import pytest
import requests_mock
from pydantic import ValidationError

from pynoonlight import FailedRequestError
from pynoonlight.tasks import (
    SANDBOX_URL,
    Image,
    PointOfInterest,
    VerificationData,
    Video,
    create_task,
)


class TestTasks:
    def test__point_of_interest_negative(self) -> None:
        with pytest.raises(
            ValidationError, match="all dictionary values must be non-negative"
        ):
            PointOfInterest(x=-1, dx=-1, y=-1, dy=-1)

    def test__point_of_interest(self) -> None:
        poi = PointOfInterest(x=1, dx=1, y=1, dy=1)
        assert poi
        assert poi.x == 1
        assert poi.dx == 1
        assert poi.y == 1
        assert poi.dy == 1

    def test__invalid_image_url(self) -> None:
        with pytest.raises(ValidationError, match="must be a valid URL"):
            Image(
                url="example.com/image.png",
                media_type="image/png",
                points_of_interest=[PointOfInterest(x=1, dx=1, y=1, dy=1)],
            )

    def test__invalid_image_media_type(self) -> None:
        with pytest.raises(
            ValidationError,
            match="must be one of 'image/jpeg', 'image/png', 'image/jpg'",
        ):
            Image(
                url="https://example.com/image.png",
                media_type="application/json",
                points_of_interest=[PointOfInterest(x=1, dx=1, y=1, dy=1)],
            )

    def test__image(self) -> None:
        Image(
            url="https://example.com/image.png",
            media_type="image/png",
            points_of_interest=[PointOfInterest(x=1, dx=1, y=1, dy=1)],
        )

    def test__invalid_video_url(self) -> None:
        with pytest.raises(ValidationError, match="must be a valid URL"):
            Video(url="example.com/video.mp4", media_type="video/mp4")

    def test__invalid_media_type(self) -> None:
        with pytest.raises(
            ValidationError, match="must be one of 'video/mp4', 'application/x-mpegURL'"
        ):
            Video(url="https://example.com/video.mp4", media_type="application/json")

    async def test__create_task_sandbox(self) -> None:
        with requests_mock.Mocker() as m:
            m.post(SANDBOX_URL, json={"id": "test_task_id"}, status_code=201)
            await create_task(
                VerificationData(
                    prompt="Is this a person?",
                    expiration=30,
                    attachments=Video(
                        url="https://security.some-home-software.com/video_clip_192052093_49039144.mp4",
                        media_type="video/mp4",
                    ),
                ),
                server_token="some_server_token",
            )

    async def test__create_task_prod(self) -> None:
        with requests_mock.Mocker() as m:
            m.post(
                "https://some-api.noonlight.com/tasks/v1/verifications",
                json={"id": "test_task_id"},
                status_code=201,
            )
            await create_task(
                VerificationData(
                    prompt="Is this a person?",
                    expiration=30,
                    attachments=Video(
                        url="https://security.some-home-software.com/video_clip_192052093_49039144.mp4",
                        media_type="video/mp4",
                    ),
                ),
                server_token="some_server_token",
                sandbox=False,
                prod_url="https://some-api.noonlight.com",
            )

    async def test__failed_request(self) -> None:
        with requests_mock.Mocker() as m:
            m.post(
                "https://some-api.noonlight.com/tasks/v1/verifications",
                status_code=500,
            )
            with pytest.raises(FailedRequestError):
                await create_task(
                    VerificationData(
                        prompt="Is this a person?",
                        expiration=30,
                        attachments=Video(
                            url="https://security.some-home-software.com/video_clip_192052093_49039144.mp4",
                            media_type="video/mp4",
                        ),
                    ),
                    server_token="some_server_token",
                    sandbox=False,
                    prod_url="https://some-api.noonlight.com",
                )
