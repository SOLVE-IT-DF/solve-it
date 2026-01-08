"""
SOLVE-IT Knowledge Base TSV Exporter

This script generates a TSV text of the SOLVE-IT knoweldge base to stdout

The script can be used directly from the command line

"""


import re
import argparse
import sys
import os
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library import KnowledgeBase

# Configure logging to show errors to console
logging.basicConfig(level=logging.ERROR, format='ERROR: %(message)s')

def print_objectives(kb, long):
    """Prints the SOLVE-IT objectives to stdout"""
    print('Objective\tDescription')
    objectives_name_list = kb.list_tactics()
    for each_objective in objectives_name_list:
        print("{}\t{}".format(each_objective, 'todo'))
    return ""


def print_techniques(kb, long):
    """Prints the SOLVE-IT techniques to stdout"""
    # Print long or short header for techniques
    if long is True:
        print('ID\tName\tDescription\tSynonyms')
    else:
        print('ID\tName')

    techniques = kb.list_techniques()
    for each_technique_id in techniques:
        if each_technique_id != "T1000":
            each_technique = kb.get_technique(each_technique_id)
            # Print long or short details for each technique
            if long is True:
                print('{}\t{}\t{}\t{}'.format(each_technique_id,
                                              each_technique.get('name'),
                                              each_technique.get('description'),
                                              each_technique.get('synonyms'), )
                      )
            else:
                print('{}\t{}\t'.format(each_technique_id,
                                        each_technique.get('name'))
                      )


def print_techniques_by_objective(kb, long):
    """Prints the SOLVE-IT techniques to stdout"""
    # Print long or short header for techniques
    if long is True:
        print('Objective\tName\tDescription\tSynonyms')
    else:
        print('Objective\tID\tName')

    objectives = kb.list_objectives()
    for each_objective in objectives:
        # print(each_objective.get('name'))
        for each_technique_id in each_objective.get('techniques'):
            t = kb.get_technique(each_technique_id)
            if long is True:
                print(f'{each_objective.get('name')}\t{each_technique_id}\t{t.get('name')}\t{t.get('description')}\t{t.get('synonyms')}')
            else:
                print(f'{each_objective.get('name')}\t{each_technique_id}\t{t.get('name')}')
            
            # process subtechniques too
            for each_sub_id in t.get('subtechniques'):
                s = kb.get_technique(each_sub_id)
                if long is True:
                    print(f'{each_objective.get('name')}\t{each_sub_id}\t{s.get('name')} (s)\t{s.get('description')}\t{s.get('synonyms')}')
                else:
                    print(f'{each_objective.get('name')}\t{each_sub_id}\t{s.get('name')} (s)')


def print_weaknesses(kb, long):
    """Prints the SOLVE-IT weaknesses to stdout"""
    # Print long or short headers for weaknesses
    if long is True:
        print('ID\tName\tINCOMP\tINAC-EX\tINAC-AS\tINAC-ALT\tINAC-COR\tMISINT')
    else:
        print('ID\tName')

    for each_weakness in kb.list_weaknesses():
        w = kb.get_weakness(each_weakness)
        # Print long or short details for each weakness
        if long is True:
            print("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(each_weakness,
                                                      w.get('name'), w.get('INCOMP'), w.get('INAC_EX'),
                                                      w.get('INAC_AS'), w.get('INAC_ALT'),
                                                      w.get('INAC_COR'), w.get('MISINT')
                                                      ))
        else:
            print("{}\t{}".format(each_weakness,
                                  w.get('name')))

def print_mitigations(kb, long):
    """Prints the SOLVE-IT mitigations to stdout"""
    if long is True:
        print('ID\tName\tTechnique')
    else:
        print('ID\tName')
    
    for each_mitigation in kb.list_mitigations():
        m = kb.get_mitigation(each_mitigation)
        mitigation_name = m.get('name')
        
        # Add technique ID in parentheses if it exists (matching Excel behavior)
        if m.get('technique'):
            mitigation_name = f"{mitigation_name} ({m.get('technique')})"
        
        if long is True:
            technique_id = m.get('technique') or ''
            print("{}\t{}\t{}".format(each_mitigation, m.get('name'), technique_id))
        else:
            print("{}\t{}".format(each_mitigation, mitigation_name))


def print_case_mapping(kb, long):
    print('ID\tName')
    for each_techniques in kb.list_techniques():
        t = kb.get_technique(each_techniques)
        print("{}\t{}\t".format(each_techniques, t.get('name')), end='')        
        for each_class in t.get('CASE_output_classes'):
            print('\n' + '\t\t\t' + f"{each_class}", end='')
        print()
        
def main():
    """Command-line entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate TSV output for parts of the SOLVE-IT knowledge base")
    parser.add_argument('--objectives', '-o', action='store_true',
                        help="Print the objectives from SOLVE-IT in TSV format")
    parser.add_argument('--techniques', '-t', action='store_true',
                        help="Print the techniques from SOLVE-IT in TSV format")
    parser.add_argument('--techniques_by_objective', '-t2', action='store_true',
                        help="Print the techniques (organized by objective) from SOLVE-IT in TSV format")
    parser.add_argument('--weaknesses', '-w', action='store_true',
                        help="Print the weaknesses from SOLVE-IT in TSV format")
    parser.add_argument('--mitigations', '-m', action='store_true',
                        help="Print the mitigations from SOLVE-IT in TSV format")
    parser.add_argument('--case', '-c', action='store_true',
                        help="Print the mapping of techniques to CASE ontology")
    parser.add_argument('--long', '-l', action='store_true',
                        help="Print extended fields other than ID and name")

    args = parser.parse_args()

    # Calculate the path to the solve-it directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    solve_it_root = os.path.dirname(script_dir)  # Go up from reporting_scripts to solve-it root
    
    kb = KnowledgeBase(solve_it_root, 'solve-it.json')

    if args.objectives is True:
        print_objectives(kb, args.long)
    elif args.techniques is True:
        print_techniques(kb, args.long)
    elif args.techniques_by_objective is True:
        print_techniques_by_objective(kb, args.long)
    elif args.weaknesses is True:
        print_weaknesses(kb, args.long)
    elif args.mitigations is True:
        print_mitigations(kb, args.long)
    elif args.case is True:
        print_case_mapping(kb, args.long)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
