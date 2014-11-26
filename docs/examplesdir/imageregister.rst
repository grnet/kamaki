Image registration
==================

In Synnefo, an image is loaded as a file to the storage service (Pithos+), and
then is registered to the image service (Plankton). The image location at the
storage server is unique in each a deployment and also a key for identifying
the image.

The image location format at user level::

    pithos://<user_uuid>/<container>/<object path>

    e.g., pithos://my-u53r-1d/images/debian_base3.diskdump

In **file** and **container** contexts, users may also use the shortcut:

    /<container>/<object path>

    e.g., /images/debian_base3.diskdump


Register an image
-----------------

Let the image file `debian_base3.diskdump` be a debian image located at the
current local directory.

Upload the image to container `images`

.. code-block:: console

    $ kamaki file upload debian_base3.diskdump /images

Register the image object with the name 'Debian Base Alpha'

.. code-block:: console

    kamaki image register --name 'Debian Base Alpha' --location=/images/debian_base3.diskdump
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/images/debian_base3.diskdump
    name:             Debian Base Alpha
    owner:            s0m3-u53r-1d
    properties:
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as /images/debian_base3.diskdump.meta (version 1352)

.. warning:: The image created by the above command will not be able to create
    a working virtual server, although the registration will be successful. In
    the synnefo universe, an image has to be registered along with some
    `properties <http://www.synnefo.org/docs/snf-image/latest/usage.html#image-properties>`_.

.. note:: The `image register` command automatically creates a meta file and
    uploads it to the same location as the image. The meta file can be
    downloaded and reused for more image registrations.

Here is another way to perform the two operations above: **/image register**
with the **\- -upload-image-file** argument. This single operation will upload
the image file and then register it as an image, and is equivalent to
sequentially calling **/file upload** and **/image register**.

In other words, the preceding and following command sequences are equivalent.

.. code-block:: console

        kamaki image register --name='Debian Base Alpha'
            --location=/images/debian_base3.diskdump
            --upload-image-file=debian_base3.diskdump


Read the metafile

.. code-block:: console

    kamaki file cat /images/debian_base3.diskdump.meta
    {
      "status": "available",
      "name": "Debian Base Gama",
      "checksum": "3cb03556ec971f...e8dd6190443b560cb7",
      "id": "7h1rd-1m4g3-1d2",
      "updated-at": "2013-06-19 08:01:00",
      "created-at": "2013-06-19 08:00:22",
      "properties": {},
      "location": "pithos://s0m3-u53r-1d/images/debian_base3.diskdump",
      "is-public": "False",
      "owner": "s0m3-u53r-1d",
      "disk-format": "diskdump",
      "size": "903471104",
      "deleted-at": "",
      "container-format": "bare"
    }

Images registered by me
-----------------------

List all images, then list only images owned by the user with id s0m3-u53r-1d

.. code-block:: console

    kamaki image list
    f1r57-1m4g3-1d Debian Base Alpha
        container_format: bare
        disk_format:      diskdump
        size:             474066944
        status:           available
    53c0nd-1m4g3-1d Beta Debian Base
        container_format: bare
        disk_format:      diskdump
        size:             474066944
        status:           available
    7h1rd-1m4g3-1d Debian Base Gama
        container_format: bare
        disk_format:      diskdump
        size:             474066944
        status:           available
    kamaki image list --owner=s0m3-u53r-1d
    7h1rd-1m4g3-1d Debian Base Gama
        container_format: bare
        disk_format:      diskdump
        size:             474066944
        status:           available

.. note:: To get the current user id, use `kamaki user info`

Unregister an image
-------------------

An image can be unregistered by its image id, but only if the current user is
also the image owner. In this example, there is only one image owned by current
user.

Unregister image owned by current user

.. code-block:: console

    kamaki image unregister 7h1rd-1m4g3-1d

Check if the image is deleted

.. code-block:: console

    kamaki image list --owner=s0m3-u53r-1d

Attempt to unregister an image of another user

.. code-block:: console

    kamaki image unregister f1r57-1m4g3-1d
    (403) FORBIDDEN forbidden ()

Register with properties
------------------------

.. warning:: A succesfully registered image will not be functional, if the
    image properties are not defined correctly. Read the
    `documentation <http://www.synnefo.org/docs/snf-image/latest/usage.html#image-properties>`_
    for more information.

The image will be registered again, but with some custom properties::

    OSFAMILY: linux
    USER: someuser

In theory, these properties can be added freely by the user, and they are not
required by the image server. In practice, some properties are absolutely
vital for an image to be useful, although not necessary for registration.
An attempt to register an image with custom properties:

