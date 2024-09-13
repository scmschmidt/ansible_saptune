#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Sören Schmidt <soeren.schmidt@suse.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: saptune

short_description: Handles saptune.

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This is my longer description explaining my test module.
             mention check_mode support

options:
    name:
        description: This is the message to send to the test module.
        required: true
        type: str
    new:
        description:
            - Control to demo if the result of this module is changed or not.
            - Parameter description can be a list as well.
        required: false
        type: bool
# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
# extends_documentation_fragment:
#     - my_namespace.my_collection.my_doc_fragment_name

author:
    - Your Name (@yourGitHubHandle)
'''

EXAMPLES = r'''
# Pass in a message
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_namespace.my_collection.my_test:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_namespace.my_collection.my_test:
    name: fail me
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
original_message:
    description: The original name param that was passed in.
    type: str
    returned: always
    sample: 'hello world'
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample: 'goodbye'
'''

import collections
import json
import os
import subprocess
from typing import List, Dict, Tuple, Any
from ansible.module_utils.basic import AnsibleModule


class OrderedSet():
    """Limited implementation of an ordered set."""
      
    def __init__(self, iterable=[]):
        self.ordered_set = collections.OrderedDict()
        self.update(iterable)
      
    def update(self, iterable=[]):
        for elem in iterable:
            self.add(elem)

    def add(self, elem):
        self.ordered_set[elem] = None

    def discard(self, elem):
        self.ordered_set.pop(elem, None)  
        
    def intersection(self, iterable=[]):
        intersection = OrderedSet()
        for elem in iterable:
            if elem in self.ordered_set.keys():
                intersection.add(elem)
        return intersection
    
    def __iter__(self):
        yield from self.ordered_set.keys()
    
    def __repr__(self):
        return self.__str__

    def __str__(self):
        return f'''{{{', '.join([repr(x) for x in self.ordered_set.keys()])}}}'''

def execute(command: List[str]) -> None:
    """Executes the given command.
    Calls module.fail_json() in case of an error."""

    try:
        with subprocess.Popen(command,
                              stdout = subprocess.PIPE, 
                              stderr = subprocess.PIPE
                             ) as proc:
            stdout = proc.stdout.readlines()
            stderr = proc.stderr.readlines()
            result['stdout'] = '\n'.join([line.strip().decode('utf-8') for line in stdout])
            result['stdout_lines'] = stdout
            result['stderr'] = '\n'.join([line.strip().decode('utf-8') for line in stderr])
            result['stderr_lines'] = stderr
            result['rc'] = proc.returncode
        if proc.returncode != 0:
            module.fail_json(msg=f'''Execution of \'{' '.join(command)}\' failed!''', **result)             
    except Exception as err:
        module.fail_json(msg=f'''Error executing \'{' '.join(command)}\': {err}''', **result)          
    return

def get_notes_and_solutions() -> (List[str], List[str], Dict[str, List[str]]):
    """Calls 'saptune note list' and 'saptune solution list'
    to get a list of all present Notes and Solutions as 
    well as the Notes of each Solution.
    Calls module.fail_json() in case of an error."""

    result = json.loads(execute(['saptune', '--format', 'json', 'note', 'list']))
    if result['exit code'] != 0:
        module.fail_json(msg='Could not retrieve Note list!', **result)
    existing_notes = [e['Note ID'] for e in result['result']['Notes available']]

    result = json.loads(execute(['saptune', '--format', 'json', 'solution', 'list']))
    if result['exit code'] != 0:
        module.fail_json(msg='Could not retrieve Solution list!', **result)
    existing_solutions = [e['Solution ID'] for e in result['result']['Solutions available']]
    solution_map = {e['Solution ID']: e['Note list'] for e in result['result']['Solutions available']}

    return existing_notes, existing_solutions, solution_map

def get_status(compliance_check=True) -> Dict[str, Any]:
    """Returns 'saptune status'.
    Calls module.fail_json() in case of an error."""
    
    command = ['saptune', '--format', 'json', 'status']
    if not compliance_check:
        command.append('--non-compliance-check')
    output = execute(command)   #TODO: WE NEED TO TELL EXECUTE TO IGNORE THE EXIT CODE IN THIS CASE!!
    try: 
        json_output = json.loads(output)
    except json.decoder.JSONDecodeError:
        module.fail_json(msg='No or broken JSON output of \'saptune --format json status\'. Is saptune version to old (<3.1) or does not run as root?', **result)
    if not json_output['result']:
        module.fail_json(msg='\'saptune --format json status\' returned an empty result!', **result)
    
    return json_output['result']
 
