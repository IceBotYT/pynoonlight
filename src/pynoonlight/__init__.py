"""Some parameters may appear as required. This is a [bug](https://github.com/mkdocstrings/pytkdocs/issues/123) with `mkdocstrings` (scroll down)"""

from __future__ import annotations

from typing import Any, Optional, Union
from urllib.parse import urlparse

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential


class FailedRequestError(Exception):
    """Exception for when a request does not return the expected status code."""


class InvalidURLError(Exception):
    """Exception for when an invalid URL is received."""


@retry(stop=stop_after_attempt(5), wait=wait_exponential(max=10))
async def _send_request(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: Union[dict[Any, Any], list[dict[Any, Any]]],
    expected_code: int,
    session: Optional[aiohttp.ClientSession] = None,
) -> aiohttp.ClientResponse:
    if session:
        async with session.request(method, url, headers=headers, data=payload) as resp:
            if resp.status != expected_code:
                raise FailedRequestError(await resp.text())

            # Cache(?) the JSON response by calling resp.json()
            await resp.json()

            return resp
    else:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=headers, data=payload
            ) as resp:
                if resp.status != expected_code:
                    raise FailedRequestError(await resp.text())

                # Cache(?) the JSON response by calling resp.json()
                await resp.json()

                return resp


def _parse_prod_url(url: str) -> str:
    # Validate the prod URL
    parsed_url = urlparse(url)

    if parsed_url.scheme != "https":
        raise InvalidURLError("Invalid or missing URL scheme (expected https)")

    if not parsed_url.netloc.endswith(".noonlight.com"):
        raise InvalidURLError("Invalid domain (expected ending with noonlight.com)")
    return f"https://{parsed_url.netloc}/dispatch/v1/alarms"


def _parse_tasks_prod_url(url: str) -> str:
    parsed_url = urlparse(url)

    if parsed_url.scheme != "https":
        raise InvalidURLError("Invalid or missing URL scheme (expected https)")

    if not parsed_url.netloc.endswith(".noonlight.com"):
        raise InvalidURLError("Invalid domain (expected ending with noonlight.com)")
    return f"https://{parsed_url.netloc}/tasks/v1/verifications"
