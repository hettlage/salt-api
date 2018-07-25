from unittest.mock import MagicMock
from io import BytesIO, StringIO
import json
import re
import zipfile
from collections import namedtuple
import httpretty
import pytest
import salt_api.proposals
from salt_api.proposals import download, submit, zip_proposal_content


# mock HTTP response object
HttpResponse = namedtuple('Response', ('status_code', 'iter_lines'))
ok_response = HttpResponse(status_code=200, iter_lines=lambda chunk_size: [b'some content'])


def test_submit_put_with_proposal_code(tmpdir, monkeypatch, uri, dummy_zip):
    """submit makes a PUT request to /proposals/[proposal_code] if called with a proposal code"""

    mock_put = MagicMock(return_value=ok_response)
    monkeypatch.setattr(salt_api.proposals.session, 'put', mock_put)

    zip_file = tmpdir.join('a.zip')
    dummy_zip(zip_file, 'Test', 'b.txt')
    submit(str(zip_file), '2018-1-SCI-042')

    mock_put.assert_called()
    assert mock_put.call_args[0][0] == uri('/proposals/2018-1-SCI-042')


def test_submit_post_without_proposal_code(tmpdir, monkeypatch, uri, dummy_zip):
    """submit makes a POST request to /proposals if called without a proposal code"""

    mock_post = MagicMock(return_value=ok_response)
    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)

    zip_file = tmpdir.join('a.zip')
    dummy_zip(zip_file, 'Test', 'b.txt')
    submit(str(zip_file))

    mock_post.assert_called()
    assert mock_post.call_args[0][0] == uri('/proposals')


def test_zip_file_is_submitted_as_is(tmpdir, monkeypatch, dummy_zip):
    """submit submits zip files as is."""

    mock_post = MagicMock(return_value=ok_response)
    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)

    zip_path = tmpdir.join('proposal_content.zip')
    dummy_zip(zip_path, 'This is some dummy content.', 'a.txt')

    with open(zip_path, 'rb') as zip:
        submit(zip)

        # a file is submitted...
        assert mock_post.call_args[1]['files']['file']

        # ... and it has the correct content.
        submitted_file = mock_post.call_args[1]['files']['file']
        submitted_file.seek(0)
        submitted_file_content = submitted_file.read()
        zip.seek(0)
        expected_file_content = zip.read()
        assert submitted_file_content == expected_file_content


def test_submit_zips_xml_content(tmpdir, monkeypatch):
    """submit zips an XML file and files referenced in it."""

    xml_template = '''<?xml version="1.0"?>

<XYZ>
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
</XYZ>'''

    # first referenced file
    pdf_content = b'This is a fake pdf file.'
    path1 = tmpdir.join('a.pdf')
    with open(path1.strpath, 'wb') as f:
        f.write(pdf_content)

    # second referenced file
    sub_dir = tmpdir.mkdir('img')
    path2 = sub_dir.join('b.png')
    png_content = b'This is a fake png file.'
    with open(path2.strpath, 'wb') as f:
        f.write(png_content)

    # third referenced file
    another_subdir = tmpdir.mkdir('spreadsheets')
    yet_another_subdir = another_subdir.mkdir('important')
    path3 = yet_another_subdir.join('c.xlsx')
    xlsx_content = b'This is a fake spreadsheet.'
    with open(path3.strpath, 'wb') as f:
        f.write(xlsx_content)

    # create the proposal content XML
    xml_file = tmpdir.join('content.xml')
    with open(xml_file.strpath, 'w') as xml:
        xml.write(xml_template.format(path1='a.pdf', path2=path2, path3=path3))

    # submit
    submitted_bytes = BytesIO()

    def mock_post(*args, **kwargs):
        submitted_bytes.write(kwargs['files']['file'].read())
        return ok_response

    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)
    submit(xml_file.strpath)

    # get the submitted file content
    expected_zip = tmpdir.join('expected.zip')
    zip_proposal_content(expected_zip.strpath, xml_file.strpath)
    with zipfile.ZipFile(submitted_bytes) as z_submitted, zipfile.ZipFile(expected_zip) as z_expected:
        assert 'XYZ.xml' in z_submitted.namelist()
        submitted_xml = None
        submitted_pdf = None
        submitted_png = None
        submitted_xlsx =  None
        for name in z_submitted.namelist():
            if name.endswith('.xml'):
                submitted_xml = z_submitted.read(name)
            if name.endswith('.pdf'):
                submitted_pdf = z_submitted.read(name)
            if name.endswith('.png'):
                submitted_png = z_submitted.read(name)
            if name.endswith('.xlsx'):
                submitted_xlsx = z_submitted.read(name)

        # check the submitted file content
        assert len(z_submitted.namelist()) == len(z_expected.namelist())
        assert b'XYZ>' in submitted_xml
        assert submitted_pdf == pdf_content
        assert submitted_png == png_content
        assert submitted_xlsx == xlsx_content