.. code-block:: console

    kamaki image register --name='Debian Base Gama' --location=/images/debian_base3.diskdump -p OS=linux -p user=someuser
    Metadata file /images/debian_base3.diskdump.meta already exists

It's true that a metafile with this name is already there, but we can override
it (**-f**)

.. code-block:: console

    kamaki image register -f --name='Debian Base Gama' --location=/images/debian_base3.diskdump -p OS=linux -p user=someuser

Register with a meta file
-------------------------

Download the meta file of the image (it was uploaded recently)

.. code-block:: console

    kamaki file download /images/debian_base3.diskdump.meta
    Downloading /images/debian_base3.diskdump.meta --> /home/someuser/debian_base3.diskdump.meta
    Done

The metadata file can be edited. Let's edit the file to add these properties::

    OS: linux
    USER: root

The resulting file will look like this:

.. code-block:: javascript

    {
      "status": "available",
      "name": "Debian Base Gama",
      "checksum": "3cb03556ec971f...e8dd6190443b560cb7",
      "id": "7h1rd-1m4g3-1d2",
      "updated-at": "2013-06-19 08:01:00",
      "created-at": "2013-06-19 08:00:22",
      "properties": {
        "OS": "linux",
        "USER": "root"
      },
      "location": "pithos://s0m3-u53r-1d/images/debian_base3.diskdump",
      "is-public": "False",
      "owner": "s0m3-u53r-1d",
      "disk-format": "diskdump",
      "size": "903471104",
      "deleted-at": "",
      "container-format": "bare"
    }

.. warning:: make sure the file is in a valid json format, otherwise image
    register will fail

In the following registration, the image name will change to a new one.

