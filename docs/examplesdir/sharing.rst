Sharing
=======

In Pithos, an object can be published, shared with all or restricted to be
accessible by only some users or groups.

Publish and unpublish
---------------------

Get publishing information for objects `info.txt` and `file2upload.txt`

.. code-block:: console

    $ kamaki file info info.txt
    cache-control:              no-cache, no-store, must-revalidate, max-age=0
    content-language:           en-us
    content-type:               plan-text/unicode
    date:                       Tue, 18 Jun 2013 12:54:14 GMT
    etag:                       d41d8cd98f00b204e9800998ecf8427e
    expires:                    Tue, 18 Jun 2013 12:54:14 GMT
    last-modified:              Mon, 17 Jun 2013 13:09:44 GMT
    server:                     gunicorn/0.14.5
    vary:                       X-Auth-Token,Accept-Language,Accept-Encoding
    x-object-hash:              e3b0c44298fc1c14....ca495991b7852b855
    x-object-modified-by:       s0m3-u53r-1d
    x-object-public:            https://example.com/pithos/public/14lhJnAhVU7
    x-object-uuid:              0493f1d9-9410-4f4b-a81f-fe42f9cefa70
    x-object-version:           1085
    x-object-version-timestamp: Mon, 17 Jun 2013 13:09:44 GMT
    $ kamaki file info file2upload.txt
    cache-control:              no-cache, no-store, must-revalidate, max-age=0
    content-language:           en-us
    content-type:               plan-text/unicode
    date:                       Tue, 18 Jun 2013 12:54:14 GMT
    etag:                       c41d8cd98f00b304e9800998ecf8427g
    expires:                    Tue, 18 Jun 2013 12:54:14 GMT
    last-modified:              Mon, 17 Jun 2013 13:09:44 GMT
    server:                     gunicorn/0.14.5
    vary:                       X-Auth-Token,Accept-Language,Accept-Encoding
    x-object-hash:              f3b0c44298fc1c149af...a495991b7852b857
    x-object-modified-by:       s0m3-u53r-1d
    x-object-uuid:              0493f1d9-9410-4f4b-a81f-fe42f9cefa70
    x-object-version:           1085
    x-object-version-timestamp: Mon, 17 Jun 2013 13:09:44 GMT

.. note:: The first object contains an "x-object-public" field, therefore is
    published. Alternatively, use the "--sharing" argument

    .. code-block:: console

        $ kamaki file info info.txt --sharing
        public url: https://example.com/pithos/public/14lhJnAhVU7

Unpublish info.txt, publish file2upload.txt

.. code-block:: console

    $ kamaki file unpublish /pithos/info.txt
    $ kamaki file publish /pithos/file2upload.txt
    https://example.com/pithos/public/43gdL2df02ld3

Modify permissions
------------------

Get current permissions. If none set, the object inherits permissions from the
container and account (in that order).

.. code-block:: console

    $ kamaki file info info.txt --sharing
    public url: https://example.com/pithos/public/14lhJnAhVU7
    $ kamaki file info file2upload.txt --sharing
    read: local_user_group, write: s0m3-u53r-1d
    public url: https://example.com/pithos/public/43gdL2df02ld3

Let user with id `4n07h3r-u53r-1d` to have read access to `info.txt` and write
access to `file2upload.txt`, and current user to have the opposite access

.. code-block:: console

    $ kamaki file modify info.txt --read-permission=4n07h3r-u53r-1d --write-permission=s0m3-u53r-1d
    $ kamaki file modify file2upload.txt --write-permission=4n07h3r-u53r-1d --read-permission=s0m3-u53r-1d

Share (read permission) `info.txt` with all

.. code-block:: console

    $ kamaki file modify info.txt --read-permission=*

Shared with me
--------------

List users who share objects with current user

.. code-block:: console

    $ kamaki sharer list
    5h4r1ng-u53r-1d (somesharinguser@example.com)
    4n07h3r-5h4r1ng-u53r-1d (anothersharinguser@example.com)

List containers of `5h4r1ng-u53r-1d` and then list `images` container

.. code-block:: console

    $ kamaki container list -A 5h4r1ng-u53r-1d
    images
    pithos
    trash
    $ kamaki file list -A 5h4r1ng-u53r-1d /images
    some-image.diskdump
    some-other-image.diskdump

Copy the shared image `some-image.diskdump` to current pithos container

.. code-block:: console

    $ kamaki file copy -A 5h4r1ng-u53r-1d /images/some-image.diskdump /pithos

    OR

    $ kamaki file copy pithos://5h4r1ng-u53r-1d/images/some-image.diskdump /pithos
