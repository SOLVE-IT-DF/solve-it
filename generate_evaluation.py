#!/usr/bin/env python3
"""
SOLVE-IT Evaluation Spreadsheet Generator

This script generates an Excel workbook that evaluates SOLVE-IT digital forensic
techniques against their potential weaknesses and mitigations. It provides a
framework for systematically assessing techniques by showing:
- Techniques and their weaknesses
- Types of weaknesses (INCOMP, INAC-EX, etc.)
- Associated mitigations for each weakness
- Interactive cells for marking mitigation status (Y/N/NA)
- Summary statistics and formulas

The script can be used directly from the command line or imported as a module
by other Python code.
"""

import os
import json
import xlsxwriter
import argparse
import sys
import solveitcore
from xlsxwriter.utility import xl_col_to_name


def generate_evaluation(techniques=None, lab_config=None, output_file=None):
    """Generate an evaluation spreadsheet for the specified techniques.
    
    Args:
        techniques: List of technique IDs to include. If None or empty, includes all techniques.
        lab_config: Path to a JSON configuration file for a specific lab setup.
        output_file: Custom output path for the Excel file.
        
    Returns:
        str: Path to the generated output file.
    """
    # Initialize parameters if not provided
    if techniques is None:
        techniques = []
        
    # Set default output file path if not provided
    if not output_file:
        if not os.path.exists('output'):
            os.mkdir('output')
        output_file = os.path.join('output', 'solve-it_evaluation_workbook.xlsx')
    
    # Generate a unique filename if the file already exists
    if os.path.exists(output_file):
        # Get the file name and extension
        base_path, extension = os.path.splitext(output_file)
        
        # Add a timestamp to make the filename unique
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{base_path}_{timestamp}{extension}"
        print(f"Output file already exists. Using new filename: {output_file}")

    # Quick test that output file is accessible
    try:
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        f = open(output_file, 'w')
        f.close()
    except Exception as e:
        raise IOError(f'Output file ({output_file}) could not be opened: {str(e)}')

    # Load knowledge base
    kb = solveitcore.SOLVEIT('data', 'solve-it.json')

    # Load lab config if present
    lab_config_data = {}
    if lab_config:
        try:
            with open(lab_config) as f:
                lab_config_data = json.loads(f.read())
        except Exception as e:
            raise ValueError(f"Error loading lab config file: {str(e)}")

    # Create the workbook
    workbook = xlsxwriter.Workbook(output_file)
    main_worksheet = workbook.add_worksheet(name='Main')

    # ----------------------------------------
    # Create cell formatting options for the workbook
    # ----------------------------------------

    # Define various cell formats for different parts of the spreadsheet
    # Each format controls appearance aspects like alignment, text wrapping,
    # borders, colors, and font styles
    
    # Primary header format for column titles
    header_type_format = workbook.add_format()
    header_type_format.set_align('center')
    header_type_format.set_align('vcenter')
    header_type_format.set_text_wrap(True)
    header_type_format.set_bold(True)

    # Set format for header
    header_small_format = workbook.add_format()
    header_small_format.set_align('center')
    header_small_format.set_align('vcenter')
    header_small_format.set_text_wrap(True)
    header_small_format.set_bold(True)
    header_small_format.set_font_size(9)

    # Set format for centralised x marks
    weakness_type_format = workbook.add_format()
    weakness_type_format.set_align('center')
    weakness_type_format.set_align('vcenter')

    # Set format for blanked out bits
    blank_grey_format = workbook.add_format()
    blank_grey_format.set_align('center')
    blank_grey_format.set_align('vcenter')
    blank_grey_format.set_bg_color('#a9a9a9')

    # Set format a blank cell
    blank_white_format = workbook.add_format()
    blank_white_format.set_align('center')
    blank_white_format.set_align('vcenter')

    # Set format for mitigation cell to complete
    blank_white_format.set_border(style=1)
    blank_white_format.set_border_color('blue')
    blank_white_format.set_bg_color('#ffffff')

    # Set format for wrapped title
    wrapped_title = workbook.add_format()
    wrapped_title.set_align('center')
    wrapped_title.set_align('vcenter')
    wrapped_title.set_text_wrap(True)

    # ----------------------------------------
    # Setup workbook layout with column headers and formatting
    # ----------------------------------------

    # Set width for the weakness description column (needs to be wide)
    main_worksheet.set_column(1, 1, 140)

    main_worksheet.write_string(0, 1, "Potential Weaknesses", header_type_format)
    main_worksheet.write_string(0, 2, "INCOMP", header_type_format)
    main_worksheet.write_string(0, 3, "INAC-EX", header_type_format)
    main_worksheet.write_string(0, 4, "INAC-AS", header_type_format)
    main_worksheet.write_string(0, 5, "INAC-ALT", header_type_format)
    main_worksheet.write_string(0, 6, "INAC-COR", header_type_format)
    main_worksheet.write_string(0, 7, "MISINT", header_type_format)
    # main_worksheet.write_string(0, 8, "Mitigations", header_type_format) # written later now as merged cell

    main_worksheet.write_string(1, 2, "Relevant information has not been acquired or found", header_small_format)
    main_worksheet.write_string(1, 3, "Do all artefacts reported as present actually exist", header_small_format)
    main_worksheet.write_string(1, 4, "For every set of items identified by a given tool, is each item truly part of that set", header_small_format)
    main_worksheet.write_string(1, 5, "Does a tool alter data in a way that changes its meaning?", header_small_format)
    main_worksheet.write_string(1, 6, "Does the forensic tool detect and compensate for missing and corrupted dataDoes the forensic tool detect and compensate for missing and corrupted data", header_small_format)
    main_worksheet.write_string(1, 7, "The results are displayed in a manner that encourages, or does not prevent misinterpretation", header_small_format)

    # Write mitigations top header
    max_mits = kb.get_max_mitigations_per_technique()
    print('Max mitigations: {}'.format(max_mits))
    max_letter = chr(ord('I') + max_mits - 1)
    main_worksheet.merge_range("I1:{}1".format(max_letter), "Mitigations", header_type_format)
    for i in range(0, max_mits):
        main_worksheet.write_string(1, 8 + i, "M{}".format(i), wrapped_title)

    # Write column headings for totals Y. N etc.
    main_worksheet.write_string(0, 8 + max_mits + 0, "Y", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 1, "N", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 2, "-", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 3, "NA", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 4, "Max", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 5, "Met", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 6, "Status", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 7, "s1", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 8, "f1", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 9, "d1", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 10, "t1", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 11, "s2", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 12, "f2", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 13, "d2", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 14, "t2", header_type_format)

    main_worksheet.write_string(0, 8 + max_mits + 15, "Notes", header_type_format)

    # Format the size of the extra columns at the end
    main_worksheet.set_column(8 + max_mits + 0, 8 + max_mits + 15, 4)
    main_worksheet.set_column(8 + max_mits + 15, 8 + max_mits + 15, 60)

    # Determine which techniques to include
    if not techniques:
        # Use all techniques if none specified
        techniques_to_print = kb.list_techniques()
    else:
        # Use the provided technique IDs
        techniques_to_print = techniques

    print(techniques_to_print)

    # ----------------------------------------
    # Generate content for each technique
    # ----------------------------------------
    
    # Big loop for each technique...
    start_pos = 2
    for each_technique in techniques_to_print:
        technique = kb.get_technique(each_technique)
        
        # Skip if technique doesn't exist
        if technique is None:
            print(f"Warning: Technique {each_technique} not found in knowledge base. Skipping.")
            continue
            
        # Add a grey divider row
        for i in range(0, 8 + max_mits):
            main_worksheet.write_string(start_pos, i, '', cell_format=blank_grey_format)
        start_pos += 1

        main_worksheet.write_string(start_pos, 0, "{}: {}".format(each_technique,
                                                                  technique.get('name')),
                                    header_type_format)
        main_worksheet.write_string(start_pos, 1, "Potential Weaknesses", header_type_format)

        # Write the headers for INCOMP etc. each time...
        main_worksheet.write_string(start_pos, 2, "INCOMP", header_type_format)
        main_worksheet.write_string(start_pos, 3, "INAC-EX", header_type_format)
        main_worksheet.write_string(start_pos, 4, "INAC-AS", header_type_format)
        main_worksheet.write_string(start_pos, 5, "INAC-ALT", header_type_format)
        main_worksheet.write_string(start_pos, 6, "INAC-COR", header_type_format)
        main_worksheet.write_string(start_pos, 7, "MISINT", header_type_format)

        # Write all the mitigation titles
        mit_index = {}

        mits = kb.get_mit_list_for_technique(each_technique)

        for i, each_mit in enumerate(mits):
            main_worksheet.write_string(start_pos, 8 + i, "{}\n{}".format(each_mit, kb.get_mitigation(each_mit).get('name')), header_small_format)
            mit_index[each_mit] = 8 + i

        # Write the weaknesses out for each technique and flag the weakness type
        for i, each_weakness in enumerate(technique.get('weaknesses')):
            weakness_info = kb.get_weakness(each_weakness)
            main_worksheet.write_string(start_pos + 1, 0, "{}".format(each_weakness))
            main_worksheet.write_string(start_pos + 1, 1, "{}".format(weakness_info.get('name')))
            main_worksheet.write_string(start_pos + 1, 2, weakness_info.get('INCOMP', ''),
                                      cell_format=weakness_type_format)
            main_worksheet.write_string(start_pos + 1, 3, weakness_info.get('INAC-EX', ''),
                                      cell_format=weakness_type_format)
            main_worksheet.write_string(start_pos + 1, 4, weakness_info.get('INAC-AS', ''),
                                      cell_format=weakness_type_format)
            main_worksheet.write_string(start_pos + 1, 5, weakness_info.get('INAC-ALT', ''),
                                      cell_format=weakness_type_format)
            main_worksheet.write_string(start_pos + 1, 6, weakness_info.get('INAC-COR', ''),
                                      cell_format=weakness_type_format)
            main_worksheet.write_string(start_pos + 1, 7, weakness_info.get('MISINT', ''),
                                      cell_format=weakness_type_format)

            # Now do the mitigations for this weakness
            # First mask out whole grid grey for mitigations (visual cue for cells not applicable to this weakness)
            for i in range(0, max_mits):
                main_worksheet.write_string(start_pos + 1, 8 + i, '', cell_format=blank_grey_format)

            # For each mitigation that applies to the current weakness:
            # - Write a white cell with dropdown selection options (Y/N/NA)
            # - Default value is 'N' until user evaluates
            for each_mit in weakness_info.get('mitigations'):
                main_worksheet.write_string(start_pos + 1, mit_index[each_mit], 'N', cell_format=blank_white_format)  # note we default everything to N to start with
                main_worksheet.data_validation('{}{}'.format(xl_col_to_name(mit_index[each_mit]), str(start_pos + 2)),
                                             {'validate': 'list',
                                              'source': ['Y', 'N', 'NA']})

                # If a lab config file is in use, write the status and notes for this mitigation
                if each_mit in lab_config_data:
                    main_worksheet.write_string('{}{}'.format(xl_col_to_name(mit_index[each_mit]), str(start_pos + 2)),
                                              lab_config_data[each_mit].get('status'))

                    main_worksheet.write_string('{}{}'.format('AH', str(start_pos + 2)),
                                              lab_config_data[each_mit].get('notes'))
                else:  # write blank to start with
                    main_worksheet.write_string('{}{}'.format(xl_col_to_name(mit_index[each_mit]), str(start_pos + 2)),
                                              "-")

            # Add Excel formulas for automatic calculations of mitigation statistics
            # These formulas help evaluate the status of mitigations for each weakness
            
            # Count cells with "Y" (mitigations implemented)
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 0,
                                       '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                           8 + max_mits - 1) + str(start_pos + 2) + ',"Y")')
            
            # Count cells with "N" (mitigations not implemented)
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 1,
                                       '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                           8 + max_mits - 1) + str(start_pos + 2) + ',"N")')
            
            # Count cells with "-" (mitigations not evaluated)
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 2,
                                       '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                           8 + max_mits - 1) + str(start_pos + 2) + ',"-")')
            
            # Count cells with "NA" (mitigations not applicable)
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 3,
                                       '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                           8 + max_mits - 1) + str(start_pos + 2) + ',"NA")')
            
            # Sum of Y, N, and - counts (total applicable mitigations)
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 4,
                                       '=SUM(' + xl_col_to_name(8 + max_mits) + str(start_pos + 2) + ':' + xl_col_to_name(
                                           8 + max_mits + 2) + str(start_pos + 2) + ')')
            
            # Create fraction showing implemented / total (e.g., "5/10")
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 5,
                                       xl_col_to_name(8 + max_mits) + str(start_pos + 2) + '&"/"&' + xl_col_to_name(
                                           8 + max_mits + 4) + str(start_pos + 2) + '', header_type_format)
            
            # Status formula: Shows "x" if there are unmet mitigations (Y=0 and N>0)
            form = "=IF(AND(" + xl_col_to_name(8 + max_mits + 0) + str(start_pos + 2) + "=0," + xl_col_to_name(8 + max_mits + 1) + str(
                start_pos + 2) + ">0),\"x\",\"\")"
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 6,
                                       form, header_type_format)

            start_pos += 1

        start_pos += 1

    # Close and save the workbook
    workbook.close()
    
    # Return the path to the generated file
    return output_file


