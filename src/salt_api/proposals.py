import os
from salt_api import session


def submit(filename, proposal_code=None):
    base_url = os.environ.get('SALT_API_PROPOSALS_BASE_URL', 'http://saltapi.salt.ac.za')

    if proposal_code:
        session.put('{base_url}/proposals/{proposal_code}'.format(base_url=base_url, proposal_code=proposal_code))
    else:
        session.post('{base_url}/proposals'.format(base_url=base_url))
