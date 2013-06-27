Upload and Downloads
====================

The operations of uploading files to pithos as objects, and downloading
objects from pithos as a file are presented in this section.

Enter file context

.. code-block:: console

    $ kamaki
    [kamaki]: file
    [file]:

Upload a file or a directory
----------------------------

First, check the files at the current directory

.. code-block:: console

    [file]: ! ls -F
    file2upload.txt
    dir2upload/
    [file]: list
    pithos (36MB, 5 objects)
    trash  (0B, 0 objects)

.. note:: the `!` symbol is used to run host shell commands

Upload `file2upload.txt` to remote container `pithos`

.. code-block:: console

    [file]: upload file2upload.txt pithos
    Uploading /home/someuser/file2upload.txt --> pithos:file2upload.txt
    Done

Check remote container `pithos` to confirm

.. code-block:: console

    [file]: list pithos
    2 KB file2upload.txt
    2KB  info.txt
    D    video/
    11MB video/tk1.mpg
    12MB video/tk2.mpg
    13MB video/tk3.mpg
    [file]:

Attempt to upload a whole directory, fail and retry with correct arguments

.. code-block:: console

    [file]: upload dir2upload pithos
    /home/someuser/dir2upload is a directory
    |  Use -R to upload directory contents
    [file]: upload -R dirupload pithos
    mkdir pithos:dir2upload
    Uploading /home/someuser/dir2upload/large.mov --> pithos:dir2upload/large.mov
    Uploading /home/someuser/dir2upload/small.mov --> pithos:dir2upload/small.mov
    Done
    [file]: list pithos
    D    dir2upload/
    1GB  dir2upload/large.mov
    1MB  dir2upload/small.mov
    2 KB file2upload.txt
    2KB  info.txt
    D    video/
    11MB video/tk1.mpg
    12MB video/tk2.mpg
    13MB video/tk3.mpg
    [file]:

.. note:: Try to reupload the files (use the -f option to override) and notice
    how much faster is the uploading now. Pithos can determine what parts of
    the file are already uploaded so that kamaki won't attempt to upload them
    again.

Download an object or a directory
---------------------------------

Download object `info.txt` as a local file of the same name

.. code-block:: console

    [file]: download pithos:info.txt
    Downloading pithos:info.txt --> /home/someuser/info.txt
    Donw
    [file]:

Download directory `video` as a local directory with its contents.
We will suppose that a power failure causes the operation to stop unexpectingly
before it's completed.

.. code-block:: console

    [file]: download -R pithos:video
    mkdir video
    Downloading pithos:video/tk1.mpg --> /home/someuser/video/tk1.mpg
    Done
    Downloading pithos:video/tk2.mpg --> /home/someuser/video/tk2.mpg
    <POWER FAILURE>

After we recover the terminal and load kamaki in `file` context, we find out
that `tk1.mpg` had been downloaded while `tk2.mpg` download is incomplete.

.. code-block:: console

    $ ls -F video
    tk1.mpg 11MB
    tk2.mpg 4MB
    $

Let's resume the download uperations (use -r)

.. code-block:: console

    [file]: download -R pithos:video
    Directory video already exists
    | Use -r to resume
    [file]: download -R -r pithos:video
    Resuming pithos:video/tk2.mpg --> /home/someuser/video/tk2.mpg
    Downloading pithos:video/tk3.mpg --> /home/someuser/video/tk3.mpg
    Done
    [file]:

Upload all
----------

.. code-block:: console

    [file]: upload -R -f . pithos
    Done
    [file]:

.. note:: Kamaki calculated that all information is already uploaded, there was
    nothing to be done. If there is was a new or modified file, kamaki would
    detect and upload it.

Download all
------------

.. code-block:: console

    [file]: download -R -r pithos
    Done
    [file]:

.. note:: Kamaki determined that all files have already been calculated. This
    operation examines all local files against the remote objects and
    downloads only missing data.

Exit Context
------------

.. code-block:: console

    [file]: exit
    [kamaki]:
