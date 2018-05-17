import os
import pytest


BASE_URL = 'http://whatever.saao.ac.za'


@pytest.fixture(scope='session', autouse=True)
def set_base_uri():
    os.environ['SALT_API_PROPOSALS_BASE_URL'] = BASE_URL

    yield


@pytest.fixture()
def uri():
    def _make_uri(endpoint):
        return BASE_URL + endpoint

    yield _make_uri
