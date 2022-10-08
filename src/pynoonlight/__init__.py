"""Some parameters may appear as required. This is a [bug](https://github.com/mkdocstrings/pytkdocs/issues/123) with `mkdocstrings` (scroll down)"""

from __future__ import annotations

from typing import Any, Optional, Union

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
        async with session.request(method, url, headers=headers, json=payload) as resp:
            if resp.status != expected_code:
                raise FailedRequestError(await resp.text())

            # Cache(?) the JSON response by calling resp.json()
            await resp.json()

            return resp
    else:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=headers, json=payload
            ) as resp:
                if resp.status != expected_code:
                    raise FailedRequestError(await resp.text())

                # Cache(?) the JSON response by calling resp.json()
                await resp.json()

                return resp
