import re

import pytest

from pynoonlight import InvalidURLError, _parse_tasks_prod_url


class TestInit:
    def test__invalid_missing_url_scheme(self) -> None:
        with pytest.raises(
            InvalidURLError,
            match=re.escape("Invalid or missing URL scheme (expected https)"),
        ):
            _parse_tasks_prod_url("file://test.png")

    def test__invalid_domain(self) -> None:
        with pytest.raises(InvalidURLError, match="Invalid domain"):
            _parse_tasks_prod_url("https://some.different.api.com")
