Sharing
=======

In Pithos, an object can be published, shared with all or restricted to be
accessible by only some users or groups.

Enter context

.. code-block:: console

    [kamaki]: file
    [file]:

Publish and unpublish
---------------------

Check publishing for objects `info.txt` and `file2upload.txt`

.. code-block:: console

    [file]: info pithos:info.txt
    cache-control:              no-cache, no-store, must-revalidate, max-age=0
    content-language:           en-us
    content-type:               plan-text/unicode
    date:                       Tue, 18 Jun 2013 12:54:14 GMT
    etag:                       d41d8cd98f00b204e9800998ecf8427e
    expires:                    Tue, 18 Jun 2013 12:54:14 GMT
    last-modified:              Mon, 17 Jun 2013 13:09:44 GMT
    server:                     gunicorn/0.14.5
    vary:                       X-Auth-Token,Accept-Language,Accept-Encoding
    x-object-hash:              e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    x-object-modified-by:       s0m3-u53r-1d
    x-object-public:            https://example.com/pithos/public/14lhJnAhVU7
    x-object-uuid:              0493f1d9-9410-4f4b-a81f-fe42f9cefa70
    x-object-version:           1085
    x-object-version-timestamp: Mon, 17 Jun 2013 13:09:44 GMT
    [file]: info file2upload.txt
    cache-control:              no-cache, no-store, must-revalidate, max-age=0
    content-language:           en-us
    content-type:               plan-text/unicode
    date:                       Tue, 18 Jun 2013 12:54:14 GMT
    etag:                       c41d8cd98f00b304e9800998ecf8427g
    expires:                    Tue, 18 Jun 2013 12:54:14 GMT
    last-modified:              Mon, 17 Jun 2013 13:09:44 GMT
    server:                     gunicorn/0.14.5
    vary:                       X-Auth-Token,Accept-Language,Accept-Encoding
    x-object-hash:              f3b0c44298fc1c149afbf4c8996df92427ae41e4649b934ca495991b7852b857
    x-object-modified-by:       s0m3-u53r-1d
    x-object-uuid:              0493f1d9-9410-4f4b-a81f-fe42f9cefa70
    x-object-version:           1085
    x-object-version-timestamp: Mon, 17 Jun 2013 13:09:44 GMT
    [file]:

.. note:: The first object contains a "x-object-public" field, therefore is
    published

Unpublish info.txt, publish file2upload.txt

.. code-block:: console

    [file]: unpublish pithos:info.txt
    [file]: publish pithos:file2upload.txt
    https://example.com/pithos/public/43gdL2df02ld3
    [file]:

Modify permissions
------------------

Check current permissions. If none set, the object is unrestricted

.. code-block:: console

    [file]: permissions get pithos:info.txt
    [file]: permissions get pithos:file2upload.txt
    read: local_user_group, write: s0m3-u53r-1d
    [file]:

Let user with id `4n07h3r-u53r-1d` to have read access to `info.txt` and write
access to `file2upload.txt`, and current user to have the opposite access

.. code-block:: console

    [file]: permissions set pithos:info.txt read=4n07h3r-u53r-1d write=s0m3-u53r-1d
    [file]: permissions set pithos:file2upload.txt write=4n07h3r-u53r-1d read=s0m3-u53r-1d

Check if everything is set correctly

.. code-block:: console

    [file]: permissions get pithos:info.txt
    read: 4n07h3r-u53r-1d
    write: s0m3-u53r-1d
    [file]: permissions get pithos:file2upload.txt
    read: s0m3-u53r-1d
    write: 4n07h3r-u53r-1d
    [file]:

Share (read permission) `info.txt` with all

.. code-block:: console

    [file]: permissions set pithos:info.txt read=*

Shared with me
--------------

List user id of users who share objects with current user

.. code-block:: console

    [file]: sharers
    5h4r1ng-u53r-1d
    4n07h3r-5h4r1ng-u53r-1d
    [file]:

List containers of `5h4r1ng-u53r-1d` and then list `image` container

.. code-block:: console

    [file]: list -A 5h4r1ng-u53r-1d
    image
    pithos
    trash
    [file]: list -A 5h4r1ng-u53r-1d image
    some-image.diskdump
    some-other-image.diskdump
    [file]:

Copy the shared image `some-image.diskdump` to current pithos container

.. code-block:: console

    [file]: copy -A 5h4r1ng-u53r-1d image:some-image.diskdump -D pithos
    [file]:

Exit context
------------

.. code-block:: console

    [file]: exit
    [kamaki]:
