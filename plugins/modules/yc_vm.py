#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: yc_vm
short_description: Create and manage VMs in Yandex Cloud
description:
  - This module creates, updates, and deletes virtual machines in Yandex Cloud.
  - Requires the yandex-cloud python-sdk to be installed.
  - Requires environment variable C(YC_IAM_TOKEN) with a valid IAM token.
  - Tested with Rocky Linux 10 (family C(rocky-10)).
version_added: "1.0.0"
author:
  - Berko Alex
options:
  folder_id:
    description: Yandex Cloud folder ID where the VM will be created.
    required: true
    type: str
  name:
    description: Name of the virtual machine.
    required: true
    type: str
  zone:
    description: Availability zone for the VM.
    default: ru-central1-a
    choices: ['ru-central1-a', 'ru-central1-b', 'ru-central1-d', 'ru-central1-e']
    type: str
  subnet_id:
    description: Subnet ID where the VM will be attached.
    required: true
    type: str
  image_id:
    description:
      - Boot disk image ID.
      - If not specified, C(image_family) is used to resolve the latest image.
    type: str
  image_family:
    description:
      - Image family to use.
      - Default is C(rocky-10) (Rocky Linux 10).
    default: rocky-10
    type: str
  cores:
    description: Number of vCPUs.
    default: 2
    type: int
  memory:
    description: Amount of RAM in GB.
    default: 2
    type: int
  core_fraction:
    description: Baseline CPU performance level.
    default: 20
    choices: [20, 50, 100]
    type: int
  disk_size:
    description: Boot disk size in GB.
    default: 10
    type: int
  disk_type:
    description: Boot disk type.
    default: network-hdd
    choices: ['network-hdd', 'network-ssd', 'network-ssd-nonreplicated']
    type: str
  platform_id:
    description: Platform ID for the VM.
    default: standard-v3
    type: str
  assign_public_ip:
    description: Assign a public IP address.
    default: true
    type: bool
  preemptible:
    description:
      - Make the VM preemptible.
      - Preemptible VMs are cheaper but can be stopped by the cloud at any
        moment and live at most 24 hours.
    default: true
    type: bool
  username:
    description: Username for the VM (created via cloud-init).
    default: alex
    type: str
  ssh_key:
    description: Public SSH key content for authentication.
    required: true
    type: str
  state:
    description: Desired state of the VM.
    default: present
    choices: ['present', 'absent']
    type: str
'''

EXAMPLES = r'''
- name: Create a preemptible Rocky Linux 10 VM
  yc_vm:
    folder_id: "b1gxxxxxxxxxxxxxxxx"
    name: "berko-rocky-vm"
    zone: "ru-central1-a"
    subnet_id: "e9bxxxxxxxxxxxxxxxx"
    image_family: "rocky-10"
    cores: 2
    memory: 4
    disk_size: 20
    disk_type: "network-ssd"
    preemptible: true
    username: "alex"
    ssh_key: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"
    state: present

- name: Create a regular (non-preemptible) VM
  yc_vm:
    folder_id: "b1gxxxxxxxxxxxxxxxx"
    name: "berko-prod-vm"
    subnet_id: "e9bxxxxxxxxxxxxxxxx"
    preemptible: false
    ssh_key: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"

- name: Delete the VM
  yc_vm:
    folder_id: "b1gxxxxxxxxxxxxxxxx"
    name: "berko-rocky-vm"
    subnet_id: "e9bxxxxxxxxxxxxxxxx"
    ssh_key: "{{ lookup('file', '~/.ssh/id_rsa.pub') }}"
    state: absent
'''

RETURN = r'''
vm:
  description: Created or existing VM information.
  returned: on success
  type: dict
  sample:
    id: "epdxxxxxxxxxxxxxxxx"
    name: "berko-rocky-vm"
    zone: "ru-central1-a"
    status: "RUNNING"
    preemptible: true
    internal_ip: "10.0.0.5"
    external_ip: "158.160.x.x"
