.. toctree::
   :maxdepth: 2

salt-api
========

Introduction
------------

The salt-api package gives developers programmatic access to parts of the SALT API.

Conceptual Solution
-------------------

The `api_package` contains a HTTP session object created with the `auth_session` function of the `auth-token-requests` package.

The `proposals` module makes HTTP requests to a server with base URL `http://saltapi.salt.ac.za`. The base URL can be changed by setting the environment variable `SALT_API_PROPOSALS_BASE_URL`.

The `api.proposals` package includes the following functions.

`submit(filename, proposal_code)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This function submits content for a proposal. The content must be a zip file or an XML file. A zip file is submitted as is. An XML file is turned into a zip file with the `zip_proposal_content` function.

`filename` can be a string , a file object or a file-like object. A string is interpreted as a file path. If a file object or file-like object is passed, it must not be an XML file referencing other files via relative file paths.

The value of the `proposal_code` argument must be consistent with the proposal code in the submitted file content (if there is one), but this is not checked. The `proposal_code` argument is required if you submit blocks or if the submitted proposal doesn't include an existing proposal code, but this is not checked.

An exception is raised if the submission fails.

`zip_proposal_content(zip, xml, parent_dir)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This function zips proposal content and files referenced therein. The zipped file can be used in a proposal content submission.

The first parameter is a file path or file-like object, to which the zipped content is written. The second parameter contains the XML content, and it may be a file path or a file-like object. The third parameter is the parent directory of the XML file.

If the parent directory is omitted and the xml parameter is a file path, the parent directory for that path is used as the parent directory.

The XML file is screened for Path elements, and the text content of each of these elements is assumed to be a file path, unless it is "auto-generated" or "automatic". Relative file paths are relative to the XML file. If the path of the XML file is undefined (as a file-like object rather than file path was passed), no relative paths may be used.

File paths in the Path elements are replaced with relative paths of the form `Included/{unique}.{ext}`, where `{unique}` and `{ext}` denote a unique random string and the file extension of the file referenced by the Path element.

The XML file and all the files referenced in Path elements are zipped. The name of the XML file shall be that of its root element, plus the file extension 'xml'. The paths of the other files shall be those contained in the Path elements.

