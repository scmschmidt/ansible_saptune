#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ansible module to configure saptune.

This module requires at least saptune 3.1 because it depends on the JSON output.

With this module is it possibe to:

    - apply or revert Notes and Solutions,
    - enable/disable and start/stop saptune.service,.
    - put sapconf and tuned out of the way

Currently this module does not handle overrides or extra Notes, but both can
be placed into the required folders by ansible.copy and this modul can trigger
a re-apply or refresh the tuning. 

Exitcodes:

    0   Everything went fine.
    1   

Ideas:
    - 
    - 

ToDo:
    - Imporve the execute function
    - Handle older saptune versions.

Changelog:
----------
10.09.2022      v0.1        - and so it begins...
"""

import collections
import json
import os
import subprocess
import sys
from typing import List, Dict, Tuple, Any


# CAN BE REMOVED AFTER DEVELOPMENT.
import pprint
import yaml


VERSION = 'v0.3'
AUTHOR = 'soeren.schmidt@suse.com'
LICENSE= ''


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


def exit_on_error(text: str, rc: int=1) -> None:
    print(text, file=sys.stderr)
    sys.exit(rc)

def execute(command: List[str]) -> str:
    """Calls the given command and returns stdout.
    In case of an error error_oin_exit() with 
    the stderr of the command is called."""

    output = []
    result = None
    try:
        with subprocess.Popen(command,
                              stdout = subprocess.PIPE, 
                              stderr = subprocess.PIPE
                             ) as proc:
            for line in proc.stdout.readlines():
                output.append((line.strip().decode('utf-8')))
            
    except Exception as err:
        exit_on_error(err)
       
    return '\n'.join(output)

def load_config() -> Dict[str, Any]:
    """Load config (in final module this will be handed over by Ansible)"""

    with open('./conf.yaml', 'r') as f:
        return yaml.safe_load(f)
        
def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Verifies if the configuration only has known attributes
    and if the data types are valid. Defaults are set.
    Returns the complete validated configuration or calls 
    error() in case of an error."""

    datatypes = {'apply': list,    
                 'force_reapply': bool,
                 'no_tuned':  bool, 
                 'no_sapconf':  bool, 
                 'enabled':  bool,
                 'started':  bool,
                 'keep_applied_if_stopped':  bool,
                 'ignore_non_compliant':  bool,
                 'ignore_degraded':  bool,
                 'staging_enabled':  bool }
    defaults = {'apply': [],
                'force_reapply': False,
                'no_tuned': True, 
                'no_sapconf': True,  
                'enabled': True, 
                'started': True, 
                'keep_applied_after_stop': False,
                'ignore_non_compliant': False,
                'ignore_degraded': False,
                'staging_enabled': False }

    # Check for unknown entries.
    unknown_entries = set(config.keys()) - set(datatypes.keys())
    if unknown_entries:
        exit_on_error(f'''Unknown configuration attributes: {', '.join(unknown_entries)}''') 

    # An empty apply list must be converted from None to an empty list.
    if config['apply'] is None:
        config['apply'] = []

    # Check data types.
    for entry, value in config.items():
        if type(value) != datatypes[entry]:
            exit_on_error(f'"{entry}" has datatype {type(value)}, but should be {datatypes[entry]}.')
    
    # Set defaults.
    for entry, value in defaults.items():
        if entry not in config.keys():
            config[entry] = value
                
    # Check if elements of 'apply' are valid strings.
    for elem in config['apply']:
        if not isinstance(elem, str):
            exit_on_error(f'"apply" must contain only strings, but "{elem}" has datatype {type(elem)}.') 
        
    return config
                
def get_notes_and_solutions() -> (List[str], List[str], Dict[str, List[str]]):
    """Calls 'saptune note list' and 'saptune solution list'
    to get a list of all present Notes and Solutions as 
    well as the Notes of each Solution.
    Calls exit_on_error() in case of problems."""

    result = json.loads(execute(['saptune', '--format', 'json', 'note', 'list']))
    if result['exit code'] != 0:
        exit_on_error('Could not retrieve Note list!') 
    existing_notes = [e['Note ID'] for e in result['result']['Notes available']]

    result = json.loads(execute(['saptune', '--format', 'json', 'solution', 'list']))
    if result['exit code'] != 0:
        exit_on_error('Could not retrieve Solution list!')
    existing_solutions = [e['Solution ID'] for e in result['result']['Solutions available']]
    solution_map = {e['Solution ID']: e['Note list'] for e in result['result']['Solutions available']}

    return existing_notes, existing_solutions, solution_map

