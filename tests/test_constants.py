import os
from unittest.mock import patch


class TestConstantsTagPrefixParsing:
    """
    handles all tests for tag prefix parsing in constants.py
    """

    def test_parse_single_prefix_default(self) -> "None":
        """
        test that default single prefix is parsed correctly
        """
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == ["next__"]

    def test_parse_single_prefix_custom(self) -> "None":
        """
        test that custom single prefix is parsed correctly
        """
        with patch.dict(os.environ, {"GH_PACKAGE_TAG_PREFIXES": "stable__"}):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == ["stable__"]

    def test_parse_comma_separated_prefixes(self) -> "None":
        """
        test that comma-separated prefixes are parsed correctly
        """
        with patch.dict(
            os.environ, {"GH_PACKAGE_TAG_PREFIXES": "next__,stable__,previous__"}
        ):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == [
                "next__",
                "stable__",
                "previous__",
            ]

    def test_parse_comma_separated_with_spaces(self) -> "None":
        with patch.dict(
            os.environ, {"GH_PACKAGE_TAG_PREFIXES": "next__ , stable__ , previous__"}
        ):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == [
                "next__",
                "stable__",
                "previous__",
            ]

    def test_parse_newline_separated_prefixes(self) -> "None":
        """
        test that newline-separated prefixes are parsed correctly
        """
        with patch.dict(
            os.environ, {"GH_PACKAGE_TAG_PREFIXES": "next__\nstable__\nprevious__"}
        ):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == [
                "next__",
                "stable__",
                "previous__",
            ]

    def test_parse_newline_separated_with_spaces(self) -> "None":
        with patch.dict(
            os.environ,
            {"GH_PACKAGE_TAG_PREFIXES": "  next__  \n  stable__  \n  previous__  "},
        ):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == [
                "next__",
                "stable__",
                "previous__",
            ]

    def test_parse_ignores_empty_values_comma(self) -> "None":
        with patch.dict(os.environ, {"GH_PACKAGE_TAG_PREFIXES": "next__,,stable__,"}):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == ["next__", "stable__"]

    def test_parse_ignores_empty_values_newline(self) -> "None":
        with patch.dict(
            os.environ, {"GH_PACKAGE_TAG_PREFIXES": "next__\n\nstable__\n"}
        ):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == ["next__", "stable__"]

    def test_parse_prefers_newline_over_comma(self) -> "None":
        with patch.dict(
            os.environ, {"GH_PACKAGE_TAG_PREFIXES": "next__,other__\nstable__"}
        ):
            import importlib

            import src.constants

            importlib.reload(src.constants)

            assert src.constants.GH_PACKAGE_TAG_PREFIXES == [
                "next__,other__",
                "stable__",
            ]
