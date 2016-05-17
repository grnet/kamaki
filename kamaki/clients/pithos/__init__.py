# Copyright 2011-2015 GRNET S.A. All rights reserved.
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
from StringIO import StringIO
from logging import getLogger

from binascii import hexlify

from kamaki.clients import SilentEvent
from kamaki.clients.pithos.rest_api import PithosRestClient
from kamaki.clients.storage import ClientError
from kamaki.clients.utils import path4url, filter_in, readall

LOG = getLogger(__name__)


def _dump_buffer(buffer_, destination):
    """Append buffer to destination (file descriptor)"""
    destination.write(buffer_)
    destination.flush()


def _pithos_hash(block, blockhash):
    h = newhashlib(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()


def _range_up(start, end, max_value, a_range):
    """
    :param start: (int) the window bottom

    :param end: (int) the window top

    :param max_value: (int) maximum accepted value

    :param a_range: (str) a range string in the form X[,X'[,X''[...]]]
        where X: x|x-y|-x where x < y and x, y natural numbers

    :returns: (str) a range string cut-off for the start-end range
        an empty response means this window is out of range
    """
    assert start >= 0, '_range_up called w. start(%s) < 0' % start
    assert end >= start, '_range_up called w. end(%s) < start(%s)' % (
        end, start)
    assert end <= max_value, '_range_up called w. max_value(%s) < end(%s)' % (
        max_value, end)
    if not a_range:
        return '%s-%s' % (start, end)
    selected = []
    for some_range in a_range.split(','):
        v0, sep, v1 = some_range.partition('-')
        if v0:
            v0 = int(v0)
            if sep:
                v1 = int(v1)
                if v1 < start or v0 > end or v1 < v0:
                    continue
                v0 = v0 if v0 > start else start
                v1 = v1 if v1 < end else end
                selected.append('%s-%s' % (v0, v1))
            elif v0 < start:
                continue
            else:
                v1 = v0 if v0 <= end else end
                selected.append('%s-%s' % (start, v1))
        else:
            v1 = int(v1)
            if max_value - v1 > end:
                continue
            v0 = (max_value - v1) if max_value - v1 > start else start
            selected.append('%s-%s' % (v0, end))
    return ','.join(selected)


class PithosClient(PithosRestClient):
    """Synnefo Pithos+ API client"""

    def __init__(self, endpoint_url, token, account=None, container=None):
        super(PithosClient, self).__init__(
            endpoint_url, token, account, container)

    def use_alternative_account(self, func, *args, **kwargs):
        """Run method with an alternative account UUID, as long as kwargs
           contain a non-None "alternative_account" argument
        """
        alternative_account = kwargs.pop('alternative_account', None)
        bu_account = self.account
        try:
            if alternative_account and alternative_account != self.account:
                self.account = alternative_account
            return func(*args, **kwargs)
        finally:
            self.account = bu_account

    def create_container(
            self,
            container=None, sizelimit=None, versioning=None, metadata=None,
            project_id=None, **kwargs):
        """
        :param container: (str) if not given, self.container is used instead

        :param sizelimit: (int) container total size limit in bytes

        :param versioning: (str) can be auto or whatever supported by server

        :param metadata: (dict) Custom user-defined metadata of the form
            { 'name1': 'value1', 'name2': 'value2', ... }

        :returns: (dict) response headers
        """
        cnt_back_up = self.container
        try:
            self.container = container or cnt_back_up
            r = self.container_put(
                quota=sizelimit, versioning=versioning, metadata=metadata,
                project_id=project_id, **kwargs)
            return r.headers
        finally:
            self.container = cnt_back_up

    def purge_container(self, container=None):
        """Delete an empty container and destroy associated blocks"""
        cnt_back_up = self.container
        try:
            self.container = container or cnt_back_up
            r = self.container_delete(until=unicode(time()))
        finally:
            self.container = cnt_back_up
        return r.headers

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

        :returns: (dict) created object metadata
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
            data = readall(f, size) if size else f.read()
        r = self.object_put(
            obj,
            data=data,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            content_type=content_type,
            permissions=sharing,
            public=public,
            success=201)
        return r.headers

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

        :returns: (dict) created object metadata
        """
        self._assert_container()
        r = self.object_put(
            obj,
            content_length=0,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            content_type=content_type,
            permissions=sharing,
            public=public,
            manifest='%s/%s' % (self.container, obj))
        return r.headers

    # upload_* auxiliary methods
    def _put_block_async(self, data, hash):
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

    def _get_file_block_info(self, fileobj, size=None, cache=None):
        """
        :param fileobj: (file descriptor) source

        :param size: (int) size of data to upload from source

        :param cache: (dict) if provided, cache container info response to
        avoid redundant calls
        """
        if isinstance(cache, dict):
            try:
                meta = cache[self.container]
            except KeyError:
                meta = self.get_container_info()
                cache[self.container] = meta
        else:
            meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        blockhash = meta['x-container-block-hash']
        size = size if size is not None else fstat(fileobj.fileno()).st_size
        nblocks = 1 + (size - 1) // blocksize
        return (blocksize, blockhash, size, nblocks)

    def _create_object_or_get_missing_hashes(
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
        return (None if r.status_code == 201 else r.json), r.headers

    def _calculate_blocks_for_upload(
            self, blocksize, blockhash, size, nblocks, hashes, hmap, fileobj,
            hash_cb=None):
        offset = 0
        if hash_cb:
            hash_gen = hash_cb(nblocks)
            hash_gen.next()

        for i in xrange(nblocks):
            block = readall(fileobj, min(blocksize, size - offset))
            bytes = len(block)
            if bytes <= 0:
                break
            hash = _pithos_hash(block, blockhash)
            hashes.append(hash)
            hmap[hash] = (offset, bytes)
            offset += bytes
            if hash_cb:
                hash_gen.next()
        msg = ('Failed to calculate uploading blocks: '
               'read bytes(%s) != requested size (%s)' % (offset, size))
        assert offset == size, msg

    def _upload_missing_blocks(self, missing, hmap, fileobj, upload_gen=None):
        """upload missing blocks asynchronously"""

        self._init_thread_limit()

        flying = []
        failures = []
        for hash in missing:
            offset, bytes = hmap[hash]
            fileobj.seek(offset)
            data = readall(fileobj, bytes)
            r = self._put_block_async(data, hash)
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
            public=None,
            container_info_cache=None,
            target_account=None):
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

        :param container_info_cache: (dict) if given, avoid redundant calls to
            server for container info (block size and hash information)

        :param target_account: (str) the UUID of the account the object will be
            allocated at, if different to the client account (e.g., when
            user A uploads something to a location owned by user B)
        """
        self._assert_container()

        block_info = (
            blocksize, blockhash, size, nblocks
            ) = self.use_alternative_account(
                self._get_file_block_info, f, size, container_info_cache,
                alternative_account=target_account)
        hashes, hmap = [], {}
        content_type = content_type or 'application/octet-stream'

        self._calculate_blocks_for_upload(
            *block_info,
            hashes=hashes,
            hmap=hmap,
            fileobj=f,
            hash_cb=hash_cb)

        hashmap = dict(bytes=size, hashes=hashes)
        missing, obj_headers = self.use_alternative_account(
            self._create_object_or_get_missing_hashes, obj, hashmap,
            content_type=content_type,
            size=size,
            if_etag_match=if_etag_match,
            if_etag_not_match='*' if if_not_exist else None,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            permissions=sharing,
            public=public,
            alternative_account=target_account)

        if missing is None:
            return obj_headers

        if upload_cb:
            upload_gen = upload_cb(len(hashmap['hashes']))
            for i in range(len(hashmap['hashes']) + 1 - len(missing)):
                try:
                    upload_gen.next()
                except:
                    LOG.debug('Progress bar failure')
                    break
        else:
            upload_gen = None

        retries = 7
        while retries:
            LOG.debug('%s blocks missing' % len(missing))
            num_of_blocks = len(missing)
            missing = self._upload_missing_blocks(
                missing, hmap, f, upload_gen)
            if missing:
                if num_of_blocks == len(missing):
                    retries -= 1
                else:
                    num_of_blocks = len(missing)
            else:
                break
        if missing:
            try:
                details = ['%s' % thread.exception for thread in missing]
            except Exception:
                details = ['Also, failed to read thread exceptions']
            raise ClientError(
                '%s blocks failed to upload' % len(missing),
                details=details)

        r = self.use_alternative_account(
            self.object_put,
            obj,
            format='json',
            hashmap=True,
            content_type=content_type,
            content_encoding=content_encoding,
            if_etag_match=if_etag_match,
            if_etag_not_match='*' if if_not_exist else None,
            etag=etag,
            json=hashmap,
            permissions=sharing,
            public=public,
            success=201,
            alternative_account=target_account)
        return r.headers

    def upload_from_string(
            self, obj, input_str,
            hash_cb=None,
            upload_cb=None,
            etag=None,
            if_etag_match=None,
            if_not_exist=None,
            content_encoding=None,
            content_disposition=None,
            content_type=None,
            sharing=None,
            public=None,
            container_info_cache=None):
        """Upload an object using multiple connections (threads)

        :param obj: (str) remote object path

        :param input_str: (str) upload content

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

        :param container_info_cache: (dict) if given, avoid redundant calls to
            server for container info (block size and hash information)
        """
        self._assert_container()

        blocksize, blockhash, size, nblocks = self._get_file_block_info(
            fileobj=None, size=len(input_str), cache=container_info_cache)
        (hashes, hmap, offset) = ([], {}, 0)
        if not content_type:
            content_type = 'application/octet-stream'

        hashes = []
        hmap = {}
        for blockid in range(nblocks):
            start = blockid * blocksize
            block = input_str[start: (start + blocksize)]
            hashes.append(_pithos_hash(block, blockhash))
            hmap[hashes[blockid]] = (start, block)

        hashmap = dict(bytes=size, hashes=hashes)
        missing, obj_headers = self._create_object_or_get_missing_hashes(
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
            return obj_headers
        num_of_missing = len(missing)

        if upload_cb:
            self.progress_bar_gen = upload_cb(nblocks)
            for i in range(nblocks + 1 - num_of_missing):
                self._cb_next()

        tries = 7
        old_failures = 0
        try:
            while tries and missing:
                flying = []
                failures = []
                for hash in missing:
                    offset, block = hmap[hash]
                    bird = self._put_block_async(block, hash)
                    flying.append(bird)
                    unfinished = self._watch_thread_limit(flying)
                    for thread in set(flying).difference(unfinished):
                        if thread.exception:
                            failures.append(thread.kwargs['hash'])
                        if thread.isAlive():
                            flying.append(thread)
                        else:
                            self._cb_next()
                    flying = unfinished
                for thread in flying:
                    thread.join()
                    if thread.exception:
                        failures.append(thread.kwargs['hash'])
                    self._cb_next()
                missing = failures
                if missing and len(missing) == old_failures:
                    tries -= 1
                old_failures = len(missing)
            if missing:
                raise ClientError('%s blocks failed to upload' % len(missing))
        except KeyboardInterrupt:
            LOG.debug('- - - wait for threads to finish')
            for thread in activethreads():
                thread.join()
            raise
        self._cb_next()

        r = self.object_put(
            obj,
            format='json',
            hashmap=True,
            content_type=content_type,
            content_encoding=content_encoding,
            if_etag_match=if_etag_match,
            if_etag_not_match='*' if if_not_exist else None,
            etag=etag,
            json=hashmap,
            permissions=sharing,
            public=public,
            success=201)
        return r.headers

    # download_* auxiliary methods
    def _get_remote_blocks_info(self, obj, **restargs):
        # retrieve object hashmap
        myrange = restargs.pop('data_range', None)
        hashmap = restargs.pop('hashmap', None) or (
            self.get_object_hashmap(obj, **restargs))
        restargs['data_range'] = myrange
        blocksize = int(hashmap['block_size'])
        blockhash = hashmap['block_hash']
        total_size = hashmap['bytes']
        # assert total_size/blocksize + 1 == len(hashmap['hashes'])
        map_dict = {}
        for i, h in enumerate(hashmap['hashes']):
            #  map_dict[h] = i   CHAGE
            if h in map_dict:
                map_dict[h].append(i)
            else:
                map_dict[h] = [i]
        return (blocksize, blockhash, total_size, hashmap['hashes'], map_dict)

    def _dump_blocks_sync(
            self, obj, remote_hashes, blocksize, total_size, dst, crange,
            **args):
        if not total_size:
            return
        for blockid, blockhash in enumerate(remote_hashes):
            if blockhash:
                start = blocksize * blockid
                is_last = start + blocksize > total_size
                end = (total_size - 1) if is_last else (start + blocksize - 1)
                data_range = _range_up(start, end, total_size, crange)
                if not data_range:
                    self._cb_next()
                    continue
                args['data_range'] = 'bytes=%s' % data_range
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
        block = readall(fp, size)
        h = newhashlib(blockhash)
        h.update(block.strip('\x00'))
        return hexlify(h.digest())

    def _thread2file(self, flying, blockids, local_file, offset=0, **restargs):
        """write the results of a greenleted rest call to a file

        :param offset: the offset of the file up to blocksize
        - e.g. if the range is 10-100, all blocks will be written to
        normal_position - 10
        """
        for key, g in flying.items():
            if g.isAlive():
                continue
            if g.exception:
                raise g.exception
            block = g.value.content
            for block_start in blockids[key]:
                # This should not be used in all cases
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
                end = total_size - 1 if (
                    key + blocksize > total_size) else key + blocksize - 1
                if end < key:
                    self._cb_next()
                    continue
                data_range = _range_up(key, end, total_size, filerange)
                if not data_range:
                    self._cb_next()
                    continue
                restargs[
                    'async_headers'] = {'Range': 'bytes=%s' % data_range}
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
            if_unmodified_since=None,
            headers=dict()):
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

        :param if_unmodified_since: (str) formated date

        :param headers: (dict) placeholder to gather object headers
        """
        restargs = dict(
            version=version,
            data_range=None if range_str is None else 'bytes=%s' % range_str,
            if_match=if_match,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
            if_unmodified_since=if_unmodified_since,
            headers=dict())

        (
            blocksize,
            blockhash,
            total_size,
            hash_list,
            remote_hashes) = self._get_remote_blocks_info(obj, **restargs)
        headers.update(restargs.pop('headers'))
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
                # this should not be used in all cases
                dst.truncate(total_size)

        self._complete_cb()

    def download_to_string(
            self, obj,
            download_cb=None,
            version=None,
            range_str=None,
            if_match=None,
            if_none_match=None,
            if_modified_since=None,
            if_unmodified_since=None,
            remote_block_info=None,
            hashmap=None,
            headers=dict()):
        """Download an object to a string (multiple connections). This method
        uses threads for http requests, but stores all content in memory.

        :param obj: (str) remote object path

        :param download_cb: optional progress.bar object for downloading

        :param version: (str) file version

        :param range_str: (str) from, to are file positions (int) in bytes

        :param if_match: (str)

        :param if_none_match: (str)

        :param if_modified_since: (str) formated date

        :param if_unmodified_since: (str) formated date

        :param remote_block_info: (tuple) blocksize, blockhas, total_size and
            hash_list

        :param hashmap: (dict) the remote object hashmap, if it is available
            e.g., from another call. Used for minimizing HEAD container
            requests

        :param headers: (dict) a placeholder dict to gather object headers

        :returns: (str) the whole object contents
        """
        restargs = dict(
            version=version,
            data_range=None if range_str is None else 'bytes=%s' % range_str,
            if_match=if_match,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
            if_unmodified_since=if_unmodified_since,
            headers=dict())

        (
            blocksize,
            blockhash,
            total_size,
            hash_list,
            remote_hashes) = self._get_remote_blocks_info(
                obj, hashmap=hashmap, **restargs)
        headers.update(restargs.pop('headers'))
        assert total_size >= 0

        if download_cb:
            self.progress_bar_gen = download_cb(len(hash_list))
            self._cb_next()

        num_of_blocks = len(remote_hashes)
        ret = [''] * num_of_blocks
        self._init_thread_limit()
        flying = dict()
        try:
            for blockid, blockhash in enumerate(remote_hashes):
                start = blocksize * blockid
                is_last = start + blocksize > total_size
                end = (total_size - 1) if is_last else (start + blocksize - 1)
                data_range_str = _range_up(start, end, end, range_str)
                if data_range_str:
                    self._watch_thread_limit(flying.values())
                    restargs['data_range'] = 'bytes=%s' % data_range_str
                    flying[blockid] = self._get_block_async(obj, **restargs)
                for runid, thread in flying.items():
                    if (blockid + 1) == num_of_blocks:
                        thread.join()
                    elif thread.isAlive():
                        continue
                    if thread.exception:
                        raise thread.exception
                    ret[runid] = thread.value.content
                    self._cb_next()
                    flying.pop(runid)
            return ''.join(ret)
        except KeyboardInterrupt:
            LOG.debug('- - - wait for threads to finish')
            for thread in activethreads():
                thread.join()

    def stream_down(self, obj, dst, buffer_blocks=4, **kwargs):
        """
        Download obj to dst as a stream. Buffer-sized chunks are downloaded
            sequentially, but the blocks of each chunk are downloaded
            asynchronously, using the download_to_string method
        :param obj: (str) the remote object
        :param dst: a file descriptor allowing sequential writing
        :param buffer_blocks: (int) the size of the buffer in blocks. If it is
            1, all blocks will be downloaded sequentially
        :param kwargs: (dict) keyword arguments for download_to_string method
        """
        buffer_blocks = 1 if buffer_blocks < 2 else buffer_blocks
        hashmap = kwargs.get('hashmap', None)
        range_str = kwargs.pop('range_str', None)
        if hashmap is None:
            # Clean kwargs if it contains hashmap=None
            kwargs.pop('hashmap', None)
            # Get new hashmap
            hashmap = kwargs['hashmap'] = self.get_object_hashmap(
                obj,
                kwargs.get('version', None),
                kwargs.get('if_match', None),
                kwargs.get('if_none_match', None),
                kwargs.get('if_modified_since', None),
                kwargs.get('if_unmodified_since', None))
        block_size, obj_size = int(hashmap['block_size']), hashmap['bytes']
        buffer_size = buffer_blocks * block_size
        event = None

        def finish_event(e):
            """Blocking: stop until e is finished or raise error"""
            if e is not None:
                if e.isAlive():
                    e.join()
                if e.exception:
                    raise e.exception

        for chunk_number in range(1 + obj_size // buffer_size):
            start = chunk_number * buffer_size
            end = start + buffer_size
            end = (obj_size if (end > obj_size) else end) - 1
            kwargs['range_str'] = _range_up(start, end, obj_size, range_str)
            buffer_ = self.download_to_string(obj, **kwargs)
            finish_event(event)
            event = SilentEvent(_dump_buffer, buffer_, dst)
            event.start()
        finish_event(event)

    # Command Progress Bar method
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
            headers=dict()):
        """
        :param obj: (str) remote object path

        :param if_match: (str)

        :param if_none_match: (str)

        :param if_modified_since: (str) formated date

        :param if_unmodified_since: (str) formated date

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
                if_unmodified_since=if_unmodified_since)
        except ClientError as err:
            if err.status == 304 or err.status == 412:
                return {}
            raise
        headers.update(r.headers)
        return r.json

    def set_account_group(self, group, usernames):
        """
        :param group: (str)

        :param usernames: (list)
        """
        r = self.account_post(update=True, groups={group: usernames})
        return r

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

    def get_account_meta(self, until=None):
        """
        :param until: (str) formated date

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
        r = self.account_post(update=True, metadata=metapairs)
        return r.headers

    def del_account_meta(self, metakey):
        """
        :param metakey: (str) metadatum key
        """
        r = self.account_post(update=True, metadata={metakey: ''})
        return r.headers

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
        return r.headers

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

    def get_container_info(self, container=None, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)

        :raises ClientError: 404 Container not found
        """
        bck_cont = self.container
        try:
            self.container = container or bck_cont
            self._assert_container()
            r = self.container_head(until=until)
        except ClientError as err:
            err.details.append('for container %s' % self.container)
            raise err
        finally:
            self.container = bck_cont
        return r.headers

    def get_container_meta(self, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)
        """
        return filter_in(
            self.get_container_info(until=until), 'X-Container-Meta')

    def get_container_object_meta(self, until=None):
        """
        :param until: (str) formated date

        :returns: (dict)
        """
        return filter_in(
            self.get_container_info(until=until), 'X-Container-Object-Meta')

    def set_container_meta(self, metapairs):
        """
        :param metapairs: (dict) {key1:val1, key2:val2, ...}
        """
        assert(type(metapairs) is dict)
        r = self.container_post(update=True, metadata=metapairs)
        return r.headers

    def del_container_meta(self, metakey):
        """
        :param metakey: (str) metadatum key

        :returns: (dict) response headers
        """
        r = self.container_post(update=True, metadata={metakey: ''})
        return r.headers

    def set_container_limit(self, limit):
        """
        :param limit: (int)
        """
        r = self.container_post(update=True, quota=limit)
        return r.headers

    def set_container_versioning(self, versioning):
        """
        :param versioning: (str)
        """
        r = self.container_post(update=True, versioning=versioning)
        return r.headers

    def del_object(self, obj, until=None, delimiter=None):
        """
        :param obj: (str) remote object path

        :param until: (str) formated date

        :param delimiter: (str)
        """
        self._assert_container()
        r = self.object_delete(obj, until=until, delimiter=delimiter)
        return r.headers

    def set_object_meta(self, obj, metapairs):
        """
        :param obj: (str) remote object path

        :param metapairs: (dict) {key1:val1, key2:val2, ...}
        """
        assert(type(metapairs) is dict)
        r = self.object_post(obj, update=True, metadata=metapairs)
        return r.headers

    def del_object_meta(self, obj, metakey):
        """
        :param obj: (str) remote object path

        :param metakey: (str) metadatum key
        """
        r = self.object_post(obj, update=True, metadata={metakey: ''})
        return r.headers

    def publish_object(self, obj):
        """
        :param obj: (str) remote object path

        :returns: (str) access url
        """
        self.object_post(obj, update=True, public=True)
        info = self.get_object_info(obj)
        return info['x-object-public']
        pref, sep, rest = self.endpoint_url.partition('//')
        base = rest.split('/')[0]
        return '%s%s%s/%s' % (pref, sep, base, info['x-object-public'])

    def unpublish_object(self, obj):
        """
        :param obj: (str) remote object path
        """
        r = self.object_post(obj, update=True, public=False)
        return r.headers

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
            read_permission=False, write_permission=False):
        """Give read/write permisions to an object.

        :param obj: (str) remote object path

        :param read_permission: (list - bool) users and user groups that get
            read permission for this object - False means all previous read
            permissions will be removed

        :param write_permission: (list - bool) of users and user groups to get
           write permission for this object - False means all previous write
           permissions will be removed

        :returns: (dict) response headers
        """

        perms = dict(read=read_permission or '', write=write_permission or '')
        r = self.object_post(obj, update=True, permissions=perms)
        return r.headers

    def del_object_sharing(self, obj):
        """
        :param obj: (str) remote object path
        """
        return self.set_object_sharing(obj)

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
        headers = {}
        if upload_cb:
            self.progress_bar_gen = upload_cb(nblocks)
            self._cb_next()
        flying = {}
        self._init_thread_limit()
        try:
            for i in range(nblocks):
                block = source_file.read(min(blocksize, filesize - offset))
                offset += len(block)

                self._watch_thread_limit(flying.values())
                unfinished = {}
                flying[i] = SilentEvent(
                    method=self.object_post,
                    obj=obj,
                    update=True,
                    content_range='bytes */*',
                    content_type='application/octet-stream',
                    content_length=len(block),
                    data=block)
                flying[i].start()

                for key, thread in flying.items():
                    if thread.isAlive():
                        if i < (nblocks - 1):
                            unfinished[key] = thread
                            continue
                        thread.join()
                    if thread.exception:
                        raise thread.exception
                    headers[key] = thread.value.headers
                    self._cb_next()
                flying = unfinished
        except KeyboardInterrupt:
            LOG.debug('- - - wait for threads to finish')
            for thread in activethreads():
                thread.join()
        finally:
            from time import sleep
            sleep(2 * len(activethreads()))
            self._cb_next()
        return headers.values()

    def truncate_object(self, obj, upto_bytes):
        """
        :param obj: (str) remote object path

        :param upto_bytes: max number of bytes to leave on file

        :returns: (dict) response headers
        """
        ctype = self.get_object_info(obj)['content-type']
        r = self.object_post(
            obj,
            update=True,
            content_range='bytes 0-%s/*' % upto_bytes,
            content_type=ctype,
            object_bytes=upto_bytes,
            source_object=path4url(self.container, obj))
        return r.headers

    def overwrite_object(
            self, obj, start, end, source_file,
            source_version=None, upload_cb=None):
        """Overwrite a part of an object from local source file
        ATTENTION: content_type must always be application/octet-stream

        :param obj: (str) remote object path

        :param start: (int) position in bytes to start overwriting from

        :param end: (int) position in bytes to stop overwriting at

        :param source_file: open file descriptor

        :param upload_db: progress.bar for uploading
        """

        self._assert_container()
        r = self.get_object_info(obj, version=source_version)
        rf_size = int(r['content-length'])
        start, end = int(start), int(end)
        assert rf_size >= start, 'Range start %s exceeds file size %s' % (
            start, rf_size)
        assert rf_size >= end, 'Range end %s exceeds file size %s' % (
            end, rf_size)
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
        datasize = end - start + 1
        nblocks = 1 + (datasize - 1) // blocksize
        offset = 0
        if upload_cb:
            self.progress_bar_gen = upload_cb(nblocks)
            self._cb_next()
        headers = []
        for i in range(nblocks):
            read_size = min(blocksize, filesize - offset, datasize - offset)
            block = source_file.read(read_size)
            r = self.object_post(
                obj,
                update=True,
                content_type='application/octet-stream',
                content_length=len(block),
                content_range='bytes %s-%s/*' % (
                    start + offset,
                    start + offset + len(block) - 1),
                source_version=source_version,
                data=block)
            headers.append(dict(r.headers))
            offset += len(block)
            self._cb_next()
        self._cb_next()
        return headers

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

        :returns: (dict) response headers
        """
        self._assert_account()
        self.container = dst_container
        src_path = path4url(src_container, src_object)
        r = self.object_put(
            dst_object or src_object,
            success=201,
            copy_from=src_path,
            content_length=0,
            source_version=source_version,
            source_account=source_account,
            public=public,
            content_type=content_type,
            delimiter=delimiter)
        return r.headers

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

        :returns: (dict) response headers
        """
        self._assert_account()
        self.container = dst_container
        dst_object = dst_object or src_object
        src_path = path4url(src_container, src_object)
        r = self.object_put(
            dst_object,
            success=201,
            move_from=src_path,
            content_length=0,
            source_account=source_account,
            source_version=source_version,
            public=public,
            content_type=content_type,
            delimiter=delimiter)
        return r.headers

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

    def reassign_container(self, project_id):
        r = self.container_post(project_id=project_id)
        return r.headers
