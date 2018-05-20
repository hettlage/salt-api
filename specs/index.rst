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

This function submits content for a proposal. The content must be a zip file or an XML file. A zip file is submitted as is. 
`filename` can be a string , a file object or a file-like object. A string is interpreted as a file path. If a file object or file-like object is passed, it must not be an XML file referencing other files.

The value of the `proposal_code` argument must be consistent with the proposal code in the submitted file content (if there is one), but this is not checked. It is required if you submit blocks or if the submitted proposal doesn't include an existing proposal code, but this is not checked.

An exception is raised if the submission fails.

`zip_proposal_content(zip, xml, parent_dir)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This function zips proposal content and files referenced therein. The zipped file can be used in a proposal content submission.

The first parameter is a file path or file-like object, to which the zipped content is written. The second parameter contains the XML content, and it may be a file path or a file-like object. The third parameter is the parent directory of the XML file.

If the parent directory is omitted and the xml parameter is a file path, the parent directory for that path is used as the parent directory.

The XML file is screened for Path elements, and the text content of each of these elements is assumed to be a file path, unless it is "auto-generated" or "automatic". Relative file paths are relative to the XML file. If the path of the XML file is undefined (as a file-like object rather than file path was passed), no relative paths may be used.

File paths in the Path elements are replaced with relative paths of the form `Included/{unique}.{ext}`, where `{unique}` and `{ext}` denote a unique random string and the file extension of the file referenced by the Path element. 

The XML file and all the files referenced in Path elements are zipped. The name of the XML file shall be that of its root element, plus the file extension 'xml'. The paths of the other files shall be those contained in the Path elements.

`download(proposal_code, content_type, name)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This function downloads content for a proposal. The content type may either be a proposal or a block. If a block is requested, its name must be supplied.

In case a block is requested, the function first resolves the name to the block's unique id and then requests the block for that id.

The requested content (which always is a zip file) is stored as a temporary file and the path of this file is returned.

An exception is raised if the download fails.

Tests
-----

The `salt_api` package shall pass the following tests.

* The package has a `session` object, which is of type 'AuthSession'.
  
The `submit` function in the proposals module shall pass the following tests.

* `submit` makes a PUT request to `/proposals/{proposal_code}` if a proposal code is passed.

* `submit` makes a POST request to `/proposals` if no proposal code is passed.

* `submit` submits the passed file as is, if it is a zip file.

* `submit` builds the correct zip file from a passed XML file, and submits that file.

* An exception is raised if the file passed to `submit` does not exist.

* An exception is raised if the file passed is an XML file and any of its Path elements contains a file path which does not exist.
  
* An exception is raised if the file passed cannot be interpreted as a zip file or an XML file.
  
* An exception is raised if the server responds with with an error code. If the server response is a JSON object with an `error` field, the value of that field is used as error message.
  
The `download` function in the `proposals` module shall pass the following tests.

* `download` makes a request to `/proposals/{proposal_code}` if the case-insensitive content type is 'proposal'. An Accept header with value `application/zip` is included in this request.

* `download` makes a GET request to `/proposals/{proposal_code}/blocks/resolve` with the query parameter `name`, the value of which is the string passed as the name argument. It parses the result as a JSON object and uses the value of the field `code` as the id in a GET request to `/proposals/{proposal_code}/blocks/{id}`. An Accept header with value `application/zip` is included in this request.
  
 * `download` saves the downloaded content as a temporary file with extension `.zip` and returns the absolute path of this file.
   
 * An exception is raised if the case-insensitive content type is neither `proposal` nor `block`.
 
 * An exception is raised if the case-insensitive content type is not `proposal` and no name is supplied.
   
 * An exception is raised if the server responds with with an error code. If the server response is a JSON object with an `error` field, the value of that field is used as error message.


Implementation
--------------