`download(filename, proposal_code, content_type, name)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This function downloads content for a proposal. The content type may either be a proposal or a block. If a block is requested, its name must be supplied.

In case a block is requested, the function first resolves the name to the block's unique id and then requests the block for that id.

The requested content (which always is a zip file) is stored in the file specified by the filename parameter. This may either be a file path or a file-like object.

An exception is raised if the download fails.

Tests
-----

`salt_api` package
~~~~~~~~~~~~~~~~~~

*Description:* The `salt_api` package has a `session` object, which is of type `AuthSession`.

*Unit test:* `test_salt_api::test_session_exists`

`submit` function in the proposals module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Description:* When the `submit` function is called with `2018-1-SCI-042` as proposal code, then it makes a PUT request to `/proposals/2018-1-SCI-042`.

*Unit test:* `test_proposals::test_submit_put_with_proposal_code`

----

*Description:* When the `submit` function is called without a proposal code, it makes a POST request to `/proposals`.

*Unit test:* `test_proposals::test_submit_post_without_proposal_code`

----

*Description:* Given that `proposal_content.zip` is a zip file, when `submit` is called with `proposal_content.zip`, then the file is submitted as is.

*Unit test:* `test_proposals::test_zip_file_is_submitted_as_is`

----

*Description:* Given that `proposal_content.xml` is an XML file, when `submit` is called with `proposal_content.xml`, then the correct zip file is built and submitted.

*Unit test:* `test_proposals::test_submit_zips_xml_content`

----

*Description:* When `submit` is called with a non-existing file, an exception is raised. The error message shall contain the file path.

*Unit test:* `test_proposals::test_submit_file_does_not_exist`

----

*Description:* Given that `proposal_content.xml` is an XML file with a Path element whose file path points to a non-existing file, when `submit` is called with `proposal_content.xml`, an exception is raised. The error message shall contain the file path.

*Unit test:* `test_proposals::test_submit_referenced_file_does_not_exist`

----

*Description:* Given that `proposal_content.xml` is an XML file with a relative file path in a Path element, when `submit` is called with `proposal_content.xml` as file or file-like object (rather than a file path), an exception is raised. The error message shall contain the file path.

*Unit test:* `test_proposals::test_zip_proposal_content_relative_path`

----

*Description:* Given that `proposal_content.xml` is an XML file with a directory's file path in a Path element, when `submit` is called with `proposal_content.xml`, an exception is raised. The error message shall contain the file path.

*Unit test:* `test_proposals::test_zip_proposal_content_referencing_directory`

----

*Description:* Given that `file` is neither a zip file nor an XML file, when `submit` is called with `file`, an exception is raised.

*Unit test:* `test_proposals::test_submit_neither_zip_nor_xml`

----

*Description:* Given that `submit` makes a server request, when the server responds with with a status code which is not between 200 and 299, an exception is raised. If the server response is a JSON object with an `error` field, the value of that field is used as error message.

*Unit test:* `test_proposals::test_submit_submission_fails_with_error_message`

`zip_proposal_content` function in the `proposals` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Description:* The XML file and the referenced files therein are zipped correctly.

*Unit test:* `test_proposals::test_zip_proposal_content_includes_referenced_files`

----

*Description:* Given the XML file is passed as a file path and given that no no value is passed for the `attachments_dir` parameter, the parent directory of the XML file is used as the attachments directory.

*Unit test:* `test_proposals::test_zip_proposal_content_takes_xml_dir_as_attachments_dir`

----

*Description:* Given that a value is passed for the `attachments_dir` parameter, this value is used as attachments directory.

*Unit test:* `test_proposals::test_zip_proposal_content_uses_attachments_dir`

----

*Description:* Given that the XML file contains a Path element with a relative file path, when this file is not passed a file path and no `attachments_dir` argument is passed, then an exception is raised. The error message contains the file path.

*Unit test:* `test_proposals::test_zip_proposal_content_relative_path`

----

*Description:* An exception is raised if a referenced file does not exist. The error message contains the file path of the missing file.

*Unit test:* `test_proposals::test_zip_proposal_content_missing_file`

----

*Description:* An exception is raised if the XML contains a Path element with a file path of a directory. The error message contains the file path.

*Unit test:* `test_proposals::test_zip_proposal_content_referencing_directory`

`download` function in the `proposals` module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Description:* `A GET request to `/proposals/{proposal_code}` is made if the case-insensitive content type is 'proposal'. An Accept header with value `application/zip` is included in this request.

*Unit test:* `test_proposals::test_download_requests_proposal`

----

*Description:* `download` makes a GET request to `/proposals/{proposal_code}/blocks/resolve` with the query parameter `name`, the value of which is the string passed as the name argument. It parses the result as a JSON object and uses the value of the field `code` as the id in a GET request to `/proposals/{proposal_code}/blocks/{id}`. An Accept header with value `application/zip` is included in this request.

*Unit test:* `test_proposals::test_download_resolves_block_name`, `test_proposals::test_download_requests_block`

----

*Description:* `download` saves the downloaded content in a given file-like object.

*Unit test:* `test_proposals::test_download_saves_downloaded_content_in_file`

----

*Description:* `download` saves the downloaded content in a file with a given file path. Existing file content is replaced.

*Unit test:* `test_proposals::test_download_saves_downloaded_content_in_file_path`

----

*Description:* The content type parameter is case-insensitive.

*Unit test:* `test_proposals::test_download_content_type_case_insensitive`

----

*Description:* An exception is raised if thecontent type is invalid. The error message includes the content type.

*Unit test:* `test_proposals::test_download_invalid_content_type`

----

*Description:* An exception is raised if the case-insensitive content type is not `proposal` and no name argument is supplied.

*Unit test:* `test_proposals::test_download_name_missing`

----

*Description:* An exception is raised if the server responds with with an error code. If the server response is a JSON object with an `error` field, the value of that field is used in error message. Otherwise the request URI is included in the error message.

*Unit test:* `test_proposals::test_download_handles_server_error_with_message`, `test_proposals::test_download_handles_server_error_without_message`

Implementation
--------------