def set_staging(is_value: bool, should_value: bool) -> List[List[str]]:
    """Returns the commands to set the staging to the desired state."""

    if is_value == should_value:
        return []
    if should_value:
        return [['saptune', 'staging', 'enable']]
    else:
        return [['saptune', 'staging', 'disable']]

def set_service(service: str, current_state: str, target_state: str) -> List[List[str]]:
    """Returns the commands to get the given systemd service to
    its desired state."""

    if current_state == target_state:
        return []
    commands = []
    if current_state == 'failed':
        commands.append(['systemctl', 'reset-failed', service])
    if target_state == 'enabled':
        commands.append(['systemctl', 'enable', service])
    if target_state == 'disabled':
        commands.append(['systemctl', 'disable', service])
    if target_state == 'active':
        commands.append(['systemctl', 'start', service])
    if target_state == 'inactive':
        commands.append(['systemctl', 'stop', service])
    
    return commands

def set_apply(existing_notes: List[str],
              existing_solutions: List[str],
              solution_map: Dict[str, List[str]],
              apply_list: List[str],
              current_applied_notes: List[str],
              current_applied_solution: str,
              force_reapply: bool) -> List[List[str]]:
    """Takes the apply list and calculates the effective Notes
    (how "applied Notes" should look like) and the effective
    Solution (what "applied Solution" should list) as well as
    the commands to achieve it.
    
    If the calculated Notes and Solution does not differ
    from the current ones, an empty command list is returned
    since nothing needs to be done.
    
    If there is a difference or `force_reapply` is set, the 
    calculated commands are returned.

    In case of an error module.fail_json() gets called.
    
    Important:
    No optimizations are done to remove unnecessary applies or reverts.
    Some users may create "interesting" apply lists, but adding complex
    code to mimic saptune behavior for such rare events is too risky. 
    It can introduce bugs and requires adaptation if saptune changes 
    its behavior. In the worst case a version switch might become necessary.
       
    Nevertheless we track Note apply and removal to calculate the 
    effective Note list as well we check if all Notes of a Solution
    have been removed to reset the effective Solution. Saptune will
    do the same."""
    
    effective_notes = OrderedSet()
    effective_solution = None
    commands = [['saptune', 'revert', 'all']]
    effective_solution_notes = None
 
    # Walk through the apply list.
    solution = None
    for entry in apply_list:

        # A Solution may not have a minus operator.
        if entry[0:2] == '-@':
            module.fail_json(msg=f'Solutions cannot have a minus operator: \'{entry}\'', **result)
        
        # Set operator and remove it from entry.
        if entry[0] == '-':
            operator = '-'
            entry = entry[1:]
        else:
            operator = '+'

        # Process the entry.
        if entry[0] == '@':    # Solution
            entry = entry[1:]
            if entry not in existing_solutions:
                module.fail_json(msg=f'Solution \'{entry}\' is unknown!', **result)
            if effective_solution:
                module.fail_json(msg=f'Only one Solution is allowed!', **result)
            effective_solution = entry
            effective_solution_notes = OrderedSet(solution_map[entry]) 
            effective_notes.update(effective_solution_notes)
            commands.append(['saptune', 'solution', 'apply', entry])
        else:   # Note
            if entry not in existing_notes:
                module.fail_json(msg=f'Note \'{entry}\' is unknown!', **result)
            if operator == '+':
                if entry not in effective_notes: 
                    effective_notes.add(entry)
                    commands.append(['saptune', 'note', 'apply', entry])
            else:
                if entry in effective_notes:
                    effective_notes.discard(entry)
                    commands.append(['saptune', 'note', 'revert', entry])
                
        # If the Notes of a Solution all have been removed,
        # the Solution is removed.
        if effective_solution:
            if effective_notes.intersection(effective_solution_notes):
                effective_solution = None
                effective_solution_notes = None
                
    # If our calculated configuration is already applied, then no
    # commands need to be executed except force_reapply is set.
    if not force_reapply:
        if effective_solution == current_applied_solution and current_applied_notes == list(effective_notes):
            return []   
        
    return commands