def get_status(compliance_check=True) -> Dict[str, Any]:
    """Returns 'saptune status'.
    Calls exit_on_error() in case of problems."""
    
    command = ['saptune', '--format', 'json', 'status']
    if not compliance_check:
        command.append('--non-compliance-check')
    output = execute(command)
    try: 
        result = json.loads(output)
    except json.decoder.JSONDecodeError:
        exit_on_error('No or broken JSON output of "saptune --format json status". Is saptune version to old (<3.1) or does not run as root?')
    if not result['result']:
        exit_on_error('"saptune --format json status" returned an empty result!')
    
    return result['result']
 
def set_staging(is_value: bool, should_value: bool) -> List[List[str]]:
    """Returns the commands to set the staging to the desired state,
    Calls exit_on_error() in case of problems."""

    if is_value == should_value:
        return []
    if should_value:
        return [['saptune', 'staging', 'enable']]
    else:
        return [['saptune', 'staging', 'disable']]

def set_service(service: str, current_state: str, target_state: str) -> List[List[str]]:
    """Returns the commands to get the given systemd service to
    its desired state.
    Calls exit_on_error() in case of problems."""

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
    and the commands to achieve it. Both are returned. In case of an
    error the function exit_on_error() gets called.
    
    No optimizations are done do remove unnecessary applies or reverts.
    The code become to complex to calulate saptune behavior. It is 
    too risky to introduce bugs just because some users might create
    "interresting" apply lists. Also changes in saptune requires  
    adaptation here and in the worst case introduces version switches.
       
    Nevertheless we track Note apply and removal to calculate the 
    effective Note list as well we check if all Notes of a Solution
    have been removed to reset the effective Solution. Saptune will
    do the same."""
    
    effective_notes = OrderedSet()
    effective_solution = None
    commands = [['saptune', 'revert', 'all']] if force_reapply else []
    effective_solution_notes = None
 
    # Walk through the apply list.
    solution = None
    for entry in apply_list:

        # A Solution may not have a minus operator.
        if entry[0:2] == '-@':
            exit_on_error(f'Solutions cannot have a minus operator: "{entry}"')
        
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
                exit_on_error(f'Solution "{entry}" is unknown!"')
            if effective_solution:
                exit_on_error(f'Only one Solution is allowed!')
            effective_solution = entry
            effective_solution_notes = OrderedSet(solution_map[entry]) 
            effective_notes.update(effective_solution_notes)
            commands.append(['saptune', 'solution', 'apply', entry])
        else:   # Note
            if entry not in existing_notes:
                exit_on_error(f'Note "{entry}" is unknown!"')
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

 
def main():

    command_list = []

    # Load config.
    config = load_config()

    # Validate config and set defaults.
    config = validate_config(config)

    # Call status to collect the current settings.
    status = get_status(compliance_check=False)

    # Set staging.
    command_list.extend(set_staging(config['staging_enabled'], 
                                   status['staging']['staging enabled']))

    # Take care of tuneD. 
    if config['no_tuned']:
        if status['services']['tuned']: # empty list, if not installed.
            for is_value, should_value in [(status['services']['tuned'][0], 'disabled'), 
                                            (status['services']['tuned'][1], 'inactive')]:
                command_list.extend(set_service('tuned.service', is_value, should_value))
    
    # Take care of sapconf. 
    if config['no_sapconf']:
        if status['services']['sapconf']: # empty list, if not installed.
            for is_value, should_value in [(status['services']['sapconf'][0], 'disabled'), 
                                            (status['services']['sapconf'][1], 'inactive')]:
                command_list.extend(set_service('sapconf.service', is_value, should_value))
        
    # Take care of saptune.service (in regards to enable/disable only).
    should_value = 'enabled' if  config['enabled'] else 'disabled'   
    command_list.extend(set_service('saptune.service', 
                                    status['services']['saptune'][0], 
                                    should_value))
            
    # If keep_applied_if_stopped is set to true, we need to
    # stop saptune.service now if this is the desired state,
    # otherwise stopping it later would remove the tuning.
    saptune_stop_handled = False
    if config['keep_applied_if_stopped']:
        if not config['started']:
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
                                  config['apply'],
                                  status['Notes applied'],
                                  applied_solution,
                                  force_reapply=config['force_reapply'])) 
    
    # Handle saptune.servie start/stop if not done earlier.
    if not saptune_stop_handled:
        should_value = 'active' if  config['started'] else 'inactive'   
        command_list.extend(set_service('saptune.service', 
                                        status['services']['saptune'][1], 
                                        should_value))
        
    # Depending on check_mode we return the commands or execute them.
    # if check_mode --> return command list and exit here!
    for command in command_list:
        print(' '.join(command))
    #   output = execute(command)   # WHAT TO DO WITH THE OUTPUT?

    # Calling status again and do final checks.
    if not config['ignore_non_compliant'] or not config['ignore_degraded']:

        # Get status again, if commands had been executed.
        if command_list:
            status = get_status(compliance_check=True)
                
        # A non compliant tuning is considered an error.
        if not config['ignore_non_compliant']:
            if status['tuning state'] == 'not compliant':
                exit_on_error('Tuning is non-compliant!')
        
        # A degraded systemd system state is considered an error.
        if not config['ignore_degraded']:
            if status['systemd system state'] == 'degraded':
                exit_on_error('Systemd system state is degraded!')

    # Bye.
    sys.exit(0)




    # # Figure out what will happen with the service first, because
    # # this has implications for implementing the configuration.
    # req_start, req_stop, req_enabled, req_disabled = service_action(config, status)

    # # If we have a 'configuration', build the Note and Solution lists.
    # if 'configuration' in config:

    #     solution_wanted, notes_wanted, actions = calculate_configuration(config['configuration'])

    #     solution_enabled = status['Solution enabled'][0] if len(status['Solution enabled']) > 1 else ''
    #     solution_applied = status['Solution applied'][0]['Solution ID'] if len(status['Solution applied']) > 1 else ''
    #     notes_enabled = ' '.join(status['Notes enabled'])
    #     notes_applied = ' '.join(status['Notes applied'])
    #     notes_wanted = ' '.join(notes_wanted)
    #     act = False     # We assume, that we have to do nothing.

    #     # We have to act, if we have
    #     # - a difference between the enabled and applied Solution or
    #     # - a differences between enabled and applied Notes
    #     # and we don't start or stop the saptune service.   
    #     # The reason is, that we'll next only take enabled Solution and Notes
    #     # into consideration. After a start/stop of the service, the applied ones
    #     # should follow the enabled ones.
    #     if ((solution_enabled != solution_applied) or (notes_enabled != notes_applied)) and (not req_start or not req_stop):
    #         act = True

    #     # We have to act, if we have
    #     # - the wanted Solution is not the enabled one, 
    #     # - the wanted Notes are not the enabled ones.
    #     if  (solution_enabled != solution_wanted) or (notes_enabled != notes_wanted):
    #         act = True

    #     # Let's act!    ADD THE NEW REFRESH COMMAND
    #     if act: 
    #         execute(['saptune', 'revert', 'all'])
    #         for action in actions:
    #             execute(action)    


    # # Deal with saptune service.
    # if req_start:
    #     execute(['systemctl', 'start', 'saptune.service'])
    # if req_stop:
    #     execute(['systemctl', 'stop', 'saptune.service'])
    # if req_enabled:
    #     execute(['systemctl', 'enable', 'saptune.service'])
    # if req_disabled:
    #     execute(['systemctl', 'disable', 'saptune.service'])

    # # Get status again to see if we are satified.
    # status = get_status()

    # # Check compliance.
    # if status['tuning state'] == 'not compliant' and not config['ignore_non-compliant']:
    #     exit_on_error(execute(['saptune', 'note', 'verify', '--show-non-compliant']))

    # # Check systemd state.
    # if status['systemd system state'] == 'degraded' and not config['ignore_degraded']:
    #     exit_on_error('Systemd state is degraded!')


if __name__ == '__main__':
    main()



 
