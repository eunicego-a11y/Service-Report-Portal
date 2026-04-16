"""
Unit tests for the TSP WORKWITH email → people-column resolution.

Run:
    .venv\\Scripts\\python.exe -m pytest tests/test_workwith_people.py -v
"""
import importlib
import sys
import types
import unittest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helper: reload app.monday with a fresh cache so tests don't bleed into each other
# ---------------------------------------------------------------------------
def _fresh_monday():
    """Import (or re-import) app.monday with a clean module state."""
    # Remove cached module so _email_to_id_cache is reset
    for key in list(sys.modules.keys()):
        if key in ("app.monday", "app"):
            del sys.modules[key]
    import app.monday as m       # noqa: E402
    m._email_to_id_cache = {}    # ensure cache is empty
    return m


FAKE_USERS_RESPONSE = {
    "data": {
        "users": [
            {"id": "111", "email": "alice@example.com"},
            {"id": "222", "email": "bob@example.com"},
            {"id": "333", "email": "carol@example.com"},
        ]
    }
}


class TestResolveUsersByEmail(unittest.TestCase):

    def _get_monday(self):
        """Get a fresh monday module with cache cleared."""
        import app.monday as m
        m._email_to_id_cache = {}
        return m

    def test_single_email_resolves(self):
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE):
            result = m.resolve_users_by_email(["alice@example.com"])
        self.assertEqual(result, [111])

    def test_multiple_emails_resolve(self):
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE):
            result = m.resolve_users_by_email(["bob@example.com", "carol@example.com"])
        self.assertEqual(result, [222, 333])

    def test_unknown_email_returns_empty(self):
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE):
            result = m.resolve_users_by_email(["nobody@example.com"])
        self.assertEqual(result, [])

    def test_empty_input_returns_empty_without_api_call(self):
        m = self._get_monday()
        with patch.object(m, "graphql") as mock_gql:
            result = m.resolve_users_by_email([])
        mock_gql.assert_not_called()
        self.assertEqual(result, [])

    def test_case_insensitive_match(self):
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE):
            result = m.resolve_users_by_email(["ALICE@EXAMPLE.COM"])
        self.assertEqual(result, [111])

    def test_comma_separated_string_splits_correctly(self):
        """A single string with comma-separated emails is split and resolved."""
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE):
            result = m.resolve_users_by_email(["alice@example.com, bob@example.com"])
        self.assertEqual(sorted(result), [111, 222])

    def test_mixed_known_unknown(self):
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE):
            result = m.resolve_users_by_email(["alice@example.com", "ghost@example.com"])
        self.assertEqual(result, [111])

    def test_api_error_returns_empty(self):
        m = self._get_monday()
        with patch.object(m, "graphql", side_effect=Exception("network error")):
            result = m.resolve_users_by_email(["alice@example.com"])
        self.assertEqual(result, [])

    def test_cache_used_on_second_call(self):
        """API should only be called once; second call reuses cache."""
        m = self._get_monday()
        with patch.object(m, "graphql", return_value=FAKE_USERS_RESPONSE) as mock_gql:
            m.resolve_users_by_email(["alice@example.com"])
            m.resolve_users_by_email(["bob@example.com"])
        mock_gql.assert_called_once()


class TestFormatColumnValuePeopleColumn(unittest.TestCase):
    """Verify format_column_value correctly serialises a list of person IDs."""

    def setUp(self):
        import app.monday as m
        self.m = m

    def test_list_of_ids_produces_personsAndTeams(self):
        result = self.m.format_column_value("multiple_person_mks8jn7f", [111, 222])
        self.assertEqual(result, {
            "personsAndTeams": [
                {"id": 111, "kind": "person"},
                {"id": 222, "kind": "person"},
            ]
        })

    def test_single_id_in_list(self):
        result = self.m.format_column_value("multiple_person_abc123", [333])
        self.assertEqual(result, {
            "personsAndTeams": [{"id": 333, "kind": "person"}]
        })

    def test_none_returns_none(self):
        result = self.m.format_column_value("multiple_person_mks8jn7f", None)
        self.assertIsNone(result)

    def test_empty_list_returns_none(self):
        # Empty list is falsy — format_column_value returns None (skips column)
        result = self.m.format_column_value("multiple_person_mks8jn7f", [])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
