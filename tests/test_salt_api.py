from salt_api import session
from token_auth_requests import AuthSession


def test_sesssion_exists():
    """The salt_api package has a session object of type AuthSession."""

    assert type(session) == AuthSession
