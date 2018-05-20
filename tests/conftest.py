import os
import zipfile
import pytest


BASE_URL = 'http://whatever.saao.ac.za'


@pytest.fixture(scope='session', autouse=True)
def set_base_uri():
    """Set the environment variable for overriding the base URL for the proposals API."""

    os.environ['SALT_API_PROPOSALS_BASE_URL'] = BASE_URL

    yield


@pytest.fixture()
def uri():
    """Fixture returning a function or creating a URI from a route.

    The URI returned by the function is the concatenation of the (dummy) base URI set by the set_base_uri fixture
    and the route passed as argument.

    """

    def _make_uri(endpoint):
        return BASE_URL + endpoint

    yield _make_uri


@pytest.fixture()
def dummy_zip():
    """Fixture returning a function for generating a dummy zip file.

    The function accepts the path for the zip file, text content and a filename. It creates a zip file containing
    exactly one file, which has the given filename and contains the given text content.

    """

    def _make_dummy_zip(zip, content, filename):
        with zipfile.ZipFile(zip, 'w') as f:
            f.writestr(filename, content)

    yield _make_dummy_zip