def test_submit_file_does_not_exist():
    """submit raises a meaningful exception if the submitted file does not exist."""

    with pytest.raises(FileNotFoundError) as excinfo:
        submit('/abc/xft/6786.zip')

    assert '/abc/xft/6786.zip' in str(excinfo.value)


def test_submit_referenced_file_does_not_exist():
    """submit raises a meaningful exception if a submitted XML file references a non-existing file."""

    xml = '''<?xml version="1.0"?>

<A>
    <Path>/abc/chy46/ght33.png</Path>
</A>'''

    with pytest.raises(Exception) as excinfo:
        submit(StringIO(xml))

    assert '/abc/chy46/ght33.png' in str(excinfo.value)


def test_submit_neither_zip_nor_xml():
    """submit raises an exception if the submitted file is no zip file and cannot be parsed as XML."""

    with pytest.raises(Exception):
        submit(StringIO('This is not XML.'))


@httpretty.httprettified
@pytest.mark.parametrize('status', [400, 401, 403, 500])
def test_submit_submission_fails(tmpdir, dummy_zip, uri, status):
    """submit raises an exception if the submission fails."""

    httpretty.register_uri(httpretty.POST,
                           uri=uri('/proposals'),
                           status=status)

    zip_file = tmpdir.join('a.zip')
    dummy_zip(zip_file.strpath, 'Test', 'b.txt')
    with pytest.raises(Exception) as excinfo:
        submit(zip_file.strpath)

    assert str(status) in str(excinfo.value)


@httpretty.httprettified
@pytest.mark.parametrize('status', [400, 401, 403, 500])
def test_submit_submission_fails_with_error_message(tmpdir, dummy_zip, uri, status):
    """submit raises an exception with the error message if the submission fails with an error message."""

    error_message = 'This is an error.'
    httpretty.register_uri(httpretty.POST,
                           uri=uri('/proposals'),
                           body=json.dumps(dict(error=error_message)),
                           status=status)

    zip_file = tmpdir.join('a.zip')
    dummy_zip(zip_file.strpath, 'Test', 'b.txt')
    with pytest.raises(Exception) as excinfo:
        submit(zip_file.strpath)

    assert error_message in str(excinfo.value)


def test_zip_proposal_content_includes_referenced_files(tmpdir):
    """zip_proposal_content zips the proposal content correctly."""

    xml_template = '''<?xml version="1.0"?>

<XYZ>
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
</XYZ>'''

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

        # XNL file and 3 attachments
        assert 'XYZ.xml' in names
        assert len(names) == 4

        # paths were updated correctly
        xml_content = z.read('XYZ.xml').decode()
        for m in re.finditer(r'Path>\s*([^<]*)\s*</[^>]+Path', xml_content, flags=re.MULTILINE):
            path = m.group(1).strip()
            assert path in names or path in ('automatic', 'auto-generated')

            # content of attachment is correct
            real_path = None
            if path.endswith('.pdf'):
                real_path = path1.strpath
            elif path.endswith('.png'):
                real_path = path2.strpath
            elif path.endswith('.xlsx'):
                real_path = path3.strpath
            else:
                continue  # the path is "automatic" or "auto-generated"
            with open(real_path, 'rb') as f:
                assert z.read(path) == f.read()


def test_zip_proposal_content_takes_xml_dir_as_attachments_dir(tmpdir):
    """zip_proposal_content takes the XML file's parent directory as the default for the attachments directory."""

    xml_template = '''<?xml version="1.0"?>

<Proposal>
    <ns1:Path xmlns:ns1="http://www.saao.ac.za/ns1">{path}</ns1:Path>
</Proposal>'''

    # referenced file
    attachment_path = tmpdir.join('a.pdf')
    with open(attachment_path.strpath, 'w') as f:
        f.write('This is a fake pdf file.')

    # create the proposal content xml file
    xml_file = tmpdir.join('proposal.xml')
    with open(xml_file.strpath, 'w') as f:
        f.write(xml_template.format(path='a.pdf'))

    # ... and the corresponding zip file
    zip_filename = tmpdir.join('proposal_content.zip')
    zip_proposal_content(zip_filename, xml_file.strpath)

    # check the zip file content
    with zipfile.ZipFile(zip_filename, 'r') as z:
        names = z.namelist()

        # XML file and attachment
        assert len(names) == 2
        assert 'Proposal.xml' in names

        # path was updated correctly
        xml_content = z.read('Proposal.xml').decode()
        m = re.search(r'Path>\s*([^<]*)\s*</[^>]+Path', xml_content, flags=re.MULTILINE)
        path = m.group(1).strip()
        assert path in z.namelist()

        # content of attachment is correct
        with open(attachment_path.strpath, 'rb') as f:
            assert z.read(path) == f.read()


