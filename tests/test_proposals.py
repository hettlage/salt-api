from unittest.mock import MagicMock
from io import StringIO
import re
import zipfile
import salt_api.proposals
from salt_api.proposals import submit, zip_proposal_content


def test_submit_put_with_proposal_code(tmpdir, monkeypatch, uri, dummy_zip):
    """submit makes a PUT request to /proposals/[proposal_code] if called with a proposal code"""

    mock_put = MagicMock()
    monkeypatch.setattr(salt_api.proposals.session, 'put', mock_put)

    zip_file = tmpdir.join('a.zip')
    dummy_zip(zip_file, 'Test', 'b.txt')
    submit(str(zip_file), '2018-1-SCI-042')

    mock_put.assert_called()
    assert mock_put.call_args[0][0] == uri('/proposals/2018-1-SCI-042')


def test_submit_post_without_proposal_code(tmpdir, monkeypatch, uri, dummy_zip):
    """submit makes a POST request to /proposals if called without a proposal code"""

    mock_post = MagicMock()
    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)

    zip_file = tmpdir.join('a.zip')
    dummy_zip(zip_file, 'Test', 'b.txt')
    submit(str(zip_file))

    mock_post.assert_called()
    assert mock_post.call_args[0][0] == uri('/proposals')


def test_zip_file_is_submitted_by_post_as_is(tmpdir, monkeypatch, dummy_zip):
    """submit submits zip files as is."""

    mock_post = MagicMock()
    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)

    zip_path = tmpdir.join('proposal_content.zip')
    dummy_zip(zip_path, 'This is some dummy content.', 'a.txt')

    with open(zip_path, 'rb') as zip:
        submit(zip)

        assert mock_post.call_args[1]['files']['file']


def test_zip_proposal_content_includes_referenced_files(tmpdir):
    """zip_proposal_content zips the proposal content correctly."""

    xml_template = '''<?xml version="1.0"?>

<Proposal>
    <ns1:Path xmlns:ns1="http://www.saao.ac.za/ns1">{path1}</ns1:Path>
    <A>
        <B xmlns="http://www.saao.ac.za/ns2">
            <Path>
                {path2}
            </Path>
            <Path>automatic</Path> 
            <C/>
        </B>
        <ns3:Path xmlns:ns3="http://www.saao.ac.za/ns3">{path3}</ns3:Path>
        <Path>
            auto-generated
        </Path>
    </A>
</Proposal>'''

    # first referenced file
    path1 = tmpdir.join('a.pdf')
    with open(path1.strpath, 'w') as f:
        f.write('This is a fake pdf file.')

    # second referenced file
    sub_dir = tmpdir.mkdir('img')
    path2 = sub_dir.join('b.png')
    with open(path2.strpath, 'w') as f:
        f.write('This is a fake png file.')

    # third referenced file
    another_subdir = tmpdir.mkdir('spreadsheets')
    yet_another_subdir = another_subdir.mkdir('important')
    path3 = yet_another_subdir.join('c.xlsx')
    with open(path3.strpath, 'w') as f:
        f.write('This is a fake spreadsheet.')

    # create the proposal content XML...
    xml = StringIO()
    xml.write(xml_template.format(path1=path1, path2=path2, path3=path3))
    xml.seek(0)

    # ... and the corresponding zip file
    zip_filename = tmpdir.join('proposal_content.zip')
    zip_proposal_content(zip_filename, xml, str(tmpdir))

    # check the zip file content
    with zipfile.ZipFile(zip_filename, 'r') as z:
        names = z.namelist()

        assert len(names) == 4
        assert 'Proposal.xml' in names

        xml_content = z.read('Proposal.xml').decode()
        for m in re.finditer(r'Path>\s*([^<]*)\s*</[^>]+Path', xml_content, flags=re.MULTILINE):
            path = m.group(1).strip()
            print('===' + path, m.group())
            assert path in names or path in ('automatic', 'auto-generated')