def main():
    """Command-line entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate an evaluation spreadsheet for SOLVE-IT techniques")
    parser.add_argument('techniques', action='store', type=str, nargs='*',
                        help="The list of techniques to include in the evaluation.")
    parser.add_argument('--lab_config', '-l', action='store', type=str,
                        help="Path to a json configuration file for a specific lab setup.")
    parser.add_argument('--case_config', '-c', action='store', type=str,
                        help="Path to a text file of techniques to include for a specific case.")
    parser.add_argument('-o', action='store', type=str, dest='output_file',
                        help="output path for evaluation spreadsheet.")
    args = parser.parse_args()
    
    # Process case_config file if provided
    techniques = args.techniques
    if args.case_config:
        try:
            with open(args.case_config, 'r') as f:
                case_techniques = [line.strip() for line in f if line.strip()]
                techniques.extend(case_techniques)
        except Exception as e:
            print(f"Error reading case config file: {str(e)}")
            return 1
    
    try:
        # Call the function with parsed args
        output_file = generate_evaluation(
            techniques=techniques,
            lab_config=args.lab_config,
            output_file=args.output_file
        )
        
        # Print success message to the user
        print(f"Evaluation workbook successfully generated at: {output_file}")
        return 0  # Success exit code
        
    except Exception as e:
        # Print error message
        print(f"Error generating evaluation workbook: {str(e)}")
        return 1  # Error exit code


if __name__ == "__main__":
    # When run as a script, call main() and exit with its return code
    sys.exit(main())