def run_module():
    
    # We need those objects in all functions.
    global module
    global result
    
    # Define module arguments/parameters.
    module_args = dict(
        apply=dict(type='list', elements='str', required=False, default=[]),
        force_reapply=dict(type='bool', required=False, default=False),
        no_tuned=dict(type='bool', required=False, default=True),
        no_sapconf=dict(type='bool', required=False, default=True),
        enabled=dict(type='bool', required=False, default=True),
        started=dict(type='bool', required=False, default=True),
        keep_applied_if_stopped=dict(type='bool', required=False, default=False),
        ignore_non_compliant=dict(type='bool', required=False, default=False),
        ignore_degraded=dict(type='bool', required=False, default=True),
        staging_enabled=dict(type='bool', required=False, default=False)   
    )

    # Start to build up the result object.
    result = dict(
        changed = False,
        rc = None,
        commands = []
    )

    # Instantiate the Ansible module.
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    # The command list to get saptune to the desired state.
    command_list = []

    # Call status to collect the current settings.
    status = get_status(compliance_check=False)

    # Set staging.
    command_list.extend(set_staging(module.params['staging_enabled'], 
                                    status['staging']['staging enabled']))

    # Take care of tuneD. 
    if module.params['no_tuned']:
        if status['services']['tuned']: # empty list, if not installed.
            for is_value, should_value in [(status['services']['tuned'][0], 'disabled'), 
                                            (status['services']['tuned'][1], 'inactive')]:
                command_list.extend(set_service('tuned.service', is_value, should_value))
    
    # Take care of sapconf. 
    if module.params['no_sapconf']:
        if status['services']['sapconf']: # empty list, if not installed.
            for is_value, should_value in [(status['services']['sapconf'][0], 'disabled'), 
                                            (status['services']['sapconf'][1], 'inactive')]:
                command_list.extend(set_service('sapconf.service', is_value, should_value))
        
    # Take care of saptune.service (in regards to enable/disable only).
    should_value = 'enabled' if  module.params['enabled'] else 'disabled'   
    command_list.extend(set_service('saptune.service', 
                                    status['services']['saptune'][0], 
                                    should_value))
       
    # If keep_applied_if_stopped is set to true, we need to
    # stop saptune.service now if this is the desired state,
    # otherwise stopping it later would remove the tuning.
    saptune_stop_handled = False
    if module.params['keep_applied_if_stopped']:
        if not module.params['started']:
            command_list.extend(set_service('saptune.service', 
                                           status['services']['saptune'][1], 
                                           'inactive'))
            saptune_stop_handled = True
        
    # Generate the commands depending on the apply list.
    existing_notes, existing_solutions, solution_map = get_notes_and_solutions()
    applied_solution = status['Solution applied'][0] if status['Solution applied'] else None
    command_list.extend(set_apply(existing_notes,
                                  existing_solutions,
                                  solution_map,
                                  module.params['apply'],
                                  status['Notes applied'],
                                  applied_solution,
                                  force_reapply=module.params['force_reapply']))
    result['commands'] = [' '.join(command) for command in command_list]
    
    # Handle saptune.service start/stop if not done earlier.
    if not saptune_stop_handled:
        should_value = 'active' if  module.params['started'] else 'inactive'   
        command_list.extend(set_service('saptune.service', 
                                        status['services']['saptune'][1], 
                                        should_value))
        
    # With check_mode we just return the commands.
    #module.check_mode = True
    if module.check_mode:
        result['msg'] = 'Do nothing because check_mode is set.'
        module.exit_json(**result)
        
    # If we have something to execute, we do.
    if command_list:
        for command in command_list:
            execute(command)    # TODO: OUTPUT HANDLING
        result['changed'] = True
    else:
        result['msg'] = 'Nothing to do.'
        module.exit_json(**result)
        



    # Calling status again and do final checks.
    if not module.params['ignore_non_compliant'] or not module.params['ignore_degraded']:

        # Get status again, if commands had been executed.
        if command_list:
            status = get_status(compliance_check=True)
                
        # A non compliant tuning is considered an error.
        if not module.params['ignore_non_compliant']:
            if status['tuning state'] == 'not compliant':
                module.fail_json(msg='Tuning is non-compliant!', **result)
        
        # A degraded systemd system state is considered an error.
        if not module.params['ignore_degraded']:
            if status['systemd system state'] == 'degraded':
                module.fail_json(msg='Systemd system state is degraded!', **result)






        

    # in the event of a successful module execution, you will want to
    # simple AnsibleModule.exit_json(), passing the key/value results
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
    