'''

from ansible.module_utils.basic import AnsibleModule
import os

try:
    import yandexcloud
    from yandex.cloud.compute.v1.instance_service_pb2 import (
        CreateInstanceRequest,
        DeleteInstanceRequest,
        ListInstancesRequest,
    )
    from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
    from yandex.cloud.compute.v1.instance_pb2 import Instance
    from yandex.cloud.compute.v1.image_service_pb2 import GetImageLatestByFamilyRequest
    from yandex.cloud.compute.v1.image_service_pb2_grpc import ImageServiceStub
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False


class YandexCloudVM:
    def __init__(self, module, token):
        self.module = module
        self.params = module.params
        self.sdk = yandexcloud.SDK(iam_token=token)
        self.instance_service = self.sdk.client(InstanceServiceStub)
        self.image_service = self.sdk.client(ImageServiceStub)

    # ------------------------------------------------------------------ #
    # Lookup helpers
    # ------------------------------------------------------------------ #
    def get_vm(self):
        """Return existing VM instance by name or None."""
        try:
            request = ListInstancesRequest(folder_id=self.params['folder_id'])
            response = self.instance_service.List(request)
            for instance in response.instances:
                if instance.name == self.params['name']:
                    return instance
            return None
        except Exception as e:
            self.module.fail_json(msg=f"Failed to list VMs: {str(e)}")

    def _resolve_image_family(self):
        """Resolve the latest image ID from the specified family."""
        try:
            request = GetImageLatestByFamilyRequest(
                folder_id='standard-images',
                family=self.params['image_family'],
            )
            response = self.image_service.GetLatestByFamily(request)
            return response.id
        except Exception as e:
            self.module.fail_json(
                msg=f"Failed to resolve image family '{self.params['image_family']}': {str(e)}"
            )

    # ------------------------------------------------------------------ #
    # Cloud-init
    # ------------------------------------------------------------------ #
    def _build_user_data(self):
        """
        Build cloud-init config for Rocky Linux (RHEL family).
        Uses 'wheel' group (RHEL admin group) instead of 'sudo'.
        """
        return f"""#cloud-config
users:
  - name: {self.params['username']}
    groups: wheel
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    lock_passwd: false
    ssh_authorized_keys:
      - {self.params['ssh_key']}
ssh_pwauth: false
disable_root: false
"""

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    def create_vm(self):
        """Create a new VM instance."""
        try:
            # Resolve image: explicit image_id wins, otherwise use family
            image_id = self.params.get('image_id') or self._resolve_image_family()

            user_data = self._build_user_data()

            network_interface = {
                'subnet_id': self.params['subnet_id'],
            }
            if self.params['assign_public_ip']:
                network_interface['primary_v4_address_spec'] = {
                    'one_to_one_nat_spec': {'ip_version': 'IPV4'}
                }

            request = CreateInstanceRequest(
                folder_id=self.params['folder_id'],
                name=self.params['name'],
                zone_id=self.params['zone'],
                platform_id=self.params['platform_id'],
                resources_spec={
                    'cores': self.params['cores'],
                    'memory': self.params['memory'] * 1024 * 1024 * 1024,
                    'core_fraction': self.params['core_fraction'],
                },
                boot_disk_spec={
                    'disk_spec': {
                        'image_id': image_id,
                        'size': self.params['disk_size'] * 1024 * 1024 * 1024,
                        'type_id': self.params['disk_type'],
                    }
                },
                network_interface_specs=[network_interface],
                metadata={
                    'user-data': user_data,
                    'ssh-keys': f"{self.params['username']}:{self.params['ssh_key']}",
                },
                scheduling_policy={
                    'preemptible': self.params['preemptible'],
                },
            )

            operation = self.instance_service.Create(request)
            self.sdk.wait_operation_and_get_result(operation)
            return self.get_vm()
        except Exception as e:
            self.module.fail_json(msg=f"Failed to create VM: {str(e)}")

    def delete_vm(self):
        """Delete a VM instance. Returns True if deleted, False if absent."""
        try:
            vm = self.get_vm()
            if not vm:
                return False
            request = DeleteInstanceRequest(instance_id=vm.id)
            operation = self.instance_service.Delete(request)
            self.sdk.wait_operation_and_get_result(operation)
            return True
        except Exception as e:
            self.module.fail_json(msg=f"Failed to delete VM: {str(e)}")

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #
    def format_vm_info(self, vm):
        if not vm:
            return None
        result = {
            'id': vm.id,
            'name': vm.name,
            'zone': vm.zone_id,
            'status': Instance.Status.Name(vm.status),
            'preemptible': vm.scheduling_policy.preemptible,
        }
        for iface in vm.network_interfaces:
            result['internal_ip'] = iface.primary_v4_address.address
            if iface.primary_v4_address.one_to_one_nat:
                result['external_ip'] = iface.primary_v4_address.one_to_one_nat.address
        return result


# ---------------------------------------------------------------------- #
# Entry point
# ---------------------------------------------------------------------- #
def main():
    module_args = dict(
        folder_id=dict(type='str', required=True),
        name=dict(type='str', required=True),
        zone=dict(type='str', default='ru-central1-a',
                  choices=['ru-central1-a', 'ru-central1-b', 'ru-central1-d', 'ru-central1-e']),
        subnet_id=dict(type='str', required=True),
        image_id=dict(type='str'),
        image_family=dict(type='str', default='rocky-10'),
        cores=dict(type='int', default=2),
        memory=dict(type='int', default=2),
        core_fraction=dict(type='int', default=20, choices=[20, 50, 100]),
        disk_size=dict(type='int', default=10),
        disk_type=dict(type='str', default='network-hdd',
                       choices=['network-hdd', 'network-ssd', 'network-ssd-nonreplicated']),
        platform_id=dict(type='str', default='standard-v3'),
        assign_public_ip=dict(type='bool', default=True),
        preemptible=dict(type='bool', default=True),
        username=dict(type='str', default='alex'),
        ssh_key=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
    )

    token = os.environ.get('YC_IAM_TOKEN')
    if not token:
        module.fail_json(msg="Environment variable YC_IAM_TOKEN is not set")

    if not SDK_AVAILABLE:
        module.fail_json(
            msg="The yandex-cloud python-sdk is not installed. "
                "Install with: pip install git+https://github.com/yandex-cloud/python-sdk"
        )

    yc = YandexCloudVM(module, token)
    result = {'changed': False}

    try:
        if module.params['state'] == 'absent':
            deleted = yc.delete_vm()
            result['changed'] = deleted
            result['msg'] = (
                f"VM {module.params['name']} deleted" if deleted
                else f"VM {module.params['name']} does not exist"
            )
        else:
            existing = yc.get_vm()
            if existing:
                result['vm'] = yc.format_vm_info(existing)
                result['changed'] = False
                result['msg'] = f"VM {module.params['name']} already exists"
            else:
                if module.check_mode:
                    result['changed'] = True
                    result['msg'] = f"VM {module.params['name']} would be created"
                else:
                    vm = yc.create_vm()
                    result['vm'] = yc.format_vm_info(vm)
                    result['changed'] = True
                    result['msg'] = f"VM {module.params['name']} created"
    except Exception as e:
        module.fail_json(msg=str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()