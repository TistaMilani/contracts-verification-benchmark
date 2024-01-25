'''
Generates solcmc contracts from versions and properties files.
'''

from setup import injector
from pathlib import PurePath
import logging
import utils
import sys
import re


TAG_GHOSTSTATE = '/// @custom:ghost'
TAG_PREGHOST = '/// @custom:preghost'
TAG_POSTGHOST = '/// @custom:postghost'
TAG_INVARIANT = '/// @custom:invariant'


def get_ghost(lines, i):
    '''
    Yields the code until EOF or '///'.
    Returns the code and the new index.
    '''
    code = [lines[i-1]]     # Save tag

    while i < len(lines) and not any(
            [TAG_GHOSTSTATE in lines[i],
             TAG_PREGHOST in lines[i],
             TAG_POSTGHOST in lines[i],
             TAG_INVARIANT in lines[i]]):

        code.append(lines[i])
        i += 1

    print(code)
    return code, i


def get_ghosts(property_path: str) -> dict:
    '''
    Extracts the ghost code from a solcmc property file.
    '''

    ghosts = {
            'pre': {},
            'post': {},
            'state': [],
            'invariants': []
            }

    # Support old specifications, to be removed later
    with open(property_path, 'r') as f:
        prop = f.read()

        state_match = re.search(TAG_GHOSTSTATE, prop)
        pre_match = re.search(TAG_PREGHOST + ' (.*)', prop)
        post_match = re.search(TAG_POSTGHOST + ' (.*)', prop)
        inv_match = re.search(TAG_INVARIANT, prop)

        if not any([state_match,
                    pre_match,
                    post_match,
                    inv_match]) and len(prop) > 0:
            ghosts['invariants'].append([l + '\n' for l in prop.splitlines()])
            return ghosts

    # Yield verification ghosts
    with open(property_path, 'r') as f:
        lines = f.readlines()
        i = 0
        header_collected = False   # To collect header
        header = []

        while i < len(lines):
            line = lines[i]

            ''' This is very inefficient '''
            # Look for a tag in the current line
            state_match = re.search(TAG_GHOSTSTATE, line)
            pre_match = re.search(TAG_PREGHOST + ' (.*)', line)
            post_match = re.search(TAG_POSTGHOST + ' (.*)', line)
            inv_match = re.search(TAG_INVARIANT, line)

            if state_match:
                if not header_collected:
                    header_collected = True
                    header = lines[:i]
                state, i = get_ghost(lines, i+1)
                ghosts['state'] += header + state
            elif pre_match:
                if not header_collected:
                    header_collected = True
                    header = lines[:i]
                # Save function name and preghosts
                fun = pre_match.group(1).strip()
                precond, i = get_ghost(lines, i+1)
                ghosts['pre'][fun] = header + precond
            elif post_match:
                if not header_collected:
                    header_collected = True
                    header = lines[:i]
                # Save function name and postghosts
                fun = post_match.group(1).strip()
                postcond, i = get_ghost(lines, i+1)
                ghosts['post'][fun] = header + postcond
            elif inv_match:
                if not header_collected:
                    header_collected = True
                    header = lines[:i]
                # Save invariants
                inv, i = get_ghost(lines, i+1)
                ghosts['invariants'] += [header + inv]
            else:
                i += 1

            if header:
                header = []

    return ghosts


def instrument_contracts(versions_paths: list, properties_paths: list) -> dict:
    '''
    Instruments contracts to verify from versions and properties.
    They will go to build/contracts.

    Returns:
        dict: { filename: contract_code, ...}
    '''

    '''IMPROVEMENT 
    Move properties sorting in a separate function '''
    # Properties associated with a version
    specific_properties = list(filter(
            lambda x: re.search(".*_v.*", x),
            properties_paths))

    # Generic properties
    generic_properties = list(
            set(properties_paths) - set(specific_properties))

    contracts = {}

    for v_path in versions_paths:
        # Extract base id from base path (e.g. v1)
        v_id = PurePath(v_path).stem.split('_')[1]

        # Properties associated with the current version v
        v_specific_properties = list(filter(
                lambda x: re.search(f'.*_{v_id}.*', x),
                specific_properties))

        v_generic_properties = generic_properties

        # Remove bound properties from the unbound variants
        for specific_property in v_specific_properties:
            # ../p1_v1.sol -> p1
            p_id = PurePath(specific_property).stem.split('_')[0]

            v_generic_properties = list(filter(
                    lambda x: not re.search(f'{p_id}', x),
                    v_generic_properties
                    ))

        # List of properties to verify for the current version
        v_properties_paths = v_specific_properties + v_generic_properties

        # Instrument version for every property
        for property_path in v_properties_paths:

            contract = []   # contract to instrument
            with open(v_path, 'r') as f:
                contract = f.readlines()

            ghosts = get_ghosts(property_path)

            if not any([ghosts['state'],
                        ghosts['pre'],
                        ghosts['post'],
                        ghosts['invariants']]):
                logging.warning(f'No instrumentation found in {property_path}.')

            if ghosts['state']:
                # Inject before last bracket
                contract_pattern = 'contract ' + utils.get_contract_name(v_path)
                contract = injector.inject_after(contract, ghosts['state'], contract_pattern)
                if contract is None:
                    state = ''.join(l for l in code)
                    logging.error(f'Ghost state injection failed: {property_path}: '
                                  f'{v_path}: {state}.')
                    sys.exit(1)

            for fun, code in ghosts['pre'].items():
                # Inject after function signature
                contract = injector.inject_after(contract, code, fun)
                if contract is None:
                    logging.error(
                            f'Preghost injection failed: {property_path}: '
                            f'{v_path}: {fun}.')
                    sys.exit(1)

            for fun, code in ghosts['post'].items():
                # Inject before last bracket of function
                contract = injector.inject_postcond(contract, code, fun)
                if contract is None:
                    logging.error(
                            f'Postghost injection failed: {property_path}: '
                            f'{v_path}: {fun}.')
                    sys.exit(1)

            for inv in ghosts['invariants']:
                # Inject before last bracket
                contract = injector.inject_before_last_bracket(contract, inv)
                if contract is None:
                    inv_as_string = ''.join(l for l in inv)
                    logging.error(f'Invariant injection failed: {property_path}: '
                                  f'{v_path}: {inv_as_string}.')
                    sys.exit(1)

            # Construct filename
            name = PurePath(v_path).stem.split('_')[0]
            p_id = PurePath(property_path).stem
            filename = f'{name}_{p_id}_{v_id}.sol'

            contracts.update({filename: ''.join(l for l in contract)})

    return contracts