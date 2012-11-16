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

from threading import Thread
from threading import enumerate as activethreads

from os import fstat
from hashlib import new as newhashlib
from time import time

from binascii import hexlify

from kamaki.clients.pithos_rest_api import PithosRestAPI
from kamaki.clients.storage import ClientError
from kamaki.clients.utils import path4url, filter_in
from StringIO import StringIO


def pithos_hash(block, blockhash):
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


class SilentEvent(Thread):
    """ Thread-run method(*args, **kwargs)
        put exception in exception_bucket
    """
    def __init__(self, method, *args, **kwargs):
        super(self.__class__, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs

    @property
    def exception(self):
        return getattr(self, '_exception', False)

    @property
    def value(self):
        return getattr(self, '_value', None)

    def run(self):
        try:
            self._value = self.method(*(self.args), **(self.kwargs))
        except Exception as e:
            print('______\n%s\n_______' % e)
            self._exception = e


class PithosClient(PithosRestAPI):
    """GRNet Pithos API client"""

    _thread_exceptions = []

    def __init__(self, base_url, token, account=None, container=None):
        super(PithosClient, self).__init__(base_url, token, account, container)

    def purge_container(self):
        r = self.container_delete(until=unicode(time()))
        r.release()

    def upload_object_unchunked(self, obj, f,
        withHashFile=False,
        size=None,
        etag=None,
        content_encoding=None,
        content_disposition=None,
        content_type=None,
        sharing=None,
        public=None):
        self.assert_container()

        if withHashFile:
            data = f.read()
            try:
                import json
                data = json.dumps(json.loads(data))
            except ValueError:
                raise ClientError(message='"%s" is not json-formated' % f.name,
                    status=1)
            except SyntaxError:
                raise ClientError(message='"%s" is not a valid hashmap file'\
                % f.name, status=1)
            f = StringIO(data)
        data = f.read(size) if size is not None else f.read()
        r = self.object_put(obj,
            data=data,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            content_type=content_type,
            permissions=sharing,
            public=public,
            success=201)
        r.release()

    # upload_* auxiliary methods
    def put_block_async(self, data, hash):
        event = SilentEvent(method=self.put_block, data=data, hash=hash)
        event.start()
        return event

    def put_block(self, data, hash):
        r = self.container_post(update=True,
            content_type='application/octet-stream',
            content_length=len(data),
            data=data,
            format='json')
        assert r.json[0] == hash, 'Local hash does not match server'

    def create_object_by_manifestation(self, obj,
        etag=None,
        content_encoding=None,
        content_disposition=None,
        content_type=None,
        sharing=None,
        public=None):
        self.assert_container()
        r = self.object_put(obj,
            content_length=0,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            content_type=content_type,
            permissions=sharing,
            public=public,
            manifest='%s/%s' % (self.container, obj))
        r.release()

    def _get_file_block_info(self, fileobj, size=None):
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        blockhash = meta['x-container-block-hash']
        size = size if size is not None else fstat(fileobj.fileno()).st_size
        nblocks = 1 + (size - 1) // blocksize
        return (blocksize, blockhash, size, nblocks)

    def _get_missing_hashes(self, obj, json,
        size=None,
        format='json',
        hashmap=True,
        content_type=None,
        etag=None,
        content_encoding=None,
        content_disposition=None,
        permissions=None,
        public=None,
        success=(201, 409)):
        r = self.object_put(obj,
            format='json',
            hashmap=True,
            content_type=content_type,
            json=json,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            permissions=permissions,
            public=public,
            success=success)
        if r.status_code == 201:
            r.release()
            return None
        return r.json

    def _caclulate_uploaded_blocks(self,
        blocksize,
        blockhash,
        size,
        nblocks,
        hashes,
        hmap,
        fileobj,
        hash_cb=None):
        offset = 0
        if hash_cb:
            hash_gen = hash_cb(nblocks)
            hash_gen.next()

        for i in range(nblocks):
            block = fileobj.read(min(blocksize, size - offset))
            bytes = len(block)
            hash = pithos_hash(block, blockhash)
            hashes.append(hash)
            hmap[hash] = (offset, bytes)
            offset += bytes
            if hash_cb:
                hash_gen.next()
        assert offset == size

    def _upload_missing_blocks(self, missing, hmap, fileobj, upload_cb=None):
        """upload missing blocks asynchronously. Use greenlets to avoid waiting
        """
        if upload_cb:
            upload_gen = upload_cb(len(missing))
            upload_gen.next()

        self._init_thread_limit()

        flying = []
        for hash in missing:
            offset, bytes = hmap[hash]
            fileobj.seek(offset)
            data = fileobj.read(bytes)
            r = self.put_block_async(data, hash)
            flying.append(r)
            unfinished = []
            for i, thread in enumerate(flying):

                unfinished = self._watch_thread_limit(unfinished)

                if thread.isAlive() or thread.exception:
                    unfinished.append(thread)
                else:
                    if upload_cb:
                        upload_gen.next()
            flying = unfinished

        for thread in flying:
            thread.join()

        failures = [r for r in flying if r.exception]
        if len(failures):
            details = ', '.join([' (%s).%s' % (i, r.exception)\
                for i, r in enumerate(failures)])
            raise ClientError(message="Block uploading failed",
                status=505,
                details=details)

        while upload_cb:
            try:
                upload_gen.next()
            except StopIteration:
                break

    def upload_object(self, obj, f,
        size=None,
        hash_cb=None,
        upload_cb=None,
        etag=None,
        content_encoding=None,
        content_disposition=None,
        content_type=None,
        sharing=None,
        public=None):
        self.assert_container()

        #init
        block_info = (blocksize, blockhash, size, nblocks) =\
            self._get_file_block_info(f, size)
        (hashes, hmap, offset) = ([], {}, 0)
        if content_type is None:
            content_type = 'application/octet-stream'

        self._caclulate_uploaded_blocks(*block_info,
            hashes=hashes,
            hmap=hmap,
            fileobj=f,
            hash_cb=hash_cb)

        hashmap = dict(bytes=size, hashes=hashes)
        missing = self._get_missing_hashes(obj, hashmap,
            content_type=content_type,
            size=size,
            etag=etag,
            content_encoding=content_encoding,
            content_disposition=content_disposition,
            permissions=sharing,
            public=public)

        if missing is None:
            return
        try:
            self._upload_missing_blocks(missing, hmap, f, upload_cb=upload_cb)
        except KeyboardInterrupt:
            print('- - - wait for threads to finish')
            for thread in activethreads():
                thread.join()
            raise

        r = self.object_put(
            obj,
            format='json',
            hashmap=True,
            content_type=content_type,
            json=hashmap,
            success=201)
        r.release()

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
            map_dict[h] = i
        return (blocksize, blockhash, total_size, hashmap['hashes'], map_dict)

    def _dump_blocks_sync(self,
        obj,
        remote_hashes,
        blocksize,
        total_size,
        dst,
        range,
        **restargs):
        for blockid, blockhash in enumerate(remote_hashes):
            if blockhash == None:
                continue
            start = blocksize * blockid
            end = total_size - 1 if start + blocksize > total_size\
                else start + blocksize - 1
            (start, end) = _range_up(start, end, range)
            restargs['data_range'] = 'bytes=%s-%s' % (start, end)
            r = self.object_get(obj, success=(200, 206), **restargs)
            self._cb_next()
            dst.write(r.content)
            dst.flush()

    def _get_block_async(self, obj, **restargs):
        event = SilentEvent(self.object_get,
            obj,
            success=(200, 206),
            **restargs)
        event.start()
        return event

    def _hash_from_file(self, fp, start, size, blockhash):
        fp.seek(start)
        block = fp.read(size)
        h = newhashlib(blockhash)
        h.update(block.strip('\x00'))
        return hexlify(h.digest())

    def _thread2file(self,
        flying,
        local_file,
        offset=0,
        **restargs):
        """write the results of a greenleted rest call to a file
        @offset: the offset of the file up to blocksize
            - e.g. if the range is 10-100, all
        blocks will be written to normal_position - 10"""
        finished = []
        for i, (start, g) in enumerate(flying.items()):
            #if i % self.POOL_SIZE == 0:
            #    g.join(0.1)
            if not g.isAlive():
                if g.exception:
                    raise g.exception
                block = g.value.content
                local_file.seek(start - offset)
                local_file.write(block)
                self._cb_next()
                finished.append(flying.pop(start))
        local_file.flush()
        return finished

    def _dump_blocks_async(self,
        obj,
        remote_hashes,
        blocksize,
        total_size,
        local_file,
        blockhash=None,
        resume=False,
        filerange=None,
        **restargs):

        file_size = fstat(local_file.fileno()).st_size if resume else 0
        flying = {}
        finished = []
        offset = 0
        if filerange is not None:
            rstart = int(filerange.split('-')[0])
            offset = rstart if blocksize > rstart else rstart % blocksize

        self._init_thread_limit()
        for block_hash, blockid in remote_hashes.items():
            start = blocksize * blockid
            if start < file_size\
            and block_hash == self._hash_from_file(
                    local_file,
                    start,
                    blocksize,
                    blockhash):
                self._cb_next()
                continue
            self._watch_thread_limit(flying.values())
            finished += self._thread2file(
                flying,
                local_file,
                offset,
                **restargs)
            end = total_size - 1 if start + blocksize > total_size\
                else start + blocksize - 1
            (start, end) = _range_up(start, end, filerange)
            if start == end:
                self._cb_next()
                continue
            restargs['async_headers'] = {'Range': 'bytes=%s-%s' % (start, end)}
            flying[start] = self._get_block_async(obj, **restargs)

        for thread in flying.values():
            thread.join()
        finished += self._thread2file(flying, local_file, offset, **restargs)

    def download_object(self,
        obj,
        dst,
        download_cb=None,
        version=None,
        overide=False,
        resume=False,
        range=None,
        if_match=None,
        if_none_match=None,
        if_modified_since=None,
        if_unmodified_since=None):

        restargs = dict(version=version,
            data_range=None if range is None else 'bytes=%s' % range,
            if_match=if_match,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
            if_unmodified_since=if_unmodified_since)

        (blocksize,
            blockhash,
            total_size,
            hash_list,
            remote_hashes) = self._get_remote_blocks_info(obj, **restargs)
        assert total_size >= 0

        if download_cb:
            self.progress_bar_gen = download_cb(len(remote_hashes))
            self._cb_next()

        if dst.isatty():
            self._dump_blocks_sync(obj,
                hash_list,
                blocksize,
                total_size,
                dst,
                range,
                **restargs)
        else:
            if len(remote_hashes) > self.POOL_SIZE:
                self.POOL_SIZE = len(remote_hashes) // 10
            self._dump_blocks_async(obj,
                remote_hashes,
                blocksize,
                total_size,
                dst,
                blockhash,
                resume,
                range,
                **restargs)
            if range is None:
                dst.truncate(total_size)

        self._complete_cb()

    #Command Progress Bar method
    def _cb_next(self):
        if hasattr(self, 'progress_bar_gen'):
            try:
                self.progress_bar_gen.next()
            except:
                pass

    def _complete_cb(self):
        while True:
            try:
                self.progress_bar_gen.next()
            except:
                break

    # Untested - except is download_object is tested first
    def get_object_hashmap(self, obj,
        version=None,
        if_match=None,
        if_none_match=None,
        if_modified_since=None,
        if_unmodified_since=None,
        data_range=None):
        try:
            r = self.object_get(obj,
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
        r = self.account_post(update=True, groups={group: usernames})
        r.release()

    def del_account_group(self, group):
        r = self.account_post(update=True, groups={group: []})
        r.release()

    def get_account_info(self, until=None):
        r = self.account_head(until=until)
        if r.status_code == 401:
            raise ClientError("No authorization")
        return r.headers

    def get_account_quota(self):
        return filter_in(self.get_account_info(),
            'X-Account-Policy-Quota',
            exactMatch=True)

    def get_account_versioning(self):
        return filter_in(self.get_account_info(),
            'X-Account-Policy-Versioning',
            exactMatch=True)

    def get_account_meta(self, until=None):
        return filter_in(self.get_account_info(until=until), 'X-Account-Meta-')

    def get_account_group(self):
        return filter_in(self.get_account_info(), 'X-Account-Group-')

    def set_account_meta(self, metapairs):
        assert(type(metapairs) is dict)
        r = self.account_post(update=True, metadata=metapairs)
        r.release()

    def del_account_meta(self, metakey):
        r = self.account_post(update=True, metadata={metakey: ''})
        r.release()

    def set_account_quota(self, quota):
        r = self.account_post(update=True, quota=quota)
        r.release()

    def set_account_versioning(self, versioning):
        r = self.account_post(update=True, versioning=versioning)
        r.release()

    def list_containers(self):
        r = self.account_get()
        return r.json

    def del_container(self, until=None, delimiter=None):
        self.assert_container()
        r = self.container_delete(until=until,
            delimiter=delimiter,
            success=(204, 404, 409))
        r.release()
        if r.status_code == 404:
            raise ClientError('Container "%s" does not exist' % self.container,
                r.status_code)
        elif r.status_code == 409:
            raise ClientError('Container "%s" is not empty' % self.container,
                r.status_code)

    def get_container_versioning(self, container):
        self.container = container
        return filter_in(self.get_container_info(),
            'X-Container-Policy-Versioning')

    def get_container_quota(self, container):
        self.container = container
        return filter_in(self.get_container_info(), 'X-Container-Policy-Quota')

    def get_container_info(self, until=None):
        r = self.container_head(until=until)
        return r.headers

    def get_container_meta(self, until=None):
        return filter_in(self.get_container_info(until=until),
            'X-Container-Meta')

    def get_container_object_meta(self, until=None):
        return filter_in(self.get_container_info(until=until),
            'X-Container-Object-Meta')

    def set_container_meta(self, metapairs):
        assert(type(metapairs) is dict)
        r = self.container_post(update=True, metadata=metapairs)
        r.release()

    def del_container_meta(self, metakey):
        r = self.container_post(update=True, metadata={metakey: ''})
        r.release()

    def set_container_quota(self, quota):
        r = self.container_post(update=True, quota=quota)
        r.release()

    def set_container_versioning(self, versioning):
        r = self.container_post(update=True, versioning=versioning)
        r.release()

    def del_object(self, obj, until=None, delimiter=None):
        self.assert_container()
        r = self.object_delete(obj, until=until, delimiter=delimiter)
        r.release()

    def set_object_meta(self, object, metapairs):
        assert(type(metapairs) is dict)
        r = self.object_post(object, update=True, metadata=metapairs)
        r.release()

    def del_object_meta(self, metakey, object):
        r = self.object_post(object, update=True, metadata={metakey: ''})
        r.release()

    def publish_object(self, object):
        r = self.object_post(object, update=True, public=True)
        r.release()

    def unpublish_object(self, object):
        r = self.object_post(object, update=True, public=False)
        r.release()

    def get_object_info(self, obj, version=None):
        r = self.object_head(obj, version=version)
        return r.headers

    def get_object_meta(self, obj, version=None):
        return filter_in(self.get_object_info(obj, version=version),
            'X-Object-Meta')

    def get_object_sharing(self, object):
        r = filter_in(self.get_object_info(object),
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

    def set_object_sharing(self, object,
        read_permition=False,
        write_permition=False):
        """Give read/write permisions to an object.
           @param object is the object to change sharing permissions
 onto
           @param read_permition is a list of users and user groups that
                get read permition for this object
                False means all previous read permissions
 will be removed
           @param write_perimition is a list of users and user groups to
                get write permition for this object
                False means all previous read permissions
 will be removed
        """
        perms = dict(read='' if not read_permition else read_permition,
            write='' if not write_permition else write_permition)
        r = self.object_post(object, update=True, permissions=perms)
        r.release()

    def del_object_sharing(self, object):
        self.set_object_sharing(object)

    def append_object(self, object, source_file, upload_cb=None):
        """@param upload_db is a generator for showing progress of upload
            to caller application, e.g. a progress bar. Its next is called
            whenever a block is uploaded
        """
        self.assert_container()
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
        nblocks = 1 + (filesize - 1) // blocksize
        offset = 0
        if upload_cb is not None:
            upload_gen = upload_cb(nblocks)
        for i in range(nblocks):
            block = source_file.read(min(blocksize, filesize - offset))
            offset += len(block)
            r = self.object_post(object,
                update=True,
                content_range='bytes */*',
                content_type='application/octet-stream',
                content_length=len(block),
                data=block)
            r.release()

            if upload_cb is not None:
                upload_gen.next()

    def truncate_object(self, object, upto_bytes):
        r = self.object_post(object,
            update=True,
            content_range='bytes 0-%s/*' % upto_bytes,
            content_type='application/octet-stream',
            object_bytes=upto_bytes,
            source_object=path4url(self.container, object))
        r.release()

    def overwrite_object(self,
        object,
        start,
        end,
        source_file,
        upload_cb=None):
        """Overwrite a part of an object with given source file
           @start the part of the remote object to start overwriting from,
                in bytes
           @end the part of the remote object to stop overwriting to, in bytes
        """
        self.assert_container()
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
        datasize = int(end) - int(start) + 1
        nblocks = 1 + (datasize - 1) // blocksize
        offset = 0
        if upload_cb is not None:
            upload_gen = upload_cb(nblocks)
        for i in range(nblocks):
            block = source_file.read(min(blocksize,
                filesize - offset,
                datasize - offset))
            offset += len(block)
            r = self.object_post(object,
                update=True,
                content_type='application/octet-stream',
                content_length=len(block),
                content_range='bytes %s-%s/*' % (start, end),
                data=block)
            r.release()

            if upload_cb is not None:
                upload_gen.next()

    def copy_object(self, src_container, src_object, dst_container,
        dst_object=False,
        source_version=None,
        public=False,
        content_type=None,
        delimiter=None):
        self.assert_account()
        self.container = dst_container
        dst_object = dst_object or src_object
        src_path = path4url(src_container, src_object)
        r = self.object_put(dst_object,
            success=201,
            copy_from=src_path,
            content_length=0,
            source_version=source_version,
            public=public,
            content_type=content_type,
            delimiter=delimiter)
        r.release()

    def move_object(self, src_container, src_object, dst_container,
        dst_object=False,
        source_version=None,
        public=False,
        content_type=None,
        delimiter=None):
        self.assert_account()
        self.container = dst_container
        dst_object = dst_object or src_object
        src_path = path4url(src_container, src_object)
        r = self.object_put(dst_object,
            success=201,
            move_from=src_path,
            content_length=0,
            source_version=source_version,
            public=public,
            content_type=content_type,
            delimiter=delimiter)
        r.release()

    def get_sharing_accounts(self, limit=None, marker=None, *args, **kwargs):
        """Get accounts that share with self.account"""
        self.assert_account()

        self.set_param('format', 'json')
        self.set_param('limit', limit, iff=limit is not None)
        self.set_param('marker', marker, iff=marker is not None)

        path = ''
        success = kwargs.pop('success', (200, 204))
        r = self.get(path, *args, success=success, **kwargs)
        return r.json

    def get_object_versionlist(self, path):
        self.assert_container()
        r = self.object_get(path, format='json', version='list')
        return r.json['versions']
