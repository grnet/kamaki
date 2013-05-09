# Copyright 2011-2013 GRNET S.A. All rights reserved.
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

from threading import enumerate as activethreads

from os import fstat
from hashlib import new as newhashlib
from time import time

from binascii import hexlify

from kamaki.clients import SilentEvent, sendlog
from kamaki.clients.pithos.rest_api import PithosRestClient
from kamaki.clients.storage import ClientError
from kamaki.clients.utils import path4url, filter_in
from StringIO import StringIO


def _pithos_hash(block, blockhash):
    h = newhashlib(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()


def _range_up(start, end, a_range):
    if a_range:
        (rstart, rend) = a_range.split('-')
        (rstart, rend) = (int(rstart), int(rend))
        if rstart > end or rend < start:
            return (0, 0)
        if rstart > start:
            start = rstart
        if rend < end:
            end = rend
    return (start, end)


class PithosClient(PithosRestClient):
    """Synnefo Pithos+ API client"""

    def __init__(self, base_url, token, account=None, container=None):
        super(PithosClient, self).__init__(base_url, token, account, container)

    def purge_container(self, container=None):
        """Delete an empty container and destroy associated blocks
        """
        cnt_back_up = self.container
        try:
            self.container = container or cnt_back_up
            self.container_delete(until=unicode(time()))
        finally:
            self.container = cnt_back_up

    def upload_object_unchunked(
            self, obj, f,
            withHashFile=False,
            size=None,
            etag=None,
            content_encoding=None,
            content_disposition=None,
            content_type=None,
            sharing=None,
            public=None):
        """
        :param obj: (str) remote object path

        :param f: open file descriptor

        :param withHashFile: (bool)

        :param size: (int) size of data to upload

        :param etag: (str)

        :param content_encoding: (str)

        :param content_disposition: (str)

        :param content_type: (str)

        :param sharing: {'read':[user and/or grp names],
            'write':[usr and/or grp names]}

        :param public: (bool)
        """
        self._assert_container()

        if withHashFile:
            data = f.read()
            try:
                import json
                data = json.dumps(json.loads(data))
            except ValueError:
                raise ClientError('"%s" is not json-formated' % f.name, 1)
            except SyntaxError:
                msg = '"%s" is not a valid hashmap file' % f.name
                raise ClientError(msg, 1)
            f = StringIO(data)
        else:
            data = f.read(size) if size else f.read()
        self.object_put(
            obj,
            data=data,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            content_type=content_type,
            permissions=sharing,
            public=public,
            success=201)

    def create_object_by_manifestation(
            self, obj,
            etag=None,
            content_encoding=None,
            content_disposition=None,
            content_type=None,
            sharing=None,
            public=None):
        """
        :param obj: (str) remote object path

        :param etag: (str)

        :param content_encoding: (str)

        :param content_disposition: (str)

        :param content_type: (str)

        :param sharing: {'read':[user and/or grp names],
            'write':[usr and/or grp names]}

        :param public: (bool)
        """
        self._assert_container()
        self.object_put(
            obj,
            content_length=0,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            content_type=content_type,
            permissions=sharing,
            public=public,
            manifest='%s/%s' % (self.container, obj))

    # upload_* auxiliary methods
    def _put_block_async(self, data, hash, upload_gen=None):
        event = SilentEvent(method=self._put_block, data=data, hash=hash)
        event.start()
        return event

    def _put_block(self, data, hash):
        r = self.container_post(
            update=True,
            content_type='application/octet-stream',
            content_length=len(data),
            data=data,
            format='json')
        assert r.json[0] == hash, 'Local hash does not match server'

    def _get_file_block_info(self, fileobj, size=None):
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        blockhash = meta['x-container-block-hash']
        size = size if size is not None else fstat(fileobj.fileno()).st_size
        nblocks = 1 + (size - 1) // blocksize
        return (blocksize, blockhash, size, nblocks)

    def _create_or_get_missing_hashes(
            self, obj, json,
            size=None,
            format='json',
            hashmap=True,
            content_type=None,
            if_etag_match=None,
            if_etag_not_match=None,
            content_encoding=None,
            content_disposition=None,
            permissions=None,
            public=None,
            success=(201, 409)):
        r = self.object_put(
            obj,
            format='json',
            hashmap=True,
            content_type=content_type,
            json=json,
            if_etag_match=if_etag_match,
            if_etag_not_match=if_etag_not_match,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            permissions=permissions,
            public=public,
            success=success)
        return None if r.status_code == 201 else r.json

    def _calculate_blocks_for_upload(
            self, blocksize, blockhash, size, nblocks, hashes, hmap, fileobj,
            hash_cb=None):
        offset = 0
        if hash_cb:
            hash_gen = hash_cb(nblocks)
            hash_gen.next()

        for i in range(nblocks):
            block = fileobj.read(min(blocksize, size - offset))
            bytes = len(block)
            hash = _pithos_hash(block, blockhash)
            hashes.append(hash)
            hmap[hash] = (offset, bytes)
            offset += bytes
            if hash_cb:
                hash_gen.next()
        msg = 'Failed to calculate uploaded blocks:'
        ' Offset and object size do not match'
        assert offset == size, msg

    def _upload_missing_blocks(self, missing, hmap, fileobj, upload_gen=None):
        """upload missing blocks asynchronously"""

        self._init_thread_limit()

        flying = []
        failures = []
        for hash in missing:
            offset, bytes = hmap[hash]
            fileobj.seek(offset)
            data = fileobj.read(bytes)
            r = self._put_block_async(data, hash, upload_gen)
            flying.append(r)
            unfinished = self._watch_thread_limit(flying)
            for thread in set(flying).difference(unfinished):
                if thread.exception:
                    failures.append(thread)
                    if isinstance(
                            thread.exception,
                            ClientError) and thread.exception.status == 502:
                        self.POOLSIZE = self._thread_limit
                elif thread.isAlive():
                    flying.append(thread)
                elif upload_gen:
                    try:
                        upload_gen.next()
                    except:
                        pass
            flying = unfinished

        for thread in flying:
            thread.join()
            if thread.exception:
                failures.append(thread)
            elif upload_gen:
                try:
                    upload_gen.next()
                except:
                    pass

        return [failure.kwargs['hash'] for failure in failures]

    def upload_object(
            self, obj, f,
            size=None,
            hash_cb=None,
            upload_cb=None,
            etag=None,
            if_etag_match=None,
            if_not_exist=None,
            content_encoding=None,
            content_disposition=None,
            content_type=None,
            sharing=None,
            public=None):
        """Upload an object using multiple connections (threads)

        :param obj: (str) remote object path

        :param f: open file descriptor (rb)

        :param hash_cb: optional progress.bar object for calculating hashes

        :param upload_cb: optional progress.bar object for uploading

        :param etag: (str)

        :param if_etag_match: (str) Push that value to if-match header at file
            creation

        :param if_not_exist: (bool) If true, the file will be uploaded ONLY if
            it does not exist remotely, otherwise the operation will fail.
            Involves the case of an object with the same path is created while
            the object is being uploaded.

        :param content_encoding: (str)

        :param content_disposition: (str)

        :param content_type: (str)

        :param sharing: {'read':[user and/or grp names],
            'write':[usr and/or grp names]}

        :param public: (bool)
        """
        self._assert_container()

        #init
        block_info = (blocksize, blockhash, size, nblocks) =\
            self._get_file_block_info(f, size)
        (hashes, hmap, offset) = ([], {}, 0)
        if not content_type:
            content_type = 'application/octet-stream'

        self._calculate_blocks_for_upload(
            *block_info,
            hashes=hashes,
            hmap=hmap,
            fileobj=f,
            hash_cb=hash_cb)

        hashmap = dict(bytes=size, hashes=hashes)
        missing = self._create_or_get_missing_hashes(
            obj, hashmap,
            content_type=content_type,
            size=size,
            if_etag_match=if_etag_match,
            if_etag_not_match='*' if if_not_exist else None,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            permissions=sharing,
            public=public)

        if missing is None:
            return

        if upload_cb:
            upload_gen = upload_cb(len(missing))
            for i in range(len(missing), len(hashmap['hashes']) + 1):
                try:
                    upload_gen.next()
                except:
                    upload_gen = None
        else:
            upload_gen = None

        retries = 7
        try:
            while retries:
                sendlog.info('%s blocks missing' % len(missing))
                num_of_blocks = len(missing)
                missing = self._upload_missing_blocks(
                    missing,
                    hmap,
                    f,
                    upload_gen)
                if missing:
                    if num_of_blocks == len(missing):
                        retries -= 1
                    else:
                        num_of_blocks = len(missing)
                else:
                    break
            if missing:
                raise ClientError(
                    '%s blocks failed to upload' % len(missing),
                    status=800)
        except KeyboardInterrupt:
            sendlog.info('- - - wait for threads to finish')
            for thread in activethreads():
                thread.join()
            raise

        self.object_put(
            obj,
            format='json',
            hashmap=True,
            content_type=content_type,
            if_etag_match=if_etag_match,
            if_etag_not_match='*' if if_not_exist else None,
            etag=etag,
            json=hashmap,
            permissions=sharing,
            public=public,
            success=201)

    # download_* auxiliary methods
    def _get_remote_blocks_info(self, obj, **restargs):
        #retrieve object hashmap
        myrange = restargs.pop('data_range', None)
        hashmap = self.get_object_hashmap(obj, **restargs)
        restargs['data_range'] = myrange
        blocksize = int(hashmap['block_size'])
        blockhash = hashmap['block_hash']
        total_size = hashmap['bytes']
        #assert total_size/blocksize + 1 == len(hashmap['hashes'])
        map_dict = {}
        for i, h in enumerate(hashmap['hashes']):
            #  map_dict[h] = i   CHAGE
            if h in map_dict:
                map_dict[h].append(i)
            else:
                map_dict[h] = [i]
        return (blocksize, blockhash, total_size, hashmap['hashes'], map_dict)

    def _dump_blocks_sync(
            self, obj, remote_hashes, blocksize, total_size, dst, range,
            **args):
        for blockid, blockhash in enumerate(remote_hashes):
            if blockhash:
                start = blocksize * blockid
                is_last = start + blocksize > total_size
                end = (total_size - 1) if is_last else (start + blocksize - 1)
                (start, end) = _range_up(start, end, range)
                args['data_range'] = 'bytes=%s-%s' % (start, end)
                r = self.object_get(obj, success=(200, 206), **args)
                self._cb_next()
                dst.write(r.content)
                dst.flush()

    def _get_block_async(self, obj, **args):
        event = SilentEvent(self.object_get, obj, success=(200, 206), **args)
        event.start()
        return event

    def _hash_from_file(self, fp, start, size, blockhash):
        fp.seek(start)
        block = fp.read(size)
        h = newhashlib(blockhash)
        h.update(block.strip('\x00'))
        return hexlify(h.digest())

    def _thread2file(self, flying, blockids, local_file, offset=0, **restargs):
        """write the results of a greenleted rest call to a file

        :param offset: the offset of the file up to blocksize
        - e.g. if the range is 10-100, all blocks will be written to
        normal_position - 10
        """
        for i, (key, g) in enumerate(flying.items()):
            if g.isAlive():
                continue
            if g.exception:
                raise g.exception
            block = g.value.content
            for block_start in blockids[key]:
                local_file.seek(block_start + offset)
                local_file.write(block)
                self._cb_next()
            flying.pop(key)
            blockids.pop(key)
        local_file.flush()

    def _dump_blocks_async(
            self, obj, remote_hashes, blocksize, total_size, local_file,
            blockhash=None, resume=False, filerange=None, **restargs):
        file_size = fstat(local_file.fileno()).st_size if resume else 0
        flying = dict()
        blockid_dict = dict()
        offset = 0
        if filerange is not None:
            rstart = int(filerange.split('-')[0])
            offset = rstart if blocksize > rstart else rstart % blocksize

        self._init_thread_limit()
        for block_hash, blockids in remote_hashes.items():
            blockids = [blk * blocksize for blk in blockids]
            unsaved = [blk for blk in blockids if not (
                blk < file_size and block_hash == self._hash_from_file(
                        local_file, blk, blocksize, blockhash))]
            self._cb_next(len(blockids) - len(unsaved))
            if unsaved:
                key = unsaved[0]
                self._watch_thread_limit(flying.values())
                self._thread2file(
                    flying, blockid_dict, local_file, offset,
                    **restargs)
                end = total_size - 1 if key + blocksize > total_size\
                    else key + blocksize - 1
                start, end = _range_up(key, end, filerange)
                if start == end:
                    self._cb_next()
                    continue
                restargs['async_headers'] = {
                    'Range': 'bytes=%s-%s' % (start, end)}
                flying[key] = self._get_block_async(obj, **restargs)
                blockid_dict[key] = unsaved

        for thread in flying.values():
            thread.join()
        self._thread2file(flying, blockid_dict, local_file, offset, **restargs)

    def download_object(
            self, obj, dst,
            download_cb=None,
            version=None,
            resume=False,
            range_str=None,
            if_match=None,
            if_none_match=None,
            if_modified_since=None,
            if_unmodified_since=None):
        """Download an object (multiple connections, random blocks)

        :param obj: (str) remote object path

        :param dst: open file descriptor (wb+)

        :param download_cb: optional progress.bar object for downloading

        :param version: (str) file version

        :param resume: (bool) if set, preserve already downloaded file parts

        :param range_str: (str) from, to are file positions (int) in bytes

        :param if_match: (str)

        :param if_none_match: (str)

        :param if_modified_since: (str) formated date

        :param if_unmodified_since: (str) formated date"""
        restargs = dict(
            version=version,
            data_range=None if range_str is None else 'bytes=%s' % range_str,
            if_match=if_match,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
            if_unmodified_since=if_unmodified_since)

        (
            blocksize,
            blockhash,
            total_size,
            hash_list,
            remote_hashes) = self._get_remote_blocks_info(obj, **restargs)
        assert total_size >= 0

        if download_cb:
            self.progress_bar_gen = download_cb(len(hash_list))
            self._cb_next()

        if dst.isatty():
            self._dump_blocks_sync(
                obj,
                hash_list,
                blocksize,
                total_size,
                dst,
                range_str,
                **restargs)
        else:
            self._dump_blocks_async(
                obj,
                remote_hashes,
                blocksize,
                total_size,
                dst,
                blockhash,
                resume,
                range_str,
                **restargs)
            if not range_str:
                dst.truncate(total_size)

        self._complete_cb()

    #Command Progress Bar method
    def _cb_next(self, step=1):
        if hasattr(self, 'progress_bar_gen'):
            try:
                for i in xrange(step):
                    self.progress_bar_gen.next()
            except:
                pass

    def _complete_cb(self):
        while True:
            try:
                self.progress_bar_gen.next()
            except:
                break

    def get_object_hashmap(
            self, obj,
            version=None,
            if_match=None,
            if_none_match=None,
            if_modified_since=None,
            if_unmodified_since=None,
            data_range=None):
        """
        :param obj: (str) remote object path

        :param if_match: (str)

        :param if_none_match: (str)

        :param if_modified_since: (str) formated date

        :param if_unmodified_since: (str) formated date

        :param data_range: (str) from-to where from and to are integers
            denoting file positions in bytes

        :returns: (list)
        """
        try:
            r = self.object_get(
                obj,
                hashmap=True,
                version=version,
                if_etag_match=if_match,
                if_etag_not_match=if_none_match,
                if_modified_since=if_modified_since,
                if_unmodified_since=if_unmodified_since,
                data_range=data_range)
        except ClientError as err:
            if err.status == 304 or err.status == 412:
                return {}
            raise
        return r.json

    def set_account_group(self, group, usernames):
        """
        :param group: (str)

        :param usernames: (list)
        """
        self.account_post(update=True, groups={group: usernames})

    def del_account_group(self, group):
        """
        :param group: (str)
        """
        self.account_post(update=True, groups={group: []})

    def get_account_info(self, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)
        """
        r = self.account_head(until=until)
        if r.status_code == 401:
            raise ClientError("No authorization", status=401)
        return r.headers

    def get_account_quota(self):
        """
        :returns: (dict)
        """
        return filter_in(
            self.get_account_info(),
            'X-Account-Policy-Quota',
            exactMatch=True)

    def get_account_versioning(self):
        """
        :returns: (dict)
        """
        return filter_in(
            self.get_account_info(),
            'X-Account-Policy-Versioning',
            exactMatch=True)

    def get_account_meta(self, until=None):
        """
        :meta until: (str) formated date

        :returns: (dict)
        """
        return filter_in(self.get_account_info(until=until), 'X-Account-Meta-')

    def get_account_group(self):
        """
        :returns: (dict)
        """
        return filter_in(self.get_account_info(), 'X-Account-Group-')

    def set_account_meta(self, metapairs):
        """
        :param metapairs: (dict) {key1:val1, key2:val2, ...}
        """
        assert(type(metapairs) is dict)
        self.account_post(update=True, metadata=metapairs)

    def del_account_meta(self, metakey):
        """
        :param metakey: (str) metadatum key
        """
        self.account_post(update=True, metadata={metakey: ''})

    """
    def set_account_quota(self, quota):
        ""
        :param quota: (int)
        ""
        self.account_post(update=True, quota=quota)
    """

    def set_account_versioning(self, versioning):
        """
        "param versioning: (str)
        """
        self.account_post(update=True, versioning=versioning)

    def list_containers(self):
        """
        :returns: (dict)
        """
        r = self.account_get()
        return r.json

    def del_container(self, until=None, delimiter=None):
        """
        :param until: (str) formated date

        :param delimiter: (str) with / empty container

        :raises ClientError: 404 Container does not exist

        :raises ClientError: 409 Container is not empty
        """
        self._assert_container()
        r = self.container_delete(
            until=until,
            delimiter=delimiter,
            success=(204, 404, 409))
        if r.status_code == 404:
            raise ClientError(
                'Container "%s" does not exist' % self.container,
                r.status_code)
        elif r.status_code == 409:
            raise ClientError(
                'Container "%s" is not empty' % self.container,
                r.status_code)

    def get_container_versioning(self, container=None):
        """
        :param container: (str)

        :returns: (dict)
        """
        cnt_back_up = self.container
        try:
            self.container = container or cnt_back_up
            return filter_in(
                self.get_container_info(),
                'X-Container-Policy-Versioning')
        finally:
            self.container = cnt_back_up

    def get_container_limit(self, container=None):
        """
        :param container: (str)

        :returns: (dict)
        """
        cnt_back_up = self.container
        try:
            self.container = container or cnt_back_up
            return filter_in(
                self.get_container_info(),
                'X-Container-Policy-Quota')
        finally:
            self.container = cnt_back_up

    def get_container_info(self, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)

        :raises ClientError: 404 Container not found
        """
        try:
            r = self.container_head(until=until)
        except ClientError as err:
            err.details.append('for container %s' % self.container)
            raise err
        return r.headers

    def get_container_meta(self, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)
        """
        return filter_in(
            self.get_container_info(until=until),
            'X-Container-Meta')

    def get_container_object_meta(self, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)
        """
        return filter_in(
            self.get_container_info(until=until),
            'X-Container-Object-Meta')

    def set_container_meta(self, metapairs):
        """
        :param metapairs: (dict) {key1:val1, key2:val2, ...}
        """
        assert(type(metapairs) is dict)
        self.container_post(update=True, metadata=metapairs)

    def del_container_meta(self, metakey):
        """
        :param metakey: (str) metadatum key
        """
        self.container_post(update=True, metadata={metakey: ''})

    def set_container_limit(self, limit):
        """
        :param limit: (int)
        """
        self.container_post(update=True, quota=limit)

    def set_container_versioning(self, versioning):
        """
        :param versioning: (str)
        """
        self.container_post(update=True, versioning=versioning)

    def del_object(self, obj, until=None, delimiter=None):
        """
        :param obj: (str) remote object path

        :param until: (str) formated date

        :param delimiter: (str)
        """
        self._assert_container()
        self.object_delete(obj, until=until, delimiter=delimiter)

    def set_object_meta(self, obj, metapairs):
        """
        :param obj: (str) remote object path

        :param metapairs: (dict) {key1:val1, key2:val2, ...}
        """
        assert(type(metapairs) is dict)
        self.object_post(obj, update=True, metadata=metapairs)

    def del_object_meta(self, obj, metakey):
        """
        :param obj: (str) remote object path

        :param metakey: (str) metadatum key
        """
        self.object_post(obj, update=True, metadata={metakey: ''})

    def publish_object(self, obj):
        """
        :param obj: (str) remote object path

        :returns: (str) access url
        """
        self.object_post(obj, update=True, public=True)
        info = self.get_object_info(obj)
        pref, sep, rest = self.base_url.partition('//')
        base = rest.split('/')[0]
        return '%s%s%s/%s' % (pref, sep, base, info['x-object-public'])

    def unpublish_object(self, obj):
        """
        :param obj: (str) remote object path
        """
        self.object_post(obj, update=True, public=False)

    def get_object_info(self, obj, version=None):
        """
        :param obj: (str) remote object path

        :param version: (str)

        :returns: (dict)
        """
        try:
            r = self.object_head(obj, version=version)
            return r.headers
        except ClientError as ce:
            if ce.status == 404:
                raise ClientError('Object %s not found' % obj, status=404)
            raise

    def get_object_meta(self, obj, version=None):
        """
        :param obj: (str) remote object path

        :param version: (str)

        :returns: (dict)
        """
        return filter_in(
            self.get_object_info(obj, version=version),
            'X-Object-Meta')

    def get_object_sharing(self, obj):
        """
        :param obj: (str) remote object path

        :returns: (dict)
        """
        r = filter_in(
            self.get_object_info(obj),
            'X-Object-Sharing',
            exactMatch=True)
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

    def set_object_sharing(
            self, obj,
            read_permition=False, write_permition=False):
        """Give read/write permisions to an object.

        :param obj: (str) remote object path

        :param read_permition: (list - bool) users and user groups that get
            read permition for this object - False means all previous read
            permissions will be removed

        :param write_perimition: (list - bool) of users and user groups to get
           write permition for this object - False means all previous write
           permissions will be removed
        """

        perms = dict(read=read_permition or '', write=write_permition or '')
        self.object_post(obj, update=True, permissions=perms)

    def del_object_sharing(self, obj):
        """
        :param obj: (str) remote object path
        """
        self.set_object_sharing(obj)

    def append_object(self, obj, source_file, upload_cb=None):
        """
        :param obj: (str) remote object path

        :param source_file: open file descriptor

        :param upload_db: progress.bar for uploading
        """

        self._assert_container()
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
        nblocks = 1 + (filesize - 1) // blocksize
        offset = 0
        if upload_cb:
            upload_gen = upload_cb(nblocks)
            upload_gen.next()
        for i in range(nblocks):
            block = source_file.read(min(blocksize, filesize - offset))
            offset += len(block)
            self.object_post(
                obj,
                update=True,
                content_range='bytes */*',
                content_type='application/octet-stream',
                content_length=len(block),
                data=block)

            if upload_cb:
                upload_gen.next()

    def truncate_object(self, obj, upto_bytes):
        """
        :param obj: (str) remote object path

        :param upto_bytes: max number of bytes to leave on file
        """
        self.object_post(
            obj,
            update=True,
            content_range='bytes 0-%s/*' % upto_bytes,
            content_type='application/octet-stream',
            object_bytes=upto_bytes,
            source_object=path4url(self.container, obj))

    def overwrite_object(self, obj, start, end, source_file, upload_cb=None):
        """Overwrite a part of an object from local source file

        :param obj: (str) remote object path

        :param start: (int) position in bytes to start overwriting from

        :param end: (int) position in bytes to stop overwriting at

        :param source_file: open file descriptor

        :param upload_db: progress.bar for uploading
        """

        r = self.get_object_info(obj)
        rf_size = int(r['content-length'])
        if rf_size < int(start):
            raise ClientError(
                'Range start exceeds file size',
                status=416)
        elif rf_size < int(end):
            raise ClientError(
                'Range end exceeds file size',
                status=416)
        self._assert_container()
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
        datasize = int(end) - int(start) + 1
        nblocks = 1 + (datasize - 1) // blocksize
        offset = 0
        if upload_cb:
            upload_gen = upload_cb(nblocks)
            upload_gen.next()
        for i in range(nblocks):
            read_size = min(blocksize, filesize - offset, datasize - offset)
            block = source_file.read(read_size)
            self.object_post(
                obj,
                update=True,
                content_type='application/octet-stream',
                content_length=len(block),
                content_range='bytes %s-%s/*' % (
                    start + offset,
                    start + offset + len(block) - 1),
                data=block)
            offset += len(block)

            if upload_cb:
                upload_gen.next()

    def copy_object(
            self, src_container, src_object, dst_container,
            dst_object=None,
            source_version=None,
            source_account=None,
            public=False,
            content_type=None,
            delimiter=None):
        """
        :param src_container: (str) source container

        :param src_object: (str) source object path

        :param dst_container: (str) destination container

        :param dst_object: (str) destination object path

        :param source_version: (str) source object version

        :param source_account: (str) account to copy from

        :param public: (bool)

        :param content_type: (str)

        :param delimiter: (str)
        """
        self._assert_account()
        self.container = dst_container
        src_path = path4url(src_container, src_object)
        self.object_put(
            dst_object or src_object,
            success=201,
            copy_from=src_path,
            content_length=0,
            source_version=source_version,
            source_account=source_account,
            public=public,
            content_type=content_type,
            delimiter=delimiter)

    def move_object(
            self, src_container, src_object, dst_container,
            dst_object=False,
            source_account=None,
            source_version=None,
            public=False,
            content_type=None,
            delimiter=None):
        """
        :param src_container: (str) source container

        :param src_object: (str) source object path

        :param dst_container: (str) destination container

        :param dst_object: (str) destination object path

        :param source_account: (str) account to move from

        :param source_version: (str) source object version

        :param public: (bool)

        :param content_type: (str)

        :param delimiter: (str)
        """
        self._assert_account()
        self.container = dst_container
        dst_object = dst_object or src_object
        src_path = path4url(src_container, src_object)
        self.object_put(
            dst_object,
            success=201,
            move_from=src_path,
            content_length=0,
            source_account=source_account,
            source_version=source_version,
            public=public,
            content_type=content_type,
            delimiter=delimiter)

    def get_sharing_accounts(self, limit=None, marker=None, *args, **kwargs):
        """Get accounts that share with self.account

        :param limit: (str)

        :param marker: (str)

        :returns: (dict)
        """
        self._assert_account()

        self.set_param('format', 'json')
        self.set_param('limit', limit, iff=limit is not None)
        self.set_param('marker', marker, iff=marker is not None)

        path = ''
        success = kwargs.pop('success', (200, 204))
        r = self.get(path, *args, success=success, **kwargs)
        return r.json

    def get_object_versionlist(self, obj):
        """
        :param obj: (str) remote object path

        :returns: (list)
        """
        self._assert_container()
        r = self.object_get(obj, format='json', version='list')
        return r.json['versions']
