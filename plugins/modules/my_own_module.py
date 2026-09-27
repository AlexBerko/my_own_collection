#!/usr/bin/python

# Copyright: (c) 2018, Terry Jones <terry.jones@example.org>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: my_file

short_description: Creates a text file with specified content on the remote host.

version_added: "1.0.0"

description:
    - Creates a text file at the given path with the given content.
    - All missing directories in the path are created automatically.
    - The module is idempotent: if the file already exists with the same content, no changes are made.
    - Supports check mode (C(--check)).

options:
    path:
        description:
            - Full path to the file that should be created.
            - Tilde (C(~)) is expanded and the path is converted to an absolute one.
            - If the path points to an existing directory, the module fails.
        required: true
        type: path
    content:
        description:
            - Content to write to the file.
            - If the file exists and its content already matches, no changes are made.
        required: true
        type: str

author:
    - Berko Alex (@AlexBerko)
'''

EXAMPLES = r'''
# Create a file with simple content
- name: Create a text file
  my_file:
    path: /tmp/hello.txt
    content: "Hello, world!\n"

# Create a file with nested directories (they will be created automatically)
- name: Create a file in a nested directory
  my_file:
    path: /tmp/app/config/settings.txt
    content: "debug=true\n"

# Use with a variable
- name: Write rendered content to a file
  my_file:
    path: "{{ ansible_env.HOME }}/.myapp/config.txt"
    content: "{{ my_config_content }}"

# Check mode: report what would change without touching the file
- name: Check what would change
  my_file:
    path: /etc/myapp/config.txt
    content: "new content"
  check_mode: true
'''

RETURN = r'''
path:
    description: Absolute path to the file that was created or checked.
    type: str
    returned: always
    sample: '/tmp/hello.txt'
changed:
    description: Whether the file was created or its content was modified.
    type: bool
    returned: always
    sample: true
'''

from ansible.module_utils.basic import AnsibleModule

import os


def run_module():
    # define available arguments/parameters a user can pass to the module
    module_args = dict(
        path=dict(type='str', required=True),
        content=dict(type='str', required=True)
    )

    # seed the result dict in the object
    # we primarily care about changed and state
    # changed is if this module effectively modified the target
    # state will include any data that you want your module to pass back
    # for consumption, for example, in a subsequent task
    result = dict(
        changed=False,
        path=''
    )

    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    path            = os.path.abspath(os.path.expanduser(module.params['path']))
    content         = module.params['content']
    result['path']  = path


    # Check if module have changes (--check)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                old_content = f.read()
        except OSError as e:
            module.fail_json(msg="Cannot read file %s: %s" % (path, e))
        result['changed'] = (old_content != content)
    else:
        result['changed'] = True

    # Exit in --check mode
    if module.check_mode:
        module.exit_json(**result)
        return


    # Check if path is directory
    if os.path.isdir(path):
        module.fail_json(msg=f"Provided path is directory: {path}")


    # Create all directories on path
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            module.fail_json(msg="Cannot create directory %s: %s" % (directory, e))

    # Write file
    try:
        with open(path, 'w') as f:
            f.write(content)
    except OSError as e:
        module.fail_json(msg="Cannot write file %s: %s" % (path, e))


    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()