def test_zip_proposal_content_uses_attachments_dir(tmpdir):
    """zip_proposal_content uses the attachments directory passed to it."""

    xml_template = '''<?xml version="1.0"?>

<Proposal>
    <ns1:Path xmlns:ns1="http://www.saao.ac.za/ns1">{path}</ns1:Path>
</Proposal>'''

    # referenced file
    dir1 = tmpdir.mkdir('dir1')
    attachment_path = dir1.join('a.pdf')
    with open(attachment_path.strpath, 'w') as f:
        f.write('This is a fake pdf file.')

    # create the proposal content xml file
    dir2 = tmpdir.mkdir('dir2')
    xml_file = dir2.join('proposal.xml')
    with open(xml_file.strpath, 'w') as f:
        f.write(xml_template.format(path='a.pdf'))

    # ... and the corresponding zip file
    zip_filename = tmpdir.join('proposal_content.zip')
    zip_proposal_content(zip_filename, xml_file.strpath, dir1.strpath)

    # check the zip file content
    with zipfile.ZipFile(zip_filename, 'r') as z:
        names = z.namelist()

        # XML file and attachment
        assert len(names) == 2
        assert 'Proposal.xml' in names

        # path was updated correctly
        xml_content = z.read('Proposal.xml').decode()
        m = re.search(r'Path>\s*([^<]*)\s*</[^>]+Path', xml_content, flags=re.MULTILINE)
        path = m.group(1).strip()
        assert path in z.namelist()

        # content of attachment is correct
        with open(attachment_path.strpath, 'rb') as f:
            assert z.read(path) == f.read()


def test_zip_proposal_content_relative_path(tmpdir):
    """zip_proposal_content must raise a meaningful exception if the XML contains a relative file path in one of its
    Path elements."""

    xml = '''<?xml version="1.0"?>

<Proposal>
    <ns1:Path xmlns:ns1="http://www.saao.ac.za/ns1">a/relative/path</ns1:Path>
</Proposal>'''

    zip_filename = tmpdir.join('proposal_content.zip')

    with pytest.raises(Exception) as excinfo:
        zip_proposal_content(zip_filename, StringIO(xml))

    assert 'a/relative/path' in str(excinfo.value)


def test_zip_proposal_content_missing_file(tmpdir):
    """zip_proposal_content must raise a meaningful exception if the XML references a file that does not exist."""

    xml = '''<?xml version="1.0"?>

<Proposal>
    <ns1:Path xmlns:ns1="http://www.saao.ac.za/ns1">/absolute/path</ns1:Path>
</Proposal>'''

    zip_filename = tmpdir.join('proposal_content.zip')

    with pytest.raises(Exception) as excinfo:
        zip_proposal_content(zip_filename, StringIO(xml))

    assert 'does not exist' in str(excinfo.value)


def test_zip_proposal_content_referencing_directory(tmpdir):
    """zip_proposal_content must raise a meaningful exception if the XML references a directory."""

    dir = str(tmpdir)
    xml = '''<?xml version="1.0"?>

<Proposal>
    <ns1:Path xmlns:ns1="http://www.saao.ac.za/ns1">{dir}</ns1:Path>
</Proposal>'''.format(dir=dir)

    zip_filename = tmpdir.join('proposal_content.zip')

    with pytest.raises(Exception) as excinfo:
        zip_proposal_content(zip_filename, StringIO(xml))

    assert dir in str(excinfo.value)


def test_download_requests_proposal(monkeypatch, uri):
    """download requests a proposal if 'proposal' is passed as the content type."""

    proposal_code = '2018-1-SCI-042'

    mock_get = MagicMock(return_value=ok_response)
    monkeypatch.setattr(salt_api.proposals.session, 'get', mock_get)

    download(BytesIO(), proposal_code=proposal_code, content_type='proposal')

    assert mock_get.call_args[0][0] == uri('/proposals/{proposal_code}'.format(proposal_code=proposal_code))
    assert mock_get.call_args[1]['headers']['Content-Type'] == 'application/zip'


@httpretty.httprettified
def test_download_resolves_block_name(monkeypatch, uri):
    """download resolves a block name."""

    proposal_code = '2018-1-SCI-042'
    block_name = 'My Shiny Block'

    mock_get = MagicMock(ok_response)
    mock_post = MagicMock(ok_response)
    monkeypatch.setattr(salt_api.proposals.session, 'get', mock_get)
    monkeypatch.setattr(salt_api.proposals.session, 'post', mock_post)

    download(BytesIO, proposal_code=proposal_code, content_type='block', name=block_name)

    assert mock_post.call_args[0][0] == uri('/proposals/{proposal_code}/blocks/resolve'
                                            .format(proposal_code=proposal_code))
    assert mock_post.call_args[1]['json'] == dict(name=block_name)


