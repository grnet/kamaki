Upload and Downloads
====================

The operations of uploading files to Pithos+ as objects, and downloading
objects from Pithos+ as files are presented in this section.

Upload a file or a directory
----------------------------

First, check the files at the current directory

.. code-block:: console

    $ ls -F
    file2upload.txt
    dir2upload/
    $ kamaki container list
    pithos (36MB, 5 objects)
    trash  (0B, 0 objects)

Upload `file2upload.txt` to the default container (`pithos`)

.. code-block:: console

    $ kamaki file upload file2upload.txt
    Uploading /home/someuser/file2upload.txt --> /pithos/file2upload.txt
    Done

Confirm

.. code-block:: console

    $ kamaki file list
    2 KB file2upload.txt
    2KB  info.txt
    D    video/
    11MB video/tk1.mpg
    12MB video/tk2.mpg
    13MB video/tk3.mpg

Attempt to upload a whole directory, fail and retry with correct arguments

.. code-block:: console

    $ kamaki file upload dir2upload
    /home/someuser/dir2upload is a directory
    |  Use -r to upload directory contents
    $ kamaki file upload -r dir2upload
    mkdir /pithos/dir2upload
    Uploading /home/someuser/dir2upload/large.mov --> /pithos/dir2upload/large.mov
    Uploading /home/someuser/dir2upload/small.mov --> /pithos/dir2upload/small.mov
    Done
    $ kamaki file list
    D    dir2upload/
    1GB  dir2upload/large.mov
    1MB  dir2upload/small.mov
    2 KB file2upload.txt
    2KB  info.txt
    D    video/
    11MB video/tk1.mpg
    12MB video/tk2.mpg
    13MB video/tk3.mpg

.. note:: Try to re-upload the files (use the -f option to override) and notice
    how much faster is the uploading now. Pithos+ can determine what parts
    (blocks) of the file are already uploaded so that only the missing pars
    will be uploaded.

Download an object or a directory
---------------------------------

Download object `info.txt` as a local file of the same name

.. code-block:: console

    $ kamaki file download info.txt
    Downloading /pithos/info.txt --> /home/someuser/info.txt
    Done

Download directory `video` as a local directory with its contents.
We assume that a power failure causes the operation to stop unexpectingly
before it's completed.

.. code-block:: console

    $ kamaki file download -r /pithos/video
    mkdir video
    Downloading /pithos/video/tk1.mpg --> /home/someuser/video/tk1.mpg
    Done
    Downloading /pithos/video/tk2.mpg --> /home/someuser/video/tk2.mpg
    <POWER FAILURE>

After we recover the terminal , we find out that `tk1.mpg` had been downloaded
while `tk2.mpg` download is incomplete.

.. code-block:: console

    $ ls -F video
    tk1.mpg 11MB
    tk2.mpg 4MB

Resume the download (use -f)

.. code-block:: console

    $ kamaki file download -r -f /pithos/video
    Resuming /pithos/video/tk2.mpg --> /home/someuser/video/tk2.mpg
    Downloading /pithos/video/tk3.mpg --> /home/someuser/video/tk3.mpg
    Done

.. note:: The -f/--force argument is used for resuming or overwriting a file.
    The result of using the argument is always the same: the local file will be
    the same as the remote one.

Upload all
----------

.. code-block:: console

    $ kamaki file upload -r -f . /pithos
    Done

.. note:: In this case, all files were already uploaded, so kamaki didn't have
    to upload anything. If a file was modified, kamaki would sync it with its
    remote counterpart.

.. note:: The **/pithos** argument means "from container **pithos**", which is
    the default container. If a user needs to upload everything to another
    container e.g., **images**:

    .. code-block:: console

        $ kamaki file upload -r -f . /images

Download all
------------

.. code-block:: console

    $ kamaki file download -r -f /pithos .
    Done

.. note:: Kamaki determined that all remote objects already exist as local files
    too, so there is nothing to be done. If a new remote object was created or
    an old one was modified, kamaki would have sync it with a local file.
