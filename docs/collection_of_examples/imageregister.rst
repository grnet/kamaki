Image registration
==================

In Synnefo, an image is loaded as a file to the storage service (Pithos+), and
then is registered to the image service (Plankton). The image location at the
storage server is unique through out a deployment and also necessary for the
image to exist.

The image location format at user level::

    <container>:<object path>

    e.g.:

    pithos:debian_base3.diskdump

The crussial element in an image location is the container (e.g. `pithos`) and
the image object path (e.g. `debian_base3.diskdump`).


Register an image
-----------------

Let the image file `debian_base3.diskdump` be a debian image located at the
current directory.

Upload the image to container `pithos`

.. code-block:: console

    [kamaki]: file upload debian_base3.diskdump pithos
    Uploading /home/someuser/debian_base3.diskdump --> pithos:debian_base3.diskdump
    Done
    [kamaki]:

Register the image object with the name 'Debian Base Alpha'

.. code-block:: console

    [kamaki]: image register 'Debian Base Alpha' pithos:debian_base3.diskdump
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump
    name:             Debian Base Alpha
    owner:            s0m3-u53r-1d
    properties:      
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as pithos:debian_base3.diskdump.meta (version 1352)
    [kamaki]:

.. note:: The `image register` command automatically creates a meta file and
    uploads it to the same location as the image. The meta file can be
    downloaded and reused for more image registrations.

Another way to perform the two operations above is to call **/image register**
with the **\- -upload-image-file** argument. This single operation will upload
the image file and then register it as an image, and is equivalent to manually
calling **/file upload** and **/image register**.

In other words, the example that follows is equivalent to calling the two
operations above.

.. code-block:: console

        [kamaki]: image register 'Debian Base Alpha'
            pithos:debian_base3.diskdump
            --upload-image-file='debian_base3.diskdump'
        [kamaki]:


Read the metafile

.. code-block:: console

    [kamaki]: file cat pithos:debian_base3.diskdump
    {
      "status": "available", 
      "name": "Debian Base Gama", 
      "checksum": "3cb03556ec971f...e8dd6190443b560cb7", 
      "id": "7h1rd-1m4g3-1d2", 
      "updated-at": "2013-06-19 08:01:00", 
      "created-at": "2013-06-19 08:00:22", 
      "properties": {}, 
      "location": "pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump", 
      "is-public": "False", 
      "owner": "s0m3-u53r-1d", 
      "disk-format": "diskdump", 
      "size": "903471104", 
      "deleted-at": "", 
      "container-format": "bare"
    }
    [kamaki]:

Images registered by me
-----------------------

List all images, then list only images owned by the user with id s0m3-u53r-1d

.. code-block:: console

    [kamaki]: image list
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
    [kamaki]: image list --owner=s0m3-u53r-1d
    7h1rd-1m4g3-1d Debian Base Gama
        container_format: bare
        disk_format:      diskdump
        size:             474066944
        status:           available
    [kamaki]:

.. note:: To get the current user id, use `user authenticate` in kamaki

Unregister an image
-------------------

An image can be unregistered by its image id, but only if the current user is
also the image owner. In this example, there is only one image owned by current
user.

Unregister image owned by current user 

.. code-block:: console

    [kamaki]: image unregister 7h1rd-1m4g3-1d
    [kamaki]:

Check if the image is deleted

.. code-block:: console

    [kamaki]: image list --owner=s0m3-u53r-1d
    [kamaki]:

Attempt to unregister an image of another user

.. code-block:: console

    [kamaki]: image unregister f1r57-1m4g3-1d
    (403) FORBIDDEN forbidden ()
    [kamaki]:

Register with properties
------------------------

The image will be registered again, but with some custom properties::

    OS: Linux
    user: someuser

These properties can be added freely by the user, and they have no significance
for the image server, but they could be used to help using the image more
efficiently.

Attempt to register with properties

.. code-block:: console

    [kamaki]: image register 'Debian Base Gama' pithos:debian_base3.diskdump -p OS=Linux -p user=someuser
    Metadata file pithos:debian_base3.diskdump.meta already exists
    [kamaki]:

It's true that the metafile is already there, but we can override it (**-f**)

.. code-block:: console

    [kamaki]: image register -f 'Debian Base Gama' pithos:debian_base3.diskdump -p OS=Linux -p user=someuser
    [kamaki]:

Register with a meta file
-------------------------

Download the meta file of the image (it was uploaded recently)

.. code-block:: console

    [kamaki]: file download pithos:debian_base3.diskdump.meta
    Downloading pithos:debian_base3.diskdump.meta --> /home/someuser/debian_base3.diskdump.meta
    Done
    [kamaki]:

