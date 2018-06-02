import os
import tempfile
import uuid
from zipfile import is_zipfile, ZipFile
from defusedxml import ElementTree
from salt_api import session


def submit(filename, proposal_code=None):
    """Submit proposal content.

    The proposal content may be a whole proposal, a list of blocks or a single block. It may be passed as a zip file
    or an XML file. If it is passed as a zip file, the content will be submitted unaltered. Otherwise it is taken to
    be an XML file and the `zip_proposal_content` function is used to generate the submitted zip file.

    If a proposal code is given, the content is submitted as a POST request; otherwise it is submitted as a PUT
    request. In both cases the content is sent as a multipart-encoded file.

    It is the user's responsibility to ensure that the submitted content is valid; this function does no checking.

    You may pass a file path or a file-like object for the filename parameter. If you pass a file-like object with XML
    content, all the file paths in the Path elements must be absolute.

    Parameters
    ----------
    filename : str or file-like
        The file with the proposal content to submit.
    proposal_code : str, optional
        The proposal code, such as "2018-1-SCI-042".

    """

    if not hasattr(filename, 'read'):
        attachments_dir = os.path.abspath(os.path.join(filename, os.path.pardir))
    else:
        attachments_dir = None

    if is_zipfile(filename):
        if hasattr(filename, 'read'):
            filename.seek(0)  # as the is_zipfile function has read in the content
            _submit(filename, attachments_dir, proposal_code)
        else:
            with open(filename, 'rb') as f:
                _submit(f, attachments_dir, proposal_code)
    else:
        if hasattr(filename, 'read'):
            filename.seek(0)  # as the is_zipfile function has read in the content
        with tempfile.TemporaryDirectory() as tmpdirname:
            zipped_filename = os.path.join(tmpdirname, 'proposal_content.zip')
            zip_proposal_content(zipped_filename, filename)
            with open(zipped_filename, 'rb') as f:
                _submit(f, attachments_dir, proposal_code)


def zip_proposal_content(zip_filename, xml, attachments_dir=None):
    """
    Zip proposal content.

    The proposal content must be passed as XML. The file is searched for Path elements. Unless the content of a Path
    element is "auto-generated" or "automatic", it is taken to be a file path. Relative file paths are assumed to be
    relative to the given attachments directory. The file path is replaced with a string of the form 'Included/[
    md5].[extension]', where [md5] and [extension] are the MD5 checksum  of the referenced file and its extension (
    such as 'pdf' or 'jpg'). The XML file and all the files referenced in Path elements are zipped. The XML file is
    named '{root}.xml' in the zip file (where {root} is the name of the root element) and the file paths of the other
    files are those in the (updated) Path elements.

    Namespaces are ignored when searching for Path elements.

    If no attachments directory is passed and the xml parameter is a file path, the parent directory of that path is
    used as the attachments directory.

    Parameters
    ----------
    zip_filename : str or file-like
        File to which the zipped content is written.
    xml : str or file-like
        File containing the proposal content XML.
    attachments_dir : str
        Directory containing the attachment files.

    """

    if hasattr(zip_filename, 'read'):
        _zip_proposal_content(zip_filename, xml, attachments_dir)
    else:
        with open(zip_filename, 'wb') as z:
            _zip_proposal_content(z, xml, attachments_dir)


def _submit(file, attachments_dir, proposal_code):
    """Submit proposal content.

    See the submit function for details.

    Parameters
    ----------
    file : file-like object
        The file with the proposal content to submit.
    attachments_dir : str, optional
        Directory containing the attachment files.
    proposal_code : str, optional
        The proposal code, such as "2018-1-SCI-042".

    """

    base_url = os.environ.get('SALT_API_PROPOSALS_BASE_URL', 'http://saltapi.salt.ac.za')

    files = {'file': file}
    if proposal_code:
        response = session.put('{base_url}/proposals/{proposal_code}'.format(base_url=base_url,
                                                                             proposal_code=proposal_code),
                               files=files)
    else:
        response = session.post('{base_url}/proposals'.format(base_url=base_url),
                                files=files)

    if response.status_code < 200 or response.status_code >= 300:
        try:
            error = response.json()['error']
        except:
            error = 'The submission failed with status code {status}'.format(status=response.status_code)
        raise Exception(error)


def _zip_proposal_content(zip_file, xml, attachments_dir):
    """Zip proposal content.

    See the zip_proposal_content function for details.

    Parameters
    ----------
    zip_file : file-like
        File to which the zipped content is written.
    xml : str or file-like
        File containing the proposal content XML.
    attachments_dir : str
        Directory containing the attachment files.

    """

    # root directory for relative file paths
    if attachments_dir:
        root_dir = attachments_dir
    elif not hasattr(xml, 'read'):
        root_dir = os.path.abspath(os.path.join(xml, os.path.pardir))
    else:
        root_dir = None

    # parse the xml for referenced files
    attachments = {}
    tree = ElementTree.parse(xml)
    root = tree.getroot()
    for e in root.iter():
        tag = (e.tag.split('}')[-1])  # element name without namespace
        if tag == 'Path':
            attachment_path = e.text.strip()
            if attachment_path in ('automatic', 'auto-generated'):
                continue

            # get the absolute path
            if not os.path.isabs(attachment_path):
                if not root_dir:
                    raise Exception('The attachment path {path} is relative, but no attachment directory was supplied'
                                    .format(path=attachment_path))
                attachment_path = os.path.join(root_dir, attachment_path)

            if not os.path.isfile(attachment_path):
                raise Exception('{path} does not exist or is no file'.format(path=attachment_path))

            # save the real path and the path for the zip file, and update the XML
            extension = os.path.splitext(attachment_path)[1]
            path_in_zip = 'Included/{uuid}{extension}'.format(uuid=uuid.uuid4(), extension=extension)
            e.text = path_in_zip
            if attachment_path not in attachments:
                attachments[attachment_path] = path_in_zip

    # create the zip file
    with ZipFile(zip_file, 'w') as z:
        root_tag = root.tag.split('}')[-1]
        z.writestr('{name}.xml'.format(name=root_tag), ElementTree.tostring(root, encoding='UTF-8'))
        for real_path, zip_path in attachments.items():
            z.write(real_path, zip_path)


def download(filename, proposal_code, content_type, name=None):
    """Download proposal content.

    The content is downloaded for the proposal with the given proposal code.

    Depending on the content_type parameter, either a whole proposal or a block is downloaded. When requesting a
    block, its name (not its block code) must be passed as the name parameter.

    The downloaded content, which is a zip file including an XML file and any files referenced therein,
    is saved in the specified file.

    Parameters
    ----------
    filename : str or file-like
        The file in which the downloaded content is stored.
    proposal_code : str
        The proposal code, such as `2018-1-SCI-042`.
    content_type : str
        The type of downloaded content. Must be either `proposal` or `block`.
    name : str, optional
        The name of the block to download. This is required when downloading a block and is ignored when downloading
         a proposal.

    """

    base_url = os.environ.get('SALT_API_PROPOSALS_BASE_URL', 'http://saltapi.salt.ac.za')

    if content_type.lower() == 'proposal':
        session.get('{base_url}/proposals/{proposal_code}'.format(base_url=base_url, proposal_code=proposal_code),
                    headers={'Content-Type': 'application/zip'})
    elif content_type.lower() == 'block':
        r = session.post('{base_url}/proposals/{proposal_code}/blocks/resolve'
                         .format(base_url=base_url,
                                 proposal_code=proposal_code),
                         json=dict(name=name))

