# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import gevent
import gevent.monkey
# Monkey-patch everything for gevent early on
gevent.monkey.patch_all()

import hashlib, os, gevent.pool

from time import time

from .storage import StorageClient, ClientError
from .utils import path4url, params4url, prefix_keys, filter_in, filter_out, list2str


def pithos_hash(block, blockhash):
    h = hashlib.new(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()

class PithosClient(StorageClient):
    """GRNet Pithos API client"""

    def __init__(self, base_url, token, account=None, container = None):
        super(PithosClient, self).__init__(base_url, token,
            account = account, container = container)
        self.async_pool = None

    def account_head(self, until = None,
        if_modified_since=None, if_unmodified_since=None, *args, **kwargs):
        """ Full Pithos+ HEAD at account level
        --- request parameters ---
        @param until (string): optional timestamp
        --- --- optional request headers ---
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_account()
        path = path4url(self.account)

        path += '' if until is None else params4url({'until':until})
        self.set_header('If-Modified-Since', if_modified_since)
        self.set_header('If-Unmodified-Since', if_unmodified_since)

        success = kwargs.pop('success', 204)
        return self.head(path, *args, success=success, **kwargs)

    def account_get(self, limit=None, marker=None, format='json', show_only_shared=False, until=None,
        if_modified_since=None, if_unmodified_since=None, *args, **kwargs):
        """  Full Pithos+ GET at account level
        --- request parameters ---
        @param limit (integer): The amount of results requested (server will use default value if None)
        @param marker (string): Return containers with name lexicographically after marker
        @param format (string): reply format can be json or xml (default: json)
        @param shared (bool): If true, only shared containers will be included in results
        @param until (string): optional timestamp
        --- --- optional request headers ---
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_account()

        param_dict = {} if format is None else dict(format=format)
        if limit is not None:
            param_dict['limit'] = limit
        if marker is not None:
            param_dict['marker'] = marker
        if show_only_shared:
            param_dict['shared'] = None
        if until is not None:
            param_dict['until'] = until

        path = path4url(self.account)+params4url(param_dict)
        self.set_header('If-Modified-Since', if_modified_since)
        self.set_header('If-Unmodified-Since', if_unmodified_since)

        success = kwargs.pop('success', (200, 204))
        return self.get(path, *args, success = success, **kwargs)

    def account_post(self, update=True,
        groups={}, metadata=None, quota=None, versioning=None, *args, **kwargs):
        """ Full Pithos+ POST at account level
        --- request parameters ---
        @param update (bool): if True, Do not replace metadata/groups
        --- request headers ---
        @groups (dict): Optional user defined groups in the form
                    {   'group1':['user1', 'user2', ...], 
                        'group2':['userA', 'userB', ...], ...
                    }
        @metadata (dict): Optional user defined metadata in the form
                    {   'name1': 'value1',
                        'name2': 'value2', ...
                    }
        @param quota(integer): If supported, sets the Account quota
        @param versioning(string): If supported, sets the Account versioning
                    to 'auto' or some other supported versioning string
        """
        self.assert_account()
        path = path4url(self.account) + params4url({'update':None}) if update else ''
        for group, usernames in groups.items():
            userstr = ''
            dlm = ''
            for user in usernames:
                userstr = userstr + dlm + user
                dlm = ','
            self.set_header('X-Account-Group-'+group, userstr)
        if metadata is not None:
            for metaname, metaval in metadata.items():
                self.set_header('X-Account-Meta-'+metaname, metaval)
        self.set_header('X-Account-Policy-Quota', quota)
        self.set_header('X-Account-Policy-Versioning', versioning)

        success = kwargs.pop('success', 202)
        return self.post(path, *args, success=success, **kwargs)

    def container_head(self, until=None,
        if_modified_since=None, if_unmodified_since=None, *args, **kwargs):
        """ Full Pithos+ HEAD at container level
        --- request params ---
        @param until (string): optional timestamp
        --- optional request headers --- 
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_container()
        path = path4url(self.account, self.container)
        path += '' if until is None else params4url(dict(until=until))
        self.set_header('If-Modified-Since', if_modified_since)
        self.set_header('If-Unmodified-Since', if_unmodified_since)
        success = kwargs.pop('success', 204)
        return self.head(path, *args, success=success, **kwargs)

    def container_get(self, limit = None, marker = None, prefix=None, delimiter=None, path = None,
        format='json', meta=[], show_only_shared=False, until=None,
        if_modified_since=None, if_unmodified_since=None, *args, **kwargs):
        """ Full Pithos+ GET at container level
        --- request parameters ---
        @param limit (integer): The amount of results requested (server qill use default value if None)
        @param marker (string): Return containers with name lexicographically after marker
        @param prefix (string): Return objects starting with prefix
        @param delimiter (string): Return objects up to the delimiter
        @param path (string): assume prefix = path and delimiter = / (overwrites prefix
        and delimiter)
        @param format (string): reply format can be json or xml (default: json)
        @param meta (list): Return objects that satisfy the key queries in the specified
        comma separated list (use <key>, !<key> for existence queries, <key><op><value>
        for value queries, where <op> can be one of =, !=, <=, >=, <, >)
        @param shared (bool): If true, only shared containers will be included in results
        @param until (string): optional timestamp
        --- --- optional request headers ---
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_container()

        param_dict = {} if format is None else dict(format=format)
        if limit is not None:
            param_dict['limit'] = limit
        if marker is not None:
            param_dict['marker'] = marker
        if path is not None:
                param_dict['path'] = path
        else:
            if prefix is not None:
                param_dict['prefix'] = prefix
            if delimiter is not None:
                param_dict['delimiter'] = delimiter
        if show_only_shared:
            param_dict['shared'] = None
        if meta is not None and len(meta) > 0:
            param_dict['meta'] = list2str(meta)
        if until is not None:
            param_dict['until'] = until
        path = path4url(self.account, self.container)+params4url(param_dict)
        self.set_header('If-Modified-Since', if_modified_since)
        self.set_header('If-Unmodified-Since', if_unmodified_since)
        success = kwargs.pop('success', 200)
        return self.get(path, *args, success=success, **kwargs)

    def container_put(self, quota=None, versioning=None, metadata=None, *args, **kwargs):
        """ Full Pithos+ PUT at container level
        --- request headers ---
        @param quota (integer): Size limit in KB
        @param versioning (string): 'auto' or other string supported by server
        @metadata (dict): Optional user defined metadata in the form
        {   'name1': 'value1',
        'name2': 'value2', ...
        }
        """
        self.assert_container()
        path = path4url(self.account, self.container)
        if metadata is not None:
            for metaname, metaval in metadata.items():
                self.set_header('X-Container-Meta-'+metaname, metaval)
        self.set_header('X-Container-Policy-Quota', quota)
        self.set_header('X-Container-Policy-Versioning', versioning)
        success = kwargs.pop('success',(201, 202))
        return self.put(path, *args, success=success, **kwargs)

    def container_post(self, update=True, format='json',
        quota=None, versioning=None, metadata=None, content_type=None, content_length=None,
        transfer_encoding=None, *args, **kwargs):
        """ Full Pithos+ POST at container level
        --- request params ---
        @param update (bool):  if True, Do not replace metadata/groups
        @param format(string): json (default) or xml
        --- request headers ---
        @param quota (integer): Size limit in KB
        @param versioning (string): 'auto' or other string supported by server
        @metadata (dict): Optional user defined metadata in the form
        {   'name1': 'value1',
        'name2': 'value2', ...
        }
        @param content_type (string): set a custom content type
        @param content_length (string): set a custrom content length
        @param transfer_encoding (string): set a custrom transfer encoding
        """
        self.assert_container()
        param_dict = {} if format is None else dict(format=format)
        if update:
            param_dict['update'] = None
        path = path4url(self.account, self.container)+params4url(param_dict)

        if metadata is not None:
            for metaname, metaval in metadata.items():
                self.set_header('X-Container-Meta-'+metaname, metaval)
        self.set_header('X-Container-Policy-Quota', quota)
        self.set_header('X-Container-Policy-Versioning', versioning)
        self.set_header('Content-Type', content_type)
        self.set_header('Content-Length', content_length)
        self.set_header('Transfer-Encoding', transfer_encoding)
        success = kwargs.pop('success', 202)
        return self.post(path, *args, success=success, **kwargs)

    def container_delete(self, until=None, delimiter=None, *args, **kwargs):
        """ Full Pithos+ DELETE at container level
        --- request parameters ---
        @param until (timestamp string): if defined, container is purged up to that time
        """
        self.assert_container()
        param_dict = {} 
        if until is not None:
            param_dict['until']=until
        if delimiter is not None:
            param_dict['delimiter'] = delimiter
        path=path4url(self.account, self.container)+params4url(param_dict)
        success = kwargs.pop('success', 204)
        return self.delete(path, success=success)

    def object_head(self, object, version=None, if_etag_match=None, if_etag_not_match = None,
        if_modified_since = None, if_unmodified_since = None, *args, **kwargs):
        """ Full Pithos+ HEAD at object level
        --- request parameters ---
        @param version (string): optional version identified
        --- request headers ---
        @param if_etag_match (string): if provided, return only results
                with etag matching with this
        @param if_etag_not_match (string): if provided, return only results
                with etag not matching with this
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_container()
        path=path4url(self.account, self.container, object)
        path += '' if version is None else params4url(dict(version=version))
        self.set_header('If-Match', if_etag_match)
        self.set_header('If-None-Match', if_etag_not_match)
        self.set_header('If-Modified-Since', if_modified_since)
        self.set_header('If-Unmodified-Since', if_unmodified_since)
        success = kwargs.pop('success', 200)
        return self.head(path, *args, success=success, **kwargs)

    def object_get(self, object, format='json', hashmap=False, version=None,
        data_range=None, if_range=False, if_etag_match=None, if_etag_not_match = None,
        if_modified_since = None, if_unmodified_since = None, *args, **kwargs):
        """ Full Pithos+ GET at object level
        --- request parameters ---
        @param format (string): json (default) or xml
        @param hashmap (bool): Optional request for hashmap
        @param version (string): optional version identified
        --- request headers ---
        @param data_range (string): Optional range of data to retrieve
        @param if_range (bool): 
        @param if_etag_match (string): if provided, return only results
                with etag matching with this
        @param if_etag_not_match (string): if provided, return only results
                with etag not matching with this
        @param if_modified_since (string): Retrieve if account has changed since provided timestamp
        @param if_unmodified_since (string): Retrieve if account has not changed since provided timestamp
        """
        self.assert_container()
        param_dict = {} if format is None else dict(format=format)
        if hashmap:
            param_dict['hashmap']=None
        if version is not None:
            param_dict['version']=version
        path=path4url(self.account, self.container, object)+params4url(param_dict)
        self.set_header('Range', data_range)
        self.set_header('If-Range', '', if_range is True and data_range is not None)
        self.set_header('If-Match', if_etag_match, )
        self.set_header('If-None-Match', if_etag_not_match)
        self.set_header('If-Modified-Since', if_modified_since)
        self.set_header('If-Unmodified-Since', if_unmodified_since)
        success = kwargs.pop('success', 200)
        return self.get(path, *args, success=success, **kwargs)

    def object_put(self, object, format='json', hashmap=False, delimiter = None, if_etag_match=None,
        if_etag_not_match = None, etag=None, content_length = None, content_type=None,
        transfer_encoding=None, copy_from=None, move_from=None, source_account=None,
        source_version=None, content_encoding = None, content_disposition=None, manifest = None,
        permitions =None, public = None, metadata=None, *args, **kwargs):
        """ Full Pithos+ PUT at object level
        --- request parameters ---
        @param format (string): json (default) or xml
        @param hashmap (bool): Optional hashmap provided instead of data
        --- request headers ---
        @param if_etag_match (string): if provided, return only results
                with etag matching with this
        @param if_etag_not_match (string): if provided, return only results
                with etag not matching with this
        @param etag (string): The MD5 hash of the object (optional to check written data)
        @param content_length (integer): The size of the data written
        @param content_type (string): The MIME content type of the object
        @param transfer_encoding (string): Set to chunked to specify incremental uploading (if used, Content-Length is ignored)
        @param copy_from (string): The source path in the form /<container>/<object>
        @param move_from (string): The source path in the form /<container>/<object>
        @param source_account (string): The source account to copy/move from
        @param source_version (string): The source version to copy from
        @param conent_encoding (string): The encoding of the object
        @param content_disposition (string): The presentation style of the object
        @param manifest (string): Object parts prefix in /<container>/<object> form
        @param permitions (dict): Object permissions in the form (all fields are optional)
                {'read':[user1, group1, user2, ...], 'write':['user3, group2, group3, ...]}
        @param public (bool): If true, Object is publicly accessible, if false, not
        @param metadata (dict): Optional user defined metadata in the form
                {'meta-key-1':'meta-value-1', 'meta-key-2':'meta-value-2', ...}
        """
        self.assert_container()
        param_dict = {} if format is None else dict(format=format)
        if hashmap:
            param_dict['hashmap'] = None
        if type(delimiter) is str:
            param_dict['delimiter'] = delimiter
        path=path4url(self.account, self.container, object)+params4url(param_dict)
        self.set_header('If-Match', if_etag_match)
        self.set_header('If-None-Match', if_etag_not_match)
        self.set_header('ETag', etag)
        self.set_header('Content-Length', content_length)
        self.set_header('Content-Type', content_type)
        self.set_header('Transfer-Encoding', transfer_encoding)
        self.set_header('X-Copy-From', copy_from)
        self.set_header('X-Move-From', move_from)
        self.set_header('X-Source-Account', source_account)
        self.set_header('X-Source-Version', source_version)
        self.set_header('Content-Encoding', content_encoding)
        self.set_header('Content-Disposition', content_disposition)
        self.set_header('X-Object-Manifest', manifest)
        perms = None
        if permitions is not None:
            for permition_type, permition_list in permitions.items():
                if perms is None:
                    perms = '' #Remove permitions
                if len(permition_list) == 0:
                    continue
                perms += ';'+permition_type if len(perms) > 0 else permition_type
                perms += '='+list2str(permition_list, seperator=',')
        self.set_header('X-Object-Sharing', perms)
        self.set_header('X-Object-Public', public)
        if metadata is not None:
            for key, val in metadata.items():
                self.set_header('X-Object-Meta-'+key, val)

        success = kwargs.pop('success', 201)
        return self.put(path, *args, success=success, **kwargs)

    def object_copy(self, object, destination, format='json', ignore_content_type=False,
        if_etag_match=None, if_etag_not_match=None, destination_account=None,
        content_type=None, content_encoding=None, content_disposition=None, source_version=None,
        permitions=None, public=False, metadata=None, *args, **kwargs):
        """ Full Pithos+ COPY at object level
        --- request parameters ---
        @param format (string): json (default) or xml
        @param ignore_content_type (bool): Ignore the supplied Content-Type
        --- request headers ---
         @param if_etag_match (string): if provided, copy only results
                with etag matching with this
        @param if_etag_not_match (string): if provided, copy only results
                with etag not matching with this
        @param destination (string): The destination path in the form /<container>/<object>
        @param destination_account (string): The destination account to copy to
        @param content_type (string): The MIME content type of the object
        @param content_encoding (string): The encoding of the object
        @param content_disposition (string): The presentation style of the object
        @param source_version (string): The source version to copy from
        @param permitions (dict): Object permissions in the form (all fields are optional)
                {'read':[user1, group1, user2, ...], 'write':['user3, group2, group3, ...]}
                permitions override source permitions, removing any old permitions
        @param public (bool): If true, Object is publicly accessible, if else, not
        @param metadata (dict): Optional user defined metadata in the form
                {'meta-key-1':'meta-value-1', 'meta-key-2':'meta-value-2', ...}
                Metadata are appended to the source metadata. In case of same keys, they
                replace the old metadata
        """
        self.assert_container()
        param_dict = {} if format is None else dict(format=format)
        if ignore_content_type:
            param_dict['ignore_content_type'] = None
        path = path4url(self.account, self.container, object)+params4url(param_dict)
        self.set_header('If-Match', if_etag_match)
        self.set_header('If-None-Match', if_etag_not_match)
        self.set_header('Destination', destination)
        self.set_header('Destination-Account', destination_account)
        self.set_header('Content-Type', content_type)
        self.set_header('Content-Encoding', content_encoding)
        self.set_header('Content-Disposition', content_disposition)
        self.set_header('X-Source-Version', source_version)
        perms = None
        if permitions is not None:
            for permition_type, permition_list in permitions.items():
                if perms is None:
                    perms = '' #Remove permitions
                if len(permition_list) == 0:
                    continue
                perms += ';'+permition_type if len(perms) > 0 else permition_type
                perms += '='+list2str(permition_list, seperator=',')
        self.set_header('X-Object-Sharing', perms)
        self.set_header('X-Object-Public', public)
        if metadata is not None:
            for key, val in metadata.items():
                self.set_header('X-Object-Meta-'+key, val)
        success = kwargs.pop('success', 201)
        return self.copy(path, *args, success=success, **kwargs)

    def object_move(self, object, format='json', ignore_content_type=False,
        if_etag_match=None, if_etag_not_match=None, destination=None, destination_account=None,
        content_type=None, content_encoding=None, content_disposition=None, permitions={},
        public=False, metadata={}, *args, **kwargs):
        """ Full Pithos+ COPY at object level
        --- request parameters ---
        @param format (string): json (default) or xml
        @param ignore_content_type (bool): Ignore the supplied Content-Type
        --- request headers ---
         @param if_etag_match (string): if provided, return only results
                with etag matching with this
        @param if_etag_not_match (string): if provided, return only results
                with etag not matching with this
        @param destination (string): The destination path in the form /<container>/<object>
        @param destination_account (string): The destination account to copy to
        @param content_type (string): The MIME content type of the object
        @param content_encoding (string): The encoding of the object
        @param content_disposition (string): The presentation style of the object
        @param source_version (string): The source version to copy from
        @param permitions (dict): Object permissions in the form (all fields are optional)
                {'read':[user1, group1, user2, ...], 'write':['user3, group2, group3, ...]}
        @param public (bool): If true, Object is publicly accessible, if false, not
        @param metadata (dict): Optional user defined metadata in the form
                {'meta-key-1':'meta-value-1', 'meta-key-2':'meta-value-2', ...}
        """
        self.assert_container()
        param_dict = {} if format is None else dict(format=format)
        if ignore_content_type:
            param_dict['ignore_content_type']=None
        path = path4url(self.account, self.container, object)+params4url(param_dict)
        self.set_header('If-Match', if_etag_match)
        self.set_header('If-None-Match', if_etag_not_match)
        self.set_header('Destination', destination)
        self.set_header('Destination-Account', destination_account)
        self.set_header('Content-Type', content_type)
        self.set_header('Content-Encoding', content_encoding)
        self.set_header('Content-Disposition', content_disposition)
        perms = None
        for permition_type, permition_list in permitions.items():
            if perms is None:
                perms = '' #Remove permitions
            if len(permition_list) == 0:
                continue
            perms += ';'+permition_type if len(perms) > 0 else permition_type
            perms += '='+list2str(permition_list, seperator=',')
        self.set_header('X-Object-Sharing', perms)
        self.set_header('X-Object-Public', public)
        for key, val in metadata.items():
            self.set_header('X-Object-Meta-'+key, val)
        success = kwargs.pop('success', 201)
        return self.move(path, *args, success=success, **kwargs)

    def object_post(self, object, format='json', update=True,
        if_etag_match=None, if_etag_not_match=None, content_length=None, content_type=None,
        content_range=None, transfer_encoding=None, content_encoding=None, content_disposition=None,
        source_object=None, source_account=None, source_version=None, object_bytes=None,
        manifest=None, permitions={}, public=False, metadata={}, *args, **kwargs):
        """ Full Pithos+ POST at object level
        --- request parameters ---
        @param format (string): json (default) or xml
        @param update (bool): Do not replace metadata
        --- request headers ---
        @param if_etag_match (string): if provided, return only results
                with etag matching with this
        @param if_etag_not_match (string): if provided, return only results
                with etag not matching with this
        @param content_length (string): The size of the data written
        @param content_type (string): The MIME content type of the object
        @param content_range (string): The range of data supplied
        @param transfer_encoding (string): Set to chunked to specify incremental uploading
                (if used, Content-Length is ignored)
        @param content_encoding (string): The encoding of the object
        @param content_disposition (string): The presentation style of the object
        @param source_object (string): Update with data from the object at path /<container>/<object>
        @param source_account (string): The source account to update from
        @param source_version (string): The source version to copy from
        @param object_bytes (integer): The updated objects final size
        @param manifest (string): Object parts prefix in /<container>/<object> form
        @param permitions (dict): Object permissions in the form (all fields are optional)
                {'read':[user1, group1, user2, ...], 'write':['user3, group2, group3, ...]}
        @param public (bool): If true, Object is publicly accessible, if false, not
        @param metadata (dict): Optional user defined metadata in the form
                {'meta-key-1':'meta-value-1', 'meta-key-2':'meta-value-2', ...}
        """
        self.assert_container()
        param_dict = {} if format is None else dict(format=format)
        if update:
            param_dict['update'] = None
        path = path4url(self.account, self.container, object)+params4url(param_dict)
        self.set_header('If-Match', if_etag_match)
        self.set_header('If-None-Match', if_etag_not_match)
        self.set_header('Content-Length', content_length, iff=transfer_encoding is None)
        self.set_header('Content-Type', content_type)
        self.set_header('Content-Range', content_range)
        self.set_header('Transfer-Encoding', transfer_encoding)
        self.set_header('Content-Encoding', content_encoding)
        self.set_header('Content-Disposition', content_disposition)
        self.set_header('X-Source-Object', source_object)
        self.set_header('X-Source-Account', source_account)
        self.set_header('X-Source-Version', source_version)
        self.set_header('X-Object-Bytes', object_bytes)
        self.set_header('X-Object-Manifest', manifest)
        perms = None
        for permition_type, permition_list in permitions.items():
            if perms is None:
                perms = '' #Remove permitions
            if len(permition_list) == 0:
                continue
            perms += ';'+permition_type if len(perms) > 0 else permition_type
            perms += '='+list2str(permition_list, seperator=',')
        self.set_header('X-Object-Sharing', perms)
        self.set_header('X-Object-Public', public)
        for key, val in metadata.items():
            self.set_header('X-Object-Meta-'+key, val)
        success=kwargs.pop('success', (202, 204))
        return self.post(path, *args, success=success, **kwargs)
       
    def object_delete(self, object, until=None, delimiter=None, *args, **kwargs):
        """ Full Pithos+ DELETE at object level
        --- request parameters --- 
        @param until (string): Optional timestamp
        """
        self.assert_container()
        param_dict = {} 
        if until is not None:
            param_dict['until']=until
        if delimiter is not None:
            param_dict['delimiter'] = delimiter
        path = path4url(self.account, self.container, object)+params4url(param_dict)
        success = kwargs.pop('success', 204)
        return self.delete(path, *args, success=success, **kwargs)

    def purge_container(self):
        self.container_delete(until=unicode(time()))

    def upload_object_unchunked(self, obj, f, withHashFile = False, size=None, etag=None,
        content_encoding=None, content_disposition=None, content_type=None, sharing=None,
        public=None):
        # This is a naive implementation, it loads the whole file in memory
        #Look in pithos for a nice implementation
        self.assert_container()

        if withHashFile:
            data = f.read()
            try:
                import json
                data = json.dumps(json.loads(data))
            except ValueError:
                raise ClientError(message='"%s" is not json-formated'%f.name, status=1)
            except SyntaxError:
                raise ClientError(message='"%s" is not a valid hashmap file'%f.name, status=1)
            from StringIO import StringIO
            f = StringIO(data)
        data = f.read(size) if size is not None else f.read()
        self.object_put(obj, data=data, etag=etag, content_encoding=content_encoding,
            content_disposition=content_disposition, content_type=content_type, permitions=sharing,
            public=public, success=201)

    def put_block_async(self, data, hash):
        class SilentGreenlet(gevent.Greenlet):
            def _report_error(self, exc_info):
                _stderr = sys._stderr
                try:
                    sys.stderr = StringIO()
                    gevent.Greenlet._report_error(self, exc_info)
                finally:
                    sys.stderr = _stderr
        POOL_SIZE = 5
        if self.async_pool is None:
            self.async_pool = gevent.pool.Pool(size=POOL_SIZE)
        g = SilentGreenlet(self.put_block, data, hash)
        self.async_pool.start(g)
        return g

    def put_block(self, data, hash):
        r = self.container_post(update=True, content_type='application/octet-stream',
            content_length=len(data), data=data, format='json')
        assert r.json[0] == hash, 'Local hash does not match server'

    def create_object_by_manifestation(self, obj, etag=None, content_encoding=None,
        content_disposition=None, content_type=None, sharing=None, public=None):
        self.assert_container()
        obj_content_type = 'application/octet-stream' if content_type is None else content_type
        self.object_put(obj, content_length=0, etag=etag, content_encoding=content_encoding,
            content_disposition=content_disposition, content_type=content_type, permitions=sharing,
            public=public, manifest='%s/%s'%(self.container,obj))

    def upload_object(self, object, f, size=None, hash_cb=None, upload_cb=None, etag=None,
        content_encoding=None, content_disposition=None, content_type=None, sharing=None,
        public=None):
        """upload_object chunk by chunk. Different chunks are uploaded asynchronously
        in a pseudo-parallel fashion (using greenlets)
        """
        self.assert_container()

        meta = self.get_container_info(self.container)
        blocksize = int(meta['x-container-block-size'])
        blockhash = meta['x-container-block-hash']

        size = size if size is not None else os.fstat(f.fileno()).st_size
        nblocks = 1 + (size - 1) // blocksize
        hashes = []
        map = {}

        offset = 0

        if hash_cb:
            hash_gen = hash_cb(nblocks)
            hash_gen.next()

        for i in range(nblocks):
            block = f.read(min(blocksize, size - offset))
            bytes = len(block)
            hash = pithos_hash(block, blockhash)
            hashes.append(hash)
            map[hash] = (offset, bytes)
            offset += bytes
            if hash_cb:
                hash_gen.next()

        assert offset == size

        obj_content_type = 'application/octet-stream' if content_type is None else content_type

        hashmap = dict(bytes=size, hashes=hashes)
        r = self.object_put(object, format='json', hashmap=True, content_type=obj_content_type,
            json=hashmap, etag=etag, content_encoding=content_encoding,
            content_disposition=content_disposition, permitions=sharing, public=public,
            success=(201, 409))

        if r.status_code == 201:
            return

        missing = r.json

        if upload_cb:
            upload_gen = upload_cb(len(missing))
            upload_gen.next()

        flying = []
        for hash in missing:
            offset, bytes = map[hash]
            f.seek(offset)
            data = f.read(bytes)
            r = self.put_block_async(data, hash)
            flying.append(r)
            for r in flying:
                if r.ready():
                    if r.exception:
                        raise r.exception
                    if upload_cb:
                        upload_gen.next()
            flying = [r for r in flying if not r.ready()]

        gevent.joinall(flying)
        self.object_put(object, format='json', hashmap=True, content_type=obj_content_type, 
            json=hashmap, success=201)

    def download_object(self, obj, f, download_cb=None, version=None, overide=False, range=None,
        if_match=None, if_none_match=None, if_modified_since=None, if_unmodified_since=None):
        """overide is forcing the local file to become exactly as the remote, even if it is
        substantialy different
        """

        self.assert_container()

        #retrieve object hashmap
        hashmap = self.get_object_hashmap(obj, version=version, if_match=if_match,
            if_none_match=if_none_match, if_modified_since=if_modified_since,
            if_unmodified_since=if_unmodified_since)
        blocksize = int(hashmap['block_size'])
        blockhash = hashmap['block_hash']
        total_size = hashmap['bytes']
        map = hashmap['hashes']
        map_dict = {}
        for h in map:
            map_dict[h] = True
        download_bars = len(map)

        if range is not None:
            try:
                (custom_start, custom_end) = range.split('-')
                (custom_start, custom_end) = (int(custom_start), int(custom_end))
            except ValueError:
                raise ClientError(message='Invalid range string', status=601)
            if custom_start > custom_end or custom_start < 0:
                raise ClientError(message='Negative range', status=601)
            elif custom_start == custom_end:
                return
            elif custom_end > total_size:
                raise ClientError(message='Range exceeds file size', status=601)
        if total_size <= 0:
            return

        #load progress bar
        if download_cb is not None:
            download_gen = download_cb(total_size/blocksize + 1)
            download_gen.next()

        #load local file existing hashmap
        if not f.isatty():
            hash_dict = {}
            from os import path
            if path.exists(f.name):
                from binascii import hexlify
                from .pithos_sh_lib.hashmap import HashMap
                h = HashMap(blocksize, blockhash)
                with_progress_bar = False if download_cb is None else True
                h.load(f, with_progress_bar)
                for i, x in enumerate(h):
                    existing_hash = hexlify(x)
                    if existing_hash in map_dict:
                        hash_dict[existing_hash] = i
                        if download_cb:
                            download_gen.next()
                    elif not overide:
                        raise ClientError(message='Local file is substantialy different',
                            status=600)

        #download and print
        for i, h in enumerate(map):
            if not f.isatty() and h in hash_dict:
                continue
            if download_cb is not None:
                download_gen.next()
            start = i*blocksize
            if range is not None:
                if start < custom_start:
                    start = custom_start
                elif start > custom_end:
                    continue
            end = start + blocksize -1 if start+blocksize < total_size else total_size -1
            if range is not None and end > custom_end:
                end = custom_end
            data_range = 'bytes=%s-%s'%(start, end)
            data = self.object_get(obj, data_range=data_range, success=(200, 206), version=version,
                if_etag_match=if_match, if_etag_not_match=if_none_match,
                if_modified_since=if_modified_since, if_unmodified_since=if_unmodified_since)
            if not f.isatty():
                f.seek(start)
            f.write(data.content)
            #f.write(data.text.encode('utf-8'))

        if overide and not f.isatty():
            f.truncate(total_size)


    def get_object_hashmap(self, obj, version=None, if_match=None, if_none_match=None,
        if_modified_since=None, if_unmodified_since=None):
        try:
            r = self.object_get(obj, hashmap=True, version=version, if_etag_match=if_match,
                if_etag_not_match=if_none_match, if_modified_since=if_modified_since,
                if_unmodified_since=if_unmodified_since)
        except ClientError as err:
            if err.status == 304 or err.status == 412:
                return {}
            raise
        from json import loads
        return loads(r.text)

    def set_account_group(self, group, usernames):
        self.account_post(update=True, groups = {group:usernames})

    def del_account_group(self, group):
        return self.account_post(update=True, groups={group:[]})

    def get_account_info(self):
        r = self.account_head()
        from datetime import datetime
        r = self.account_head(if_modified_since=datetime.now())
        if r.status_code == 401:
            raise ClientError("No authorization")
        return r.headers

    def get_account_quota(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-Quota', exactMatch = True)

    def get_account_versioning(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-Versioning', exactMatch = True)

    def get_account_meta(self):
        return filter_in(self.get_account_info(), 'X-Account-Meta-')

    def get_account_group(self):
        return filter_in(self.get_account_info(), 'X-Account-Group-')

    def set_account_meta(self, metapairs):
        assert(type(metapairs) is dict)
        self.account_post(update=True, metadata=metapairs)

    def del_account_meta(self, metakey):
        self.account_post(update=True, metadata={metakey:''})

    def set_account_quota(self, quota):
        self.account_post(update=True, quota=quota)

    def set_account_versioning(self, versioning):
        self.account_post(update=True, versioning = versioning)

    def list_containers(self):
        r = self.account_get()
        return r.json

    def del_container(self, until=None, delimiter=None):
        self.assert_container()
        r = self.container_delete(until=until, delimiter=delimiter, success=(204, 404, 409))
        if r.status_code == 404:
            raise ClientError('Container "%s" does not exist'%self.container, r.status_code)
        elif r.status_code == 409:
            raise ClientError('Container "%s" is not empty'%self.container, r.status_code)

    def get_container_versioning(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Policy-Versioning')

    def get_container_quota(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Policy-Quota')

    def get_container_meta(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Meta-')

    def get_container_object_meta(self, container):
        return filter_in(self.get_container_info(container), 'X-Container-Object-Meta')

    def set_container_meta(self, metapairs):
        assert(type(metapairs) is dict)
        self.container_post(update=True, metadata=metapairs)

    def del_container_meta(self, metakey):
        self.container_post(update=True, metadata={metakey:''})

    def set_container_quota(self, quota):
        self.container_post(update=True, quota=quota)

    def set_container_versioning(self, versioning):
        self.container_post(update=True, versioning=versioning)

    def del_object(self, obj, until=None, delimiter=None):
        self.assert_container()
        self.object_delete(obj, until=until, delimiter=delimiter)

    def set_object_meta(self, object, metapairs):
        assert(type(metapairs) is dict)
        self.object_post(object, update=True, metadata=metapairs)

    def del_object_meta(self, metakey, object):
        self.object_post(object, update=True, metadata={metakey:''})

    def publish_object(self, object):
        self.object_post(object, update=True, public=True)

    def unpublish_object(self, object):
        self.object_post(object, update=True, public=False)

    def get_object_sharing(self, object):
        r = filter_in(self.get_object_info(object), 'X-Object-Sharing', exactMatch = True)
        reply = {}
        if len(r) > 0:
            perms = r['x-object-sharing'].split(';')
            for perm in perms:
                try:
                    perm.index('=')
                except ValueError:
                    raise ClientError('Incorrect reply format')
                (key, val) = perm.strip().split('=')
                reply[key] = val
        return reply

    def set_object_sharing(self, object, read_permition = False, write_permition = False):
        """Give read/write permisions to an object.
           @param object is the object to change sharing permitions onto
           @param read_permition is a list of users and user groups that get read permition for this object
                False means all previous read permitions will be removed
           @param write_perimition is a list of users and user groups to get write permition for this object
                False means all previous read permitions will be removed
        """
        perms = {}
        perms['read'] = read_permition if isinstance(read_permition, list) else ''
        perms['write'] = write_permition if isinstance(write_permition, list) else ''
        self.object_post(object, update=True, permitions=perms)

    def del_object_sharing(self, object):
        self.set_object_sharing(object)

    def append_object(self, object, source_file, upload_cb = None):
        """@param upload_db is a generator for showing progress of upload
            to caller application, e.g. a progress bar. Its next is called
            whenever a block is uploaded
        """
        self.assert_container()
        meta = self.get_container_info(self.container)
        blocksize = int(meta['x-container-block-size'])
        filesize = os.fstat(source_file.fileno()).st_size
        nblocks = 1 + (filesize - 1)//blocksize
        offset = 0
        if upload_cb is not None:
            upload_gen = upload_cb(nblocks)
        for i in range(nblocks):
            block = source_file.read(min(blocksize, filesize - offset))
            offset += len(block)
            self.object_post(object, update=True, content_range='bytes */*',
                content_type='application/octet-stream', content_length=len(block), data=block)
            if upload_cb is not None:
                upload_gen.next()

    def truncate_object(self, object, upto_bytes):
        self.object_post(object, update=True, content_range='bytes 0-%s/*'%upto_bytes,
            content_type='application/octet-stream', object_bytes=upto_bytes,
            source_object=path4url(self.container, object))

    def overwrite_object(self, object, start, end, source_file, upload_cb=None):
        """Overwrite a part of an object with given source file
           @start the part of the remote object to start overwriting from, in bytes
           @end the part of the remote object to stop overwriting to, in bytes
        """
        self.assert_container()
        meta = self.get_container_info(self.container)
        blocksize = int(meta['x-container-block-size'])
        filesize = os.fstat(source_file.fileno()).st_size
        datasize = int(end) - int(start) + 1
        nblocks = 1 + (datasize - 1)//blocksize
        offset = 0
        if upload_cb is not None:
            upload_gen = upload_cb(nblocks)
        for i in range(nblocks):
            block = source_file.read(min(blocksize, filesize - offset, datasize - offset))
            offset += len(block)
            self.object_post(object, update=True, content_type='application/octet-stream', 
                content_length=len(block), content_range='bytes %s-%s/*'%(start,end), data=block)
            if upload_cb is not None:
                upload_gen.next()

    def copy_object(self, src_container, src_object, dst_container, dst_object=False,
        source_version = None, public=False, content_type=None, delimiter=None):
        self.assert_account()
        self.container = dst_container
        dst_object = dst_object or src_object
        src_path = path4url(src_container, src_object)
        self.object_put(dst_object, success=201, copy_from=src_path, content_length=0,
            source_version=source_version, public=public, content_type=content_type,
            delimiter=delimiter)

    def move_object(self, src_container, src_object, dst_container, dst_object=False,
        source_version = None, public=False, content_type=None, delimiter=None):
        self.assert_account()
        self.container = dst_container
        dst_object = dst_object or src_object
        src_path = path4url(src_container, src_object)
        self.object_put(dst_object, success=201, move_from=src_path, content_length=0,
            source_version=source_version, public=public, content_type=content_type,
            delimiter=delimiter)
