#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import collections
import os
import sys
import yaml
from typing import List, Dict, Tuple

class OrderedSet():
    """Limited implementation of an ordered set,"""
      
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

def error(text: str):
    print(text, file=sys.stderr)
    sys.exit(1)

def validate_config(config: Dict) -> Dict:
    """Verifies if the configuration only has known attributes
    and if the data types are valid. Defaults are set.
    Returns the complete validated configuration or calls 
    error() in case of an error.
    """

    datatypes = {'apply': list,    
                 'force_reapply': bool,
                 'no_tuned':  bool, 
                 'no_sapconf':  bool, 
                 'enabled':  bool,
                 'started':  bool,
                 'keep_applied_after_stop':  bool,
                 'ignore_non_compliant':  bool,
                 'ignore_degraded':  bool,
                 'staging':  bool }
    defaults = {'apply': [],
                'force_reapply': False,
                'no_tuned': True, 
                'no_sapconf': True,  
                'enabled': True, 
                'started': True, 
                'keep_applied_after_stop': False,
                'ignore_non_compliant': False,
                'ignore_degraded': False,
                'staging': False }

    # Check for unknown entries.
    unknown_entries = set(config.keys()) - set(datatypes.keys())
    if unknown_entries:
        error(f'''Unknown configuration attributes: {', '.join(unknown_entries)}''') 

    # Check data types.
    for entry, value in config.items():
        if type(value) != datatypes[entry]:
            error(f'"{entry}" has datatype {type(value)}, but should be {datatypes[entry]}.')
    
    # Set defaults.
    for entry, value in defaults.items():
        if entry not in config.keys():
            config[entry] = value
        
    # Check if elements of 'apply' are valid strings.
    for elem in config['apply']:
        if not isinstance(elem, str):
            error(f'"apply" must contain only strings, but "{elem}" has datatype {type(elem)}.') 
        
    return config

def calc_expectation_and_commands(apply_list: List[str]) -> Tuple[str, List[str], List[str]]:
    """Takes the apply list and calculates the effective Notes
    and the commands to achieve it. Both are returned. In case of an
    error the function error() gets called.
    
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
    commands = []
    effective_solution_notes = None
 
    # HERE WE NEED TO CALL A FUNCTION TO POPULATE THE VARIABLES.
    existing_notes = ['1410736', '1656250', '1680803', '1771258', '1805750', '1868829', '1980196', '2161991', '2382421', '2534844', '2578899', '2684254', '2993054', '3024346', '900929', '941735', 'SAP_BOBJ']
    existing_solutions = ['BOBJ', 'HANA', 'MAXDB', 'NETWEAVER', 'NETWEAVER+HANA', 'NETWEAVER+MAXDB', 'S4HANA-APP+DB', 'S4HANA-APPSERVER', 'S4HANA-DBSERVER', 'SAP-ASE']
    solution_map = {'BOBJ': ['941735', '1771258', '2578899', 'SAP_BOBJ', '2993054', '1656250'], 'HANA': ['941735', '1771258', '1868829', '1980196', '2578899', '2684254', '2382421', '2534844', '2993054', '1656250'], 'MAXDB': ['941735', '1771258', '2578899'], 'NETWEAVER': ['941735', '1771258', '2578899', '2993054', '1656250', '900929'], 'NETWEAVER+HANA': ['941735', '1771258', '1868829', '1980196', '2578899', '2684254', '2382421', '2534844', '2993054', '1656250'], 'NETWEAVER+MAXDB': ['941735', '1771258', '2578899', '2993054', '1656250', '900929'], 'S4HANA-APP+DB': ['941735', '1771258', '1868829', '1980196', '2578899', '2684254', '2382421', '2534844', '2993054', '1656250'], 'S4HANA-APPSERVER': ['941735', '1771258', '2578899', '2993054', '1656250', '900929'], 'S4HANA-DBSERVER': ['941735', '1771258', '1868829', '1980196', '2578899', '2684254', '2382421', '2534844', '2993054', '1656250'], 'SAP-ASE': ['941735', '1680803', '1771258', '2578899', '2993054', '1656250']}

    # Walk through the apply list.
    solution = None
    for entry in apply_list:
        print(entry)

        # A Solution may not have a minus operator.
        if entry[0:2] == '-@':
            error(f'Solutions cannot have a minus operator: "{entry}"')
        
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
                error(f'Solution "{entry}" is unknown!"')
            if effective_solution:
                error(f'Only one Solution is allowed!')
            effective_solution = entry
            effective_solution_notes = OrderedSet(solution_map[entry]) 
            effective_notes.update(effective_solution_notes)
            commands.append(['saptune', 'solution', 'apply', entry])
        else:   # Note
            if entry not in existing_notes:
                error(f'Note "{entry}" is unknown!"')
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
                
    return effective_solution, effective_notes, commands


def main():
    
    with open('./conf.yaml', 'r') as f:
        config = yaml.safe_load(f)
        
    config = validate_config(config)
    expected_solution, expected_notes, commands = calc_expectation_and_commands(config['apply'])    

    print('---')
    print(expected_solution)
    print(expected_notes)
    for note in expected_notes:
        print(note, type(note))
    print(commands)

if __name__ == '__main__':
    main()
