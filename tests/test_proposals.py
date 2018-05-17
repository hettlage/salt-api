from unittest.mock import MagicMock
import salt_api.proposals
from salt_api.proposals import submit


def test_submit_put_with_proposal_code(monkeypatch, uri):
    """submit makes a PUT request to /proposals/[proposal_code] if called with a proposal code"""

    mock_put = MagicMock()
    monkeypatch.setattr(salt_api.proposals.session, 'put', mock_put)

    submit('aaa', '2018-1-SCI-042')

    mock_put.assert_called()
    assert mock_put.call_args[0][0] == uri('/proposals/2018-1-SCI-042')


def test_submit_post_without_proposal_code(monkeypatch, uri):
    """submit makes a POST request to /proposals if called without a proposal code"""

    mock_post = MagicMock()
    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)

    submit('aaaa')

    mock_post.assert_called()
    assert mock_post.call_args[0][0] == uri('/proposals')