The metadata file can be edited. Let's edit the file, by adding properties::

    OS: Linux
    user: root

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
        "OS": "Linux",
        "USER": "root"
      }, 
      "location": "pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump", 
      "is-public": "False", 
      "owner": "s0m3-u53r-1d", 
      "disk-format": "diskdump", 
      "size": "903471104", 
      "deleted-at": "", 
      "container-format": "bare"
    }

.. warning:: make sure the file is in a valid json format, otherwise image
    register will fail

In the following registration, a different name will be used for the image.

Register the image (don't forget the -f parameter, to override the metafile).

.. code-block:: console

    [kamaki]: image register -f 'Debian Base Delta' pithos:debian_base3.diskdump --metafile=debian_base3.diskdump.meta
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump
    name:             Debian Base Delta
    owner:            s0m3-u53r-1d
    properties:      
            OS:     Linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as pithos:debian_base3.diskdump.meta (version 1359)
    [kamaki]:

Metadata and Property modification
----------------------------------

Image metadata and custom properties can be modified even after the image is
registered. Metadata are fixed image attributes, like name, disk format etc.
while custom properties are set by the image owner and, usually, refer to
attributes of the images OS.

Let's rename the image:

.. code-block:: console

    [kamaki]: image meta set 7h1rd-1m4g3-1d --name='Changed Name'
    [kamaki]:

If we, now, get the image metadata, we will see that the name is changed:

.. code-block:: console

    [kamaki]: image info 7h1rd-1m4g3-1d
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump
    name:             Changed Name
    owner:            s0m3-u53r-1d
    properties:      
            OS:     Linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    [kamaki]:

We can use the same idea to change the values of other metadata like disk
format, container format or status. On the other hand, we cannot modify the
id, owner, location, checksum and dates. E.g., to publish and unpublish:

.. code-block:: console

    [kamaki]: image meta set 7h1rd-1m4g3-1d --publish --name='Debian Base Gama'
    [kamaki]: image meta set 7h1rd-1m4g3-1d --unpublish
    [kamaki]:

The first call published the image (set is-public to True) and also restored
the name to "Debian Base Gama". The second one unpublished the image (set
is-public to False).

To delete metadata, use the image meta delete method:

.. code-block:: console

    [kamaki]: image meta delete 7h1rd-1m4g3-1d status
    [kamaki]:

will empty the value of "status".

These operations can be used for properties with the same semantics:

.. code-block:: console

    [kamaki]: image meta set 7h1rd-1m4g3-1d -p user=user
    [kamaki]: image info 7h1rd-1m4g3-1d
    ...
    properties:
            OS:     Linux
            USER:   user
    ...
    [kamaki]:

Just to test the feature, let's create a property "greet" with value
"hi there", and then remove it. Also, let's restore the value of USER:

.. code-block:: console

    [kamaki]: image meta set 7h1rd-1m4g3-1d -p greet='Hi there' -p user=root
    [kamaki]: image info 7h1rd-1m4g3-1d
    ...
    properties:
            OS:     Linux
            USER:   root
            GREET:  Hi there
    ...
    [kamaki]: image meta delete 7h1rd-1m4g3-1d -p greet
    [kamaki]: image info 7h1rd-1m4g3-1d
    ...
    properties:
            OS:     Linux
            USER:   root
    ...
    [kamaki]:


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

**An explicit name overrides the metafile**

Each image needs a name and this is given as the first argument of the
`register` command. This name overrides the name in the metafile.

**Reregistration is not update, but an override**

The property `user: root` won over `user: someuser`, because it was set last.
Actually, all properties were replaced by the new ones, when the image was
reregistered, and the same holds with all customizable attributes of the image.

Command line wins the metafile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's compine the metafile with a command line attribute `user: admin`

.. code-block:: console

    [kamaki]: image register -f 'Debian Base Delta' pithos:debian_base3.diskdump --metafile=debian_base3.diskdump.meta
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump
    name:             Debian Base Delta
    owner:            s0m3-u53r-1d
    properties:      
            OS:     Linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as pithos:debian_base3.diskdump.meta (version 1377)
    [kamaki]:

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

        [kamaki]: file versioning get pithos
        x-container-policy-versioning: auto
        [kamaki]:

    To set versioning to auto

    .. code-block:: console

        [kamaki]: file versioning set auto pithos
        [kamaki]:

In the above examples, the image was registered many times by overriding the
metafile. It is possible to avoid writing a metafile, as well as accessing
older versions of the file.

Register the image without uploading a metafile

.. code-block:: console

    [kamaki]: image register 'Debian Base Delta' pithos:debian_base3.diskdump --metafile=debian_base3.diskdump.meta --no-metafile-upload
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               7h1rd-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump
    name:             Debian Base Delta
    owner:            s0m3-u53r-1d
    properties:      
            OS:     Linux
            USER:   root
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    [kamaki]:

Uploaded metafiles are kept in versions, thanks to Pithos+ versioning support

.. code-block:: console

    [kamaki]: file versions pithos:debian_base3.diskdump.meta
    1352
     created: 19-06-2013 11:00:22
    1359
     created: 19-06-2013 11:01:00
    1377
     created: 19-06-2013 11:34:37
    [kamaki]:

Consult the first version of the metafile

.. code-block:: console

    [kamaki]: file cat --object-version=1352 pithos:debian_base3.diskdump.meta
    {
      "status": "available", 
      "name": "Debian Base Gama", 
      "checksum": "3cb03556ec971f...e8dd6190443b560cb7", 
      "id": "7h1rd-1m4g3-1d2", 
      "updated-at": "2013-06-19 08:01:00", 
      "created-at": "2013-06-19 08:00:22", 
      "properties": {}, 
      "location": "pithos://s0m3-u53r-1d/pithos/debian_base3.diskdump", 
      "is-public": "False", 
      "owner": "s0m3-u53r-1d", 
      "disk-format": "diskdump", 
      "size": "903471104", 
      "deleted-at": "", 
      "container-format": "bare"
    }
    [kamaki]:

Download the second version

.. code-block:: console

    [kamaki]: file download --object-version=1359 pithos:debian_base3.diskdump.meta debian_base3.diskdump.meta.v1359
    Downloading pithos:debian_base3.diskdump.meta --> /home/someuser/debian_base3.diskdump.meta.v1359
    Done
    [kamaki]:

Batch image upload
------------------

Let a directory at /home/someuser/images with a variety of images needed to be
uploaded and registered.

Batch-upload the images

.. code-block:: console

    [kamaki]: file upload -R images pithos
    mkdir pithos:images
    Uploading /home/someuser/images/debian.diskdump --> pithos:images/debian.diskdump
    Uploading /home/someuser/images/win8.diskdump --> pithos:images/win8.diskdump
    ...
    Done
    [kamaki]:

Make sure the images are uploaded to pithos:images/ remote directory object

.. code-block:: console

    [kamaki]: file list pithos:images/
    D       images/
    983MB   images/debian.diskdump
    2.2GB   images/win8.diskdump
    ...
    [kamaki]:

Use the host shell capabilities to streamline the registration, so exit kamaki

.. code-block:: console

    [kamaki]: /exit

The following is a bash script that attempts to register the already uploaded
images:

.. code-block:: bash

    #!/bin/bash

    userid=... # e.g. s0m3-u53r-1d
    container=... # e.g. pithos

    for path in images/*.diskdump; do
        location=$container:${path}
        kamaki image register $path $location
    done

Let's use the script (enriched with a separator message) to batch-register the
images (all images will be named after their relative paths).

Also, let the registered images be public (accessible to all users for creating
VMs) by adding the **--public** flag argument when calling `image register`.

.. code-block:: console

    $ for path in images/*.diskdump; do
        location=pithos:${path}
        echo "- - - Register ${path} - - -"
        kamaki image register $path $location --public
    done
    - - - Register images/debian.diskdump ---
    checksum:         3cb03556ec971f...e8dd6190443b560cb7
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               d3b14n-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/images/debian.diskdump
    name:             images/debian.diskdump
    owner:            s0m3-u53r-1d
    properties:
    size:             903471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as pithos:images/debian.diskdump.meta (version 4201)
    - - - Register images/win8.diskdump ---
    checksum:         4cb03556ec971f...e8dd6190443b560cb6
    container-format: bare
    created-at:       2013-06-19 08:00:22
    deleted-at:       
    disk-format:      diskdump
    id:               w1nd0w5-1m4g3-1d
    is-public:        False
    location:         pithos://s0m3-u53r-1d/pithos/images/win8.diskdump
    name:             images/win8.diskdump
    owner:            s0m3-u53r-1d
    properties:
    size:             2103471104
    status:           available
    updated-at:       2013-06-19 08:01:00
    Metadata file uploaded as pithos:images/debian.diskdump.meta (version 4301)
    ...
    $

.. note:: All images can be re-registered, either individually or with a batch
    process.


