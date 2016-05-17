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

from kamaki.clients.cyclades.rest_api import (
    CycladesComputeRestClient, CycladesBlockStorageRestClient)
from kamaki.clients.network import NetworkClient
from kamaki.clients.utils import path4url
from kamaki.clients import ClientError, Waiter, wait


class CycladesComputeClient(CycladesComputeRestClient, Waiter):
    """Synnefo Cyclades Compute API client"""

    CONSOLE_TYPES = ('vnc', 'vnc-ws', 'vnc-wss')

    def create_server(
            self, name, flavor_id, image_id,
            metadata=None, personality=None, networks=None, project_id=None,
            response_headers=dict(location=None)):
        """Submit request to create a new server

        :param name: (str)

        :param flavor_id: integer id denoting a preset hardware configuration

        :param image_id: (str) id denoting the OS image to run on virt. server

        :param metadata: (dict) vm metadata updated by os/users image metadata

        :param personality: a list of (file path, file contents) tuples,
            describing files to be injected into virtual server upon creation

        :param networks: (list of dicts) Networks to connect to, list this:
            "networks": [
            {"uuid": <network_uuid>},
            {"uuid": <network_uuid>, "fixed_ip": address},
            {"port": <port_id>}, ...]
            ATTENTION: Empty list is different to None. None means 'apply the
            default server policy', empty list means 'do not attach a network'

        :param project_id: the project where to assign the server

        :returns: a dict with the new virtual server details

        :raises ClientError: wraps request errors
        """
        image = self.get_image_details(image_id)
        metadata = metadata or dict()
        for key in ('os', 'users'):
            try:
                metadata.setdefault(key, image['metadata'][key])
            except KeyError:
                pass

        req = {'server': {
            'name': name, 'flavorRef': flavor_id, 'imageRef': image_id}}

        if metadata:
            req['server']['metadata'] = metadata

        if personality:
            req['server']['personality'] = personality

        if networks is not None:
            req['server']['networks'] = networks

        if project_id is not None:
            req['server']['project'] = project_id

        r = self.servers_post(json_data=req, success=(202, ))
        for k, v in response_headers.items():
            response_headers[k] = r.headers.get(k, v)
        return r.json['server']

    def set_firewall_profile(self, server_id, profile, port_id):
        """Set the firewall profile for the public interface of a server
        :param server_id: integer (str or int)
        :param profile: (str) ENABLED | DISABLED | PROTECTED
        :param port_id: (str) This port must connect to a public network
        :returns: (dict) response headers
        """
        req = {'firewallProfile': {'profile': profile, 'nic': port_id}}
        r = self.servers_action_post(server_id, json_data=req, success=202)
        return r.headers

    def start_server(self, server_id):
        """Submit a startup request

        :param server_id: integer (str or int)

        :returns: (dict) response headers
        """
        req = {'start': {}}
        r = self.servers_action_post(server_id, json_data=req, success=202)
        return r.headers

    def shutdown_server(self, server_id):
        """Submit a shutdown request

        :param server_id: integer (str or int)

        :returns: (dict) response headers
        """
        req = {'shutdown': {}}
        r = self.servers_action_post(server_id, json_data=req, success=202)
        return r.headers

    def get_server_console(self, server_id, console_type='vnc'):
        """
        :param server_id: integer (str or int)

        :param console_type: str (vnc, vnc-ws, vnc-wss, default: vnc)

        :returns: (dict) info to set a VNC connection to virtual server
        """
        ct = self.CONSOLE_TYPES
        assert console_type in ct, '%s not in %s' % (console_type, ct)
        req = {'console': {'type': console_type}}
        r = self.servers_action_post(server_id, json_data=req, success=200)
        return r.json['console']

    def reassign_server(self, server_id, project):
        req = {'reassign': {'project': project}}
        r = self.servers_action_post(server_id, json_data=req, success=200)
        return r.headers

    def get_server_stats(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (dict) auto-generated graphs of statistics (urls)
        """
        r = self.servers_stats_get(server_id)
        return r.json['stats']

    def get_server_diagnostics(self, server_id):
        """
        :param server_id: integer (str or int)

        :returns: (list)
        """
        r = self.servers_diagnostics_get(server_id)
        return r.json

    def get_server_status(self, server_id):
        """Deprecated - will be removed in version 0.15
        :returns: (current status, progress percentile if available)"""
        r = self.get_server_details(server_id)
        return r['status'], (r.get('progress', None) if (
            r['status'] in ('BUILD', )) else None)

    def wait_server_while(
            self, server_id,
            current_status='BUILD', delay=1, max_wait=100, wait_cb=None):
        """Wait for server WHILE its status is current_status
        :param server_id: integer (str or int)
        :param current_status: (str) BUILD|ACTIVE|STOPPED|DELETED|REBOOT
        :param delay: time interval between retries
        :max_wait: (int) timeout in secconds
        :param wait_cb: if set a progressbar is used to show progress
        :returns: (str) the new mode if succesfull, (bool) False if timed out
        """
        return wait(
            self.get_server_details, (server_id, ),
            lambda i: i['status'] != current_status,
            delay, max_wait, wait_cb)

    def wait_server_until(
            self, server_id,
            target_status='ACTIVE', delay=1, max_wait=100, wait_cb=None):
        """Wait for server WHILE its status is target_status
        :param server_id: integer (str or int)
        :param target_status: (str) BUILD|ACTIVE|STOPPED|DELETED|REBOOT
        :param delay: time interval between retries
        :max_wait: (int) timeout in secconds
        :param wait_cb: if set a progressbar is used to show progress
        :returns: (str) the new mode if succesfull, (bool) False if timed out
        """
        return wait(
            self.get_server_details, (server_id, ),
            lambda i: i['status'] == target_status,
            delay, max_wait, wait_cb)

    # Backwards compatibility - deprecated, will be replaced in 0.15
    wait_server = wait_server_while

    # Volume attachment extensions

    def get_volume_attachment(self, server_id, attachment_id):
        """
        :param server_id: (str)
        :param attachment_id: (str)
        :returns: (dict) details on the volume attachment
        """
        r = self.volume_attachment_get(server_id, attachment_id)
        return r.json['volumeAttachment']

    def list_volume_attachments(self, server_id):
        """
        :param server_id: (str)
        :returns: (list) all volume attachments for this server
        """
        r = self.volume_attachment_get(server_id)
        return r.json['volumeAttachments']

    def attach_volume(self, server_id, volume_id):
        """Attach volume on server
        :param server_id: (str)
        :volume_id: (str)
        :returns: (dict) information on attachment (contains volumeId)
        """
        r = self.volume_attachment_post(server_id, volume_id)
        return r.json['volumeAttachment']

    def delete_volume_attachment(self, server_id, attachment_id):
        """Delete a volume attachment. The volume will not be deleted.
        :param server_id: (str)
        :param attachment_id: (str)
        :returns: (dict) HTTP response headers
        """
        r = self.volume_attachment_delete(server_id, attachment_id)
        return r.headers

    def detach_volume(self, server_id, volume_id):
        """Remove volume attachment(s) for this volume and server
        This is not an atomic operation. Use "delete_volume_attachment" for an
        atomic operation with similar semantics.
        :param server_id: (str)
        :param volume_id: (str)
        :returns: (list) the deleted attachments
        """
        all_atts = self.list_volume_attachments(server_id)
        vstr = '%s' % volume_id
        attachments = [a for a in all_atts if ('%s' % a['volumeId']) == vstr]
        for attachment in attachments:
            self.delete_volume_attachment(server_id, attachment['id'])
        return attachments

# Backwards compatibility - will be removed in 0.15
CycladesClient = CycladesComputeClient


class CycladesNetworkClient(NetworkClient):
    """Cyclades Network API extentions"""

    network_types = (
        'CUSTOM', 'MAC_FILTERED', 'IP_LESS_ROUTED', 'PHYSICAL_VLAN')

    def list_networks(self, detail=None):
        path = path4url('networks', 'detail' if detail else '')
        r = self.get(path, success=200)
        return r.json['networks']

    def create_network(self, type, name=None, shared=None, project_id=None):
        req = dict(network=dict(type=type, admin_state_up=True))
        if name:
            req['network']['name'] = name
        if shared not in (None, ):
            req['network']['shared'] = bool(shared)
        if project_id is not None:
            req['network']['project'] = project_id
        r = self.networks_post(json_data=req, success=201)
        return r.json['network']

    def reassign_network(self, network_id, project_id, **kwargs):
        """POST endpoint_url/networks/<network_id>/action

        :returns: request response
        """
        path = path4url('networks', network_id, 'action')
        req = {'reassign': {'project': project_id}}
        r = self.post(path, json=req, success=200, **kwargs)
        return r.headers

    def list_ports(self, detail=None):
        path = path4url('ports', 'detail' if detail else '')
        r = self.get(path, success=200)
        return r.json['ports']

    def create_port(
            self, network_id,
            device_id=None, security_groups=None, name=None, fixed_ips=None):
        """
        :param fixed_ips: (list of dicts) [{"ip_address": IPv4}, ...]
        """
        port = dict(network_id=network_id)
        if device_id:
            port['device_id'] = device_id
        if security_groups:
            port['security_groups'] = security_groups
        if name:
            port['name'] = name
        if fixed_ips:
            for fixed_ip in fixed_ips or []:
                if 'ip_address' not in fixed_ip:
                    raise ValueError('Invalid fixed_ip [%s]' % fixed_ip)
            port['fixed_ips'] = fixed_ips
        r = self.ports_post(json_data=dict(port=port), success=201)
        return r.json['port']

    def create_floatingip(
            self,
            floating_network_id=None, floating_ip_address='', project_id=None):
        """
        :param floating_network_id: if not provided, it is assigned
            automatically by the service
        :param floating_ip_address: only if the IP is availabel in network pool
        :param project_id: specific project to get resource quotas from
        """
        floatingip = {}
        if floating_network_id:
            floatingip['floating_network_id'] = floating_network_id
        if floating_ip_address:
            floatingip['floating_ip_address'] = floating_ip_address
        if project_id is not None:
            floatingip['project'] = project_id
        r = self.floatingips_post(
            json_data=dict(floatingip=floatingip), success=200)
        return r.json['floatingip']

    def reassign_floating_ip(self, floating_network_id, project_id):
        """Change the project where this ip is charged"""
        path = path4url('floatingips', floating_network_id, 'action')
        json_data = dict(reassign=dict(project=project_id))
        self.post(path, json=json_data, success=200)


class CycladesBlockStorageClient(CycladesBlockStorageRestClient):
    """Cyclades Block Storage REST API Client"""

    def create_volume(
            self, size, display_name,
            server_id=None,
            display_description=None,
            snapshot_id=None,
            imageRef=None,
            volume_type=None,
            metadata=None,
            project=None):
        """:returns: (dict) new volumes' details"""
        r = self.volumes_post(
            size, display_name,
            server_id=server_id,
            display_description=display_description,
            snapshot_id=snapshot_id,
            imageRef=imageRef,
            volume_type=volume_type,
            metadata=metadata,
            project=project)
        return r.json['volume']

    def reassign_volume(self, volume_id, project):
        self.volumes_action_post(volume_id, {"reassign": {"project": project}})

    def create_snapshot(
            self, volume_id, display_name=None, display_description=None):
        """:returns: (dict) new snapshots' details"""
        return super(CycladesBlockStorageClient, self).create_snapshot(
            volume_id,
            display_name=display_name,
            display_description=display_description)