Register the image (don't forget the -f parameter, to override the metafile).

.. code-block:: console

    kamaki image register -f --name='Debian Base Delta' --location=/images/debian_base3.diskdump --metafile=debian_base3.diskdump.meta
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/images/debian_base3.diskdump
    name:             Debian Base Delta
    owner:            s0m3-u53r-1d
    properties:
            OS:     linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as /images/debian_base3.diskdump.meta (version 1359)

Metadata and Property modification
----------------------------------

According to the OpenStack terminology, the terms **metadata** and
**properties** are two different thinks, if we talk about images. **Metadata**
are all kinds of named metadata on an image. Some of them are assigned by the
system, some others are custom and set by the users who register the image.
These custom **metadata** are called **properties**.

Image **metadata** and custom **properties** can be modified even after the
image is registered. Metadata are fixed image attributes, like name, disk
format etc. while custom properties are set by the image owner and, usually,
refer to attributes of the images OS.

Let's rename the image:

.. code-block:: console

    kamaki image modify 7h1rd-1m4g3-1d --name='Changed Name'

A look at the image metadata reveals that the name is changed:

.. code-block:: console

    kamaki image info 7h1rd-1m4g3-1d
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/images/debian_base3.diskdump
    name:             Changed Name
    owner:            s0m3-u53r-1d
    properties:
            OS:     linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    kamaki

We can use the same idea to change the values of other metadata like disk
format, container format or status. On the other hand, we cannot modify the
id, owner, location, checksum and dates. e.g., to make an image public or
private:

.. code-block:: console

    kamaki image modify 7h1rd-1m4g3-1d --public --name='Debian Base Gama'
    kamaki image modify 7h1rd-1m4g3-1d --private

The first call publishes the image (set is-public to True) and also restores
the name to "Debian Base Gama". The second one unpublishes the image (set
is-public to False).

These operations can be used for properties with the same semantics:

.. code-block:: console

    kamaki image modify 7h1rd-1m4g3-1d -p user=user
    kamaki image info 7h1rd-1m4g3-1d
    ...
    properties:
            OS:     linux
            USER:   user
    ...
    kamaki

Just to test the feature, let's create a property "greet" with value
"hi there", and then remove it. Also, let's restore the value of USER:

.. code-block:: console

    kamaki image modify 7h1rd-1m4g3-1d -p greet='Hi there' -p user=root
    kamaki image info 7h1rd-1m4g3-1d
    ...
    properties:
            OS:     linux
            USER:   root
            GREET:  Hi there
    ...
    kamaki image modify 7h1rd-1m4g3-1d --property-del greet
    kamaki image info 7h1rd-1m4g3-1d
    ...
    properties:
            OS:     linux
            USER:   root
    ...
    kamaki


Reregistration: priorities and overrides
----------------------------------------

Let's review the examples presented above::

    - Register an image with name `Debian Base Gama`
    - Unregister the image
    - Register a new image of the uploaded image object, with custom properties
    - Reregister the image with a meta file and modified properties and name

**The image id is related to the image object**

Although the image was unregistered and reregistered, the image id, that is
produced automatically at the server side, was the same. This is due to the
fact that image ids are 1 to 1 related to image objects uploaded to Pithos+

**An explicit image name overrides the metafile**

Each image needs a name and this is given as the first argument of the
`register` command. This name overrides the name in the metafile.

**Reregistration is not an update, but an override**

The property `user: root` won over `user: someuser`, because it was set last.
Actually, all properties were replaced by the new ones, when the image was
reregistered, and the same holds with all customizable attributes of the image.

Command line wins the metafile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's compine the metafile with a command line attribute `user: admin`

.. code-block:: console

    kamaki image register -f --name='Debian Base Delta' --location=/images/debian_base3.diskdump --metafile=debian_base3.diskdump.meta
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0me-u53r/images/s0m3-u53r-1d/images/debian_base3.diskdump
    name:             Debian Base Delta
    owner:            s0m3-u53r-1d
    properties:
            OS:     linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as /images/debian_base3.diskdump.meta (version 1377)
    kamaki

Although the property `OS` was read from the metafile, the property `USER` was
set by the command line property to `admin`.

.. note:: This feature allows the use of a metafile as a template for uploading
    multiple images with many common attributes but slight modifications per
    image

Multiple metafile versions
--------------------------

.. warning:: Make sure your container is set to auto, otherwise, there will be
    no object versions

    .. code-block:: console

        kamaki container info images | grep versioning
        x-container-policy-versioning: auto

    To set versioning to auto

    .. code-block:: console

        kamaki container modify images --versioning=auto

In the above examples, the image was registered many times by overriding the
metafile. It is possible to avoid writing a metafile, as well as accessing
older versions of the file.

Register the image without uploading a metafile

.. code-block:: console

    kamaki image register --name='Debian Base Delta' --location=/images/debian_base3.diskdump --metafile=debian_base3.diskdump.meta --no-metafile-upload
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r/images/s0m3-u53r-1d/images/debian_base3.diskdump
    name:             Debian Base Delta
    owner:            s0m3-u53r-1d
    properties:
            OS:     linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    kamaki

Uploaded metafiles are kept in versions, thanks to Pithos+ versioning support

.. code-block:: console

    kamaki file info /images/debian_base3.diskdump.meta --object-versions
    1352
     created: 19-06-2013 11:00:22
    1359
     created: 19-06-2013 11:01:00
    1377
     created: 19-06-2013 11:34:37
    kamaki

Consult the first version of the metafile

.. code-block:: console

    kamaki file cat --object-version=1352 /images/debian_base3.diskdump.meta
    {
      "status": "available",
      "name": "Debian Base Gama",
      "checksum": "3cb03556ec971f...e8dd6190443b560cb7",
      "id": "7h1rd-1m4g3-1d2",
      "updated-at": "2013-06-19 08:01:00",
      "created-at": "2013-06-19 08:00:22",
      "properties": {},
      "location": "pithos://s0m3-u53r/images/s0m3-u53r-1d/images/debian_base3.diskdump",
      "is-public": "False",
      "owner": "s0m3-u53r-1d",
      "disk-format": "diskdump",
      "size": "903471104",
      "deleted-at": "",
      "container-format": "bare"
    }

Download the second version

.. code-block:: console

    kamaki file download --object-version=1359 /images/debian_base3.diskdump.meta debian_base3.diskdump.meta.v1359
    Downloading /images/debian_base3.diskdump.meta --> /home/someuser/debian_base3.diskdump.meta.v1359
    Done

Batch image upload
------------------

Let a directory at /home/someuser/images with a variety of images needed to be
uploaded and registered.

Batch-upload the images

.. code-block:: console

    kamaki file upload -r images /images
    mkdir /images/images
    Uploading /home/someuser/images/debian.diskdump --> /images/images/debian.diskdump
    Uploading /home/someuser/images/win8.diskdump --> /images/images/win8.diskdump
    ...
    Done

Make sure the images are uploaded to /images/images/ remote directory object

.. code-block:: console

    kamaki file list /images/images/
    D       images/
    983MB   images/debian.diskdump
    2.2GB   images/win8.diskdump
    ...
    kamaki

Use the host shell capabilities to streamline the registration, so exit kamaki

.. code-block:: console

    kamaki /exit