@httpretty.httprettified
def test_download_requests_block(monkeypatch, uri):
    """download requests a block if 'block' is passed as the content type."""

    proposal_code = '2018-1-SCI-042'
    block_code = 'xfgt5hj-9io'

    httpretty.register_uri(httpretty.POST,
                           uri=uri('/proposals/{proposal_code}/blocks/resolve'.format(proposal_code=proposal_code)),
                           body=json.dumps(dict(code=block_code)))

    mock_get = MagicMock()
    monkeypatch.setattr(salt_api.proposals.session, 'get', mock_get)

    download(BytesIO(), proposal_code=proposal_code, content_type='block', name='My Shiny Block')

    assert mock_get.call_args[0][0] == uri('/proposals/{proposal_code}/blocks/{block_code}'
                                           .format(proposal_code=proposal_code, block_code=block_code))
    assert mock_get.call_args[1]['headers']['Content-Type'] == 'application/zip'


@httpretty.httprettified
def test_download_saves_downloaded_content_in_file(tmpdir, uri):
    """download saves the downloaded content in the given file object."""

    proposal_code = '2018-1-SCI-042'
    block_code = 'xghu-78-opi'
    downloaded_content = b'This is some dummy download content.'
    httpretty.register_uri(httpretty.POST,
                           uri=uri('/proposals/{proposal_code}/blocks/resolve'.format(proposal_code=proposal_code)),
                           body=json.dumps(dict(code=block_code)))
    httpretty.register_uri(httpretty.GET,
                           uri=uri('/proposals/{proposal_code}/blocks/{block_code}'
                                   .format(proposal_code=proposal_code, block_code=block_code)),
                           body = downloaded_content)

    filename = tmpdir.join('download.zip')
    with open(filename, 'wb') as f:
        download(f, proposal_code, 'Block', 'ABC123')

    with open(filename, 'rb') as f:
        assert f.read() == downloaded_content


@pytest.mark.parametrize('content_type', ('proposal', 'PROPOSAL', 'Proposal', 'pRoPOsAL'))
def test_download_content_type_case_insensitive(tmpdir, monkeypatch, uri, content_type):
    # The content type is case-insensitive.

    proposal_code = '2018-1-SCI-042'

    mock_get = MagicMock(return_value=ok_response)
    monkeypatch.setattr(salt_api.proposals.session, 'get', mock_get)

    download(BytesIO(), proposal_code=proposal_code, content_type=content_type)

    assert mock_get.call_args[0][0] == uri('/proposals/{proposal_code}'.format(proposal_code=proposal_code))
    assert mock_get.call_args[1]['headers']['Content-Type'] == 'application/zip'

@httpretty.httprettified
def test_download_saves_downloaded_content_in_file_path(tmpdir, uri):
    """download saves the downloaded content in the given file-like object. Existing file content is replaced."""

    # set up file content, so that we can test it is replaced
    filename = tmpdir.join('download.zip')
    with open(filename, 'wb') as f:
        f.write(b'This is content that shall be replaced.')

    # download the proposal content
    proposal_code = '2018-1-SCI-042'
    block_code = 'xghu-78-opi'
    downloaded_content = b'This is some dummy download content.'
    httpretty.register_uri(httpretty.POST,
                           uri=uri('/proposals/{proposal_code}/blocks/resolve'.format(proposal_code=proposal_code)),
                           body=json.dumps(dict(code=block_code)))
    httpretty.register_uri(httpretty.GET,
                           uri=uri('/proposals/{proposal_code}/blocks/{block_code}'
                                   .format(proposal_code=proposal_code, block_code=block_code)),
                           body = downloaded_content)

    download(filename, proposal_code, 'Block', 'ABC123')

    # check that the proposal content has replaced the existing content
    with open(filename, 'rb') as f:
        assert f.read() == downloaded_content


def test_download_invalid_content_type(tmpdir):
    # download raises a meaningful ValueError if it is called with an invalid content type

    filename = tmpdir.join('download.zip')
    proposal_code = '2018-1-SCI-042'
    content_type = 'vhsfgh67ru'
    with pytest.raises(ValueError) as excinfo:
        download(filename, proposal_code, content_type)

    assert content_type in str(excinfo.value)


def test_download_name_missing(tmpdir):
    # download raises a meaningful exception if the content type is not 'proposal' and no name argument is supplied.

    filename = tmpdir.join('download.zip')
    proposal_code = '2018-1-SCI-042'
    content_type = 'vhsfgh67ru'
    with pytest.raises(ValueError) as excinfo:
        download(filename, proposal_code, 'block')

    assert content_type in str(excinfo.value)
