#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Sören Schmidt <soeren.schmidt@suse.com>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: saptune_facts

short_description: Get saptune status as fact

version_added: "0.0.1"

description: 
        The module will make the result of C(saptune --format json status) available 
        as Ansible fact.

options:
    compliance_check:
        description:
            Defines if a compliance check shall be done.
        required: false
        default: true
        type: bool
  
requirements:
    - C(saptune) must support JSON output (>= 3.1)
     
author:
    - Sören Schmidt (soeren.schmidt@suse.com)
'''

EXAMPLES = r'''
# Simply get the facts
- name: Tune for SAP HANA
  saptune_facts:

# Get the facts, but skip compliance check
- name: Tune for SAP HANA
  saptune_facts:
    compliance_check: false

'''

RETURN = r'''
saptune:
    description: The result object of the last C(saptune --format json status).
    type: dict
    returned: always
    sample: '{
        "services": {
        "saptune": [
            "enabled",
            "active"
        ],
        "sapconf": [],
        "tuned": []
        },
        "systemd system state": "running",
        "tuning state": "compliant",
        "virtualization": "oracle",
        "configured version": "3",
        "package version": "3.1.3",
        "Solution enabled": [],
        "Notes enabled by Solution": [],
        "Solution applied": [],
        "Notes applied by Solution": [],
        "Notes enabled additionally": [
        "SAP_BOBJ"
        ],
        "Notes enabled": [
        "SAP_BOBJ"
        ],
        "Notes applied": [
        "SAP_BOBJ"
        ],
        "staging": {
        "staging enabled": false,
        "Notes staged": [],
        "Solutions staged": []
        }'
'''

import collections
import json
import subprocess
from typing import List, Tuple
from ansible.module_utils.basic import AnsibleModule


def execute(command: List[str], ignore_error: bool=False) -> None:
    """Executes the given command and returns stdout.
    If ignore_error is set, an exit code not 0 does not lead to a failure.
    Calls module.fail_json() in case of an error."""

    # Set some result entries.
    for entry, default in ('stdout', ''), ('stdout_lines', []), ('stderr', ''), ('stderr_lines', []):
        if entry not in result:
            result[entry] = default
        
    try:
        with subprocess.Popen(command,
                              stdout = subprocess.PIPE, 
                              stderr = subprocess.PIPE
                             ) as proc:
            stdout = proc.stdout.readlines()
            stderr = proc.stderr.readlines()
            stdout_str = '\n'.join([line.strip().decode('utf-8') for line in stdout])
            stderr_str = '\n'.join([line.strip().decode('utf-8') for line in stderr])
            if stdout:
                result['stdout'] = result['stdout'] + stdout_str 
                result['stdout_lines'].append(stdout)
            if stderr:
                result['stderr'] = result['stderr'] + stderr_str
                result['stderr_lines'].append(stderr)
            result['rc'] = proc.returncode
        if proc.returncode != 0 and not ignore_error:
            module.fail_json(msg=f'''Execution of \'{' '.join(command)}\' failed!''', **result)             
    except Exception as err:
        module.fail_json(msg=f'''Error executing \'{' '.join(command)}\': {err}''', **result)          
    return stdout_str
 
def run_module():
    
    # We need those objects in all functions.
    global module
    global result
    
    # Define module arguments/parameters.
    module_args = dict(
        compliance_check=dict(type='bool', required=False, default=True)
    )

    # Start to build up the result object.
    result = dict(
        changed = False,
    )
    
    # Instantiate the Ansible module.
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )
    
    # Get saptune status.
    command = ['saptune', '--format', 'json', 'status']
    if not module.params['compliance_check']:
        command.append('--non-compliance-check')
    output = execute(command, ignore_error=False)
    try: 
        status_output = json.loads(output)
    except json.decoder.JSONDecodeError:
        module.fail_json(msg='No or broken JSON output of \'saptune --format json status\'. Is saptune version to old (<3.1) or does not run as root?', **result)
    if not status_output['result']:
        module.fail_json(msg='\'saptune --format json status\' returned an empty result!', **result)
    
    # Return with the result.
    result['rc'] = 0
    result['ansible_facts'] = { 'saptune': status_output['result']}
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
    
