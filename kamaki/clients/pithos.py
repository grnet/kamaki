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
import gevent.pool

from os import fstat, path
from hashlib import new as newhashlib
from time import time, sleep
from datetime import datetime
import sys

from binascii import hexlify
from .pithos_sh_lib.hashmap import HashMap

from .pithos_rest_api import PithosRestAPI
from .storage import ClientError
from .utils import path4url, filter_in

def pithos_hash(block, blockhash):
    h = newhashlib(blockhash)
    h.update(block.rstrip('\x00'))
    return h.hexdigest()

class PithosClient(PithosRestAPI):
    """GRNet Pithos API client"""

    def __init__(self, base_url, token, account=None, container = None):
        super(PithosClient, self).__init__(base_url, token, account = account,
            container = container)
        self.async_pool = None

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
                _stderr = None
                try:
                    _stderr = sys._stderr
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
       
    #upload_* auxiliary methods 
    def _get_file_block_info(self, fileobj, size=None):
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        blockhash = meta['x-container-block-hash']
        size = size if size is not None else fstat(fileobj.fileno()).st_size
        nblocks = 1 + (size - 1) // blocksize
        return (blocksize, blockhash, size, nblocks)

    def _get_missing_hashes(self, obj, json, size=None, format='json', hashmap=True,
        content_type=None, etag=None, content_encoding=None, content_disposition=None,
        permitions=None, public=None, success=(201, 409)):
        r = self.object_put(obj, format='json', hashmap=True, content_type=content_type,
            json=json, etag=etag, content_encoding=content_encoding,
            content_disposition=content_disposition, permitions=permitions, public=public,
            success=success)
        if r.status_code == 201:
            return None
        return r.json

    def _caclulate_uploaded_blocks(self, blocksize, blockhash, size, nblocks, hashes, hmap, fileobj,
        hash_cb=None):
        offset=0
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
        """upload missing blocks asynchronously in a pseudo-parallel fashion (greenlets)
        """
        if upload_cb:
            upload_gen = upload_cb(len(missing))
            upload_gen.next()

        flying = []
        for hash in missing:
            offset, bytes = hmap[hash]
            fileobj.seek(offset)
            data = fileobj.read(bytes)
            r = self.put_block_async(data, hash)
            flying.append(r)
            for r in flying:
                if r.ready():
                    if r.exception:
                        raise r.exception
                    if upload_cb:
                        upload_gen.next()
            flying = [r for r in flying if not r.ready()]
        while upload_cb:
            try:
                upload_gen.next()
            except StopIteration:
                break
        gevent.joinall(flying)

    def upload_object(self, obj, f, size=None, hash_cb=None, upload_cb=None, etag=None,
        content_encoding=None, content_disposition=None, content_type=None, sharing=None,
        public=None):
        self.assert_container()

        #init
        block_info = (blocksize, blockhash, size, nblocks) = self._get_file_block_info(f, size)
        (hashes, hmap, offset) = ([], {}, 0)
        content_type = 'application/octet-stream' if content_type is None else content_type

        self._caclulate_uploaded_blocks(*block_info, hashes=hashes, hmap=hmap, fileobj=f,
            hash_cb=hash_cb)

        hashmap = dict(bytes=size, hashes=hashes)
        missing = self._get_missing_hashes(obj, hashmap, content_type=content_type, size=size,
            etag=etag, content_encoding=content_encoding, content_disposition=content_disposition,
            permitions=sharing, public=public)

        if missing is None:
            return
        self._upload_missing_blocks(missing, hmap, f, upload_cb=upload_cb)

        self.object_put(obj, format='json', hashmap=True, content_type=content_type, 
            json=hashmap, success=201)
      
    #download_* auxiliary methods
    def _get_object_block_info(self,obj, **kwargs):
        #retrieve object hashmap
        hashmap = self.get_object_hashmap(obj, **kwargs)
        blocksize = int(hashmap['block_size'])
        blockhash = hashmap['block_hash']
        total_size = hashmap['bytes']
        hmap = hashmap['hashes']
        map_dict = {}
        for h in hmap:
            map_dict[h] = True
        return (blocksize, blockhash, total_size, hmap, map_dict)

    def _get_range_limits(self, range):
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
        return (custom_start, custom_end)

    def _get_downloaded_blocks(self, hmap, fileobj, blocksize, blockhash, map_dict,
        overide=False, download_gen=None):
        if fileobj.isatty() or not path.exists(fileobj.name):
            return {}
        h = HashMap(blocksize, blockhash)
        with_progress_bar = False if download_gen is None else True
        h.load(fileobj, with_progress_bar)
        resumed = {}
        for i, x in enumerate(h):
            existing_hash = hexlify(x)
            if existing_hash in map_dict:
        #resume if some blocks have been downloaded
                resumed[existing_hash] = i
                if with_progress_bar:
                    try:
                        download_gen.next()
                    except:
                        pass
            elif not overide:
                raise ClientError(message='Local file is substantialy different',
                    status=600)
        return resumed

    def _get_block_range(self, blockid, blocksize, total_size, custom_start, custom_end):
        start = blockid*blocksize
        if custom_start is not None:
            if start < custom_start:
                start = custom_start
            elif start > custom_end:
                return (None, None)
        end = start + blocksize -1 if start+blocksize < total_size else total_size -1
        if custom_end is not None and end > custom_end:
            end = custom_end
        return (start, end)

    def _manage_downloading_greenlets(self, flying, objfile, broken_greenlets = [], sleeptime=0):
        newflying = []
        for v in flying:
            h = v['handler']
            if h.ready():
                if h.exception:
                    h.release()
                    raise h.exception
                try:
                    block = h.value.content
                except AttributeError:
                    #catch greenlets that break due to an eventlist bug
                    print('- - - - - > Got a borken greenlet here')
                    broken_greenlets.append(v)
                    continue
                objfile.seek(v['start'])
                objfile.write(block)
                objfile.flush()
            else:
                #if there are unfinished greenlets, sleep for some time - be carefull with that
                sleep(sleeptime)
                newflying.append(v)
        return newflying

    def _get_block(self, obj, **kwargs):
        return self.object_get(obj, success=(200, 206), binary=True, **kwargs)

    def _get_block_async(self, obj, **kwargs):
        class SilentGreenlet(gevent.Greenlet):
            def _report_error(self, exc_info):
                _stderr = sys._stderr
                try:
                    sys.stderr = StringIO()
                    gevent.Greenlet._report_error(self, exc_info)
                finally:
                    sys.stderr = _stderr
        POOL_SIZE =7
        if self.async_pool is None:
            self.async_pool = gevent.pool.Pool(size=POOL_SIZE)
        g = SilentGreenlet(self._get_block, obj, **kwargs)
        self.async_pool.start(g)
        return g

    def _async_download_missing_blocks(self, obj, objfile, hmap, resumed, blocksize, total_size, 
        download_gen=None, custom_start = None, custom_end=None, **restargs):
        """Attempt pseudo-multithreaded (with greenlets) download of blocks, or if that
        is not possible retreat to sequensial block download
        """

        flying = []
        for i, h in enumerate(hmap):
            if h in resumed:
                continue
            if download_gen:
                try:
                    download_gen.next()
                except StopIteration:
                    pass
            (start, end) = self._get_block_range(i, blocksize, total_size, custom_start, custom_end)
            if start is None:
                continue
            data_range = 'bytes=%s-%s'%(start, end)
            handler = self._get_block_async(obj, data_range=data_range, **restargs)
            flying.append({'handler':handler, 'start':start, 'data_range':data_range})
            broken = []
            flying = self._manage_downloading_greenlets(flying, objfile, broken_greenlets=broken)
            #workaround for eventlib bug that breaks greenlets: replace them with new ones
            for brgr in broken:
                brgr['handler'] = self._get_block_async(obj, data_range=brgr['data_range'],
                    **restargs)
                flying.append(brgr)
                               
        #write the last results and exit
        while len(flying) > 0:
            broken = []
            flying=self._manage_downloading_greenlets(flying, objfile, broken_greenlets=broken,
                sleeptime=0.1)
            #workaround for eventlib bug that breaks greenlets: replace them with new ones
            for brgr in broken:
                brgr['handler'] = self._get_block_async(obj, data_range=brgr['data_range'],
                    **restargs)
                flying.append(brgr)
        objfile.truncate(total_size)

        gevent.joinall(flying)

    def _append_missing_blocks(self, obj, objfile, hmap, resumed, blocksize, total_size,
        download_gen=None, custom_start=None, custom_end=None, **restargs):
        for i, h in enumerate(hmap):
            if h in resumed:
                continue
            if download_gen:
                try:
                    download_gen.next()
                except StopIteration:
                    pass
            (start, end) = self._get_block_range(i, blocksize, total_size, custom_start, custom_end)
            data_range = 'bytes=%s-%s'%(start, end)
            r = self._get_block(obj, data_range=data_range, **restargs)
            objfile.write(r.content)
            objfile.flush() 

    def download_object(self, obj, objfile, download_cb=None, version=None, overide=False, range=None,
        if_match=None, if_none_match=None, if_modified_since=None, if_unmodified_since=None):
        """overide is forcing the local file to become exactly as the remote, even if it is
        substantialy different
        """

        self.assert_container()

        (blocksize, blockhash, total_size, hmap, map_dict) = self._get_object_block_info(obj,
            version=version, if_match=if_match, if_none_match=if_none_match,
            if_modified_since=if_modified_since, if_unmodified_since=if_unmodified_since)

        if total_size <= 0:
            return

        (custom_start, custom_end) = (None, None) if range is None \
            else self._get_range_limits(range)

        #load progress bar
        if download_cb is not None:
            download_gen = download_cb(total_size/blocksize + 1)
            download_gen.next()

        resumed = self._get_downloaded_blocks(hmap, objfile, blocksize, blockhash, map_dict,
            overide=overide, download_gen=download_gen)
        restargs=dict(version=version, if_etag_match=if_match, if_etag_not_match=if_none_match,
            if_modified_since=if_modified_since, if_unmodified_since=if_unmodified_since)

        if objfile.isatty():
            self._append_missing_blocks(obj, objfile, hmap, resumed, blocksize, total_size,
                download_gen, custom_start=custom_start, custom_end=custom_end, **restargs)
        else:
            self._async_download_missing_blocks(obj, objfile, hmap, resumed, blocksize, total_size,
                download_gen, custom_start=custom_start, custom_end=custom_end, **restargs)


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
        return r.json

    def set_account_group(self, group, usernames):
        self.account_post(update=True, groups = {group:usernames})

    def del_account_group(self, group):
        self.account_post(update=True, groups={group:[]})

    def get_account_info(self, until=None):
        r = self.account_head(until=until)
        if r.status_code == 401:
            raise ClientError("No authorization")
        return r.headers

    def get_account_quota(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-Quota', exactMatch = True)

    def get_account_versioning(self):
        return filter_in(self.get_account_info(), 'X-Account-Policy-Versioning', exactMatch = True)

    def get_account_meta(self, until=None):
        return filter_in(self.get_account_info(until = until), 'X-Account-Meta-')

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
        self.container = container
        return filter_in(self.get_container_info(), 'X-Container-Policy-Versioning')

    def get_container_quota(self, container):
        self.container = container
        return filter_in(self.get_container_info(), 'X-Container-Policy-Quota')

    def get_container_info(self, until = None):
        r = self.container_head(until=until)
        return r.headers

    def get_container_meta(self, until = None):
        return filter_in(self.get_container_info(until=until), 'X-Container-Meta')

    def get_container_object_meta(self, until = None):
        return filter_in(self.get_container_info(until=until), 'X-Container-Object-Meta')

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

    def get_object_info(self, obj, version=None):
        r = self.object_head(obj, version=version)
        return r.headers

    def get_object_meta(self, obj, version=None):
        return filter_in(self.get_object_info(obj, version=version), 'X-Object-Meta')

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
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
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
        meta = self.get_container_info()
        blocksize = int(meta['x-container-block-size'])
        filesize = fstat(source_file.fileno()).st_size
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