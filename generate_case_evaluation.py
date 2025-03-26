import os
import json
import xlsxwriter
import argparse
from xlsxwriter.utility import xl_col_to_name

path_to_data = 'data'
path_to_weaknesses = os.path.join(path_to_data, 'weaknesses')
path_to_mitigations = os.path.join(path_to_data, 'mitigations')
path_to_techniques = os.path.join(path_to_data, 'techniques')

weaknesses = {}
mitigations = {}


def load_tactics(path_to_tactics_list):
    f = open(path_to_tactics_list)
    tactics_list = json.loads(f.read())
    return tactics_list

def load_techniques(path_to_techniques):
    '''Loads techniques from on disk json into dictionary'''
    techniques = {}
    for each in os.listdir(path_to_techniques):
        if each[-4:] == 'json':
            technique_path = os.path.join(path_to_techniques, each)
            f = open(technique_path)
            try:
                tech_dict = json.loads(f.read())
            except json.decoder.JSONDecodeError:
                print('error loading JSON from {}'.format(technique_path))
                quit()
            techniques[tech_dict.get('id')] = tech_dict
    return techniques

def load_weaknesses(path_to_weaknesses):
    '''Loads weaknesses from on disk json into dictionary'''
    weaknesses = {}
    for each in os.listdir(path_to_weaknesses):
        if each[-4:] == 'json':
            f = open(os.path.join(path_to_weaknesses, each))
            weakness_dict = json.loads(f.read())
            weaknesses[weakness_dict.get('id')] = weakness_dict
    return weaknesses


def get_mit_list_for_technique(technique, weaknesses):
    mit_list_for_this_technique = []
    for each_weakness in technique.get('weaknesses'):
        weakness_info = weaknesses.get(each_weakness)

        for each_mitigation in weakness_info.get('mitigations'):
            if each_mitigation not in mit_list_for_this_technique:
                mit_list_for_this_technique.append(each_mitigation)

    return mit_list_for_this_technique

def load_mitigations(path_to_mitigations):
    '''Loads mitigations from on disk json into dictionary'''
    mitigations = {}
    for each in os.listdir(path_to_mitigations):
        if each[-4:] == 'json':
            f = open(os.path.join(path_to_mitigations, each))
            mit_dict = json.loads(f.read())
            mitigations[mit_dict.get('id')] = mit_dict
    return mitigations


def get_max_mitigations_per_technique(techniques, weaknesses):
    max_mits = 0
    for each_technique in techniques:
        mits = get_mit_list_for_technique(techniques[each_technique], weaknesses)

        if len(mits) > max_mits:
            max_mits = len(mits)

    return max_mits

def main():

    # Command line parameter handling
    parser = argparse.ArgumentParser()
    parser.add_argument('techniques', action='store', type=str, nargs='*',
                        help="The list of techniques to include in the evaluation.")
    parser.add_argument('--lab_config', '-l', action='store', type=str,
                        help="Path to a json configuration file for a specific lab setup.")
    parser.add_argument('--case_config', '-c', action='store', type=str,
                        help="Path to a text file of techniques to include for a specific case.")
    parser.add_argument('-o', action='store', type=str, dest='output_file',
                        help="output path for evaluation spreadsheet.")
    args = parser.parse_args()

    techniques = load_techniques(path_to_techniques)
    weaknesses = load_weaknesses(path_to_weaknesses)
    mitigations = load_mitigations(path_to_mitigations)

    if args.output_file:
        outfile = args.output_file
    else:
        outfile = 'case_evaluation.xlsx'

    # quick test that output file is accessible
    try:
        f = open(outfile, 'w')
        f.close()
    except:
        print('output file ({}) could not be opened'.format(outfile))
        quit()


    # load lab config if present:

    if args.lab_config:
        f = open(args.lab_config)
        lab_config = json.loads(f.read())
    else:
        lab_config = {}

    workbook = xlsxwriter.Workbook(outfile)
    main_worksheet = workbook.add_worksheet(name='Main')

    # ----------------------------------------

    # set format for header
    header_type_format = workbook.add_format()
    header_type_format.set_align('center')
    header_type_format.set_align('vcenter')
    header_type_format.set_text_wrap(True)
    header_type_format.set_bold(True)

    # set format for header
    header_small_format = workbook.add_format()
    header_small_format.set_align('center')
    header_small_format.set_align('vcenter')
    header_small_format.set_text_wrap(True)
    header_small_format.set_bold(True)
    header_small_format.set_size(9)

    # set format for centralised x marks
    weakness_type_format = workbook.add_format()
    weakness_type_format.set_align('center')
    weakness_type_format.set_align('vcenter')

    # set format for blanked out bits
    blank_grey_format = workbook.add_format()
    blank_grey_format.set_align('center')
    blank_grey_format.set_align('vcenter')
    blank_grey_format.set_bg_color('#a9a9a9')

    # set format a blank cell
    blank_white_format = workbook.add_format()
    blank_white_format.set_align('center')
    blank_white_format.set_align('vcenter')

    # set format for mitigation cell to complete
    blank_white_format.set_border(style=1)
    blank_white_format.set_border_color('blue')
    blank_white_format.set_bg_color('#ffffff')

    # set format for wrapped title
    wrapped_title = workbook.add_format()
    wrapped_title.set_align('center')
    wrapped_title.set_align('vcenter')
    wrapped_title.set_text_wrap(True)

    # ----------------------------------------

    main_worksheet.set_column(1, 1, 140)

    main_worksheet.write_string(0, 1,"Potential Weaknesses", header_type_format)
    main_worksheet.write_string(0, 2, "INCOMP", header_type_format)
    main_worksheet.write_string(0, 3, "INAC-EX", header_type_format)
    main_worksheet.write_string(0, 4, "INAC-AS", header_type_format)
    main_worksheet.write_string(0, 5, "INAC-ALT", header_type_format)
    main_worksheet.write_string(0, 6, "INAC-COR", header_type_format)
    main_worksheet.write_string(0, 7, "MISINT", header_type_format)
    #main_worksheet.write_string(0, 8, "Mitigations", header_type_format) # writen later now as merged cell

    main_worksheet.write_string(1, 2, "Relevant information has not been acquired or found", header_small_format)
    main_worksheet.write_string(1, 3, "Do all artefacts reported as present actually exist", header_small_format)
    main_worksheet.write_string(1, 4, "For every set of items identified by a given tool, is each item truly part of that set", header_small_format)
    main_worksheet.write_string(1, 5, "Does a tool alter data in a way that changes its meaning?", header_small_format)
    main_worksheet.write_string(1, 6, "Does the forensic tool detect and compensate for missing and corrupted dataDoes the forensic tool detect and compensate for missing and corrupted data", header_small_format)
    main_worksheet.write_string(1, 7, "The results are displayed in a manner that encourages, or does not prevent misinterpretation", header_small_format)


    # Write mitigations top header
    max_mits = get_max_mitigations_per_technique(techniques, weaknesses)
    print('Max mitiations: {}'.format(max_mits))
    max_letter = chr(ord('I') + max_mits-1)
    main_worksheet.merge_range("I1:{}1".format(max_letter), "Mitigations", header_type_format)
    for i in range(0, max_mits):
        main_worksheet.write_string(1, 8+i, "M{}".format(i), wrapped_title)

    # Write column headings for totals Y. N etc.
    main_worksheet.write_string(0, 8 + max_mits + 0, "Y", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 1, "N", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 2, "-", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 3, "NA", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 4, "Max", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 5, "Met", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 6, "Status", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 7, "s", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 8, "f", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 9, "d", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 10, "t", header_type_format)
    main_worksheet.write_string(0, 8 + max_mits + 11, "Notes", header_type_format)

    # formats the size of the extra columns at the end
    main_worksheet.set_column(8 + max_mits + 0, 8 + max_mits + 11, 4)
    main_worksheet.set_column(8 + max_mits + 11, 8 + max_mits + 11, 60)


    if len(args.techniques) == 0:
        # print them all
        techniques_to_print = techniques
    else:
        # Take them from the CLI arguments
        techniques_to_print = args.techniques

        # techniques_to_print = ['T1001',  # Triage
        #                        'T1002',  # disk imaging
        #                        'T1042',  # disk image hash validation
        #                        'T1059',  # identify partitions
        #                        'T1060',  # process file system structures
        #                        'T1054',  # media review
        #                        'T1049'   # keyword searching
        #                         ]

    print(techniques)

    # Big loop for each technique...
    start_pos = 2
    for each_technique in techniques_to_print:
        # add a grey divider row
        for i in range(0, 8+max_mits):
            main_worksheet.write_string(start_pos, i, '', cell_format=blank_grey_format)
        start_pos+=1

        main_worksheet.write_string(start_pos, 0, "{}: {}".format(each_technique,
                                                                  techniques[each_technique].get('name')),
                                    header_type_format)
        main_worksheet.write_string(start_pos, 1, "Potential Weaknesses", header_type_format)

        # write the headers for INCOMP etc each time...
        main_worksheet.write_string(start_pos, 2, "INCOMP", header_type_format)
        main_worksheet.write_string(start_pos, 3, "INAC-EX", header_type_format)
        main_worksheet.write_string(start_pos, 4, "INAC-AS", header_type_format)
        main_worksheet.write_string(start_pos, 5, "INAC-ALT", header_type_format)
        main_worksheet.write_string(start_pos, 6, "INAC-COR", header_type_format)
        main_worksheet.write_string(start_pos, 7, "MISINT", header_type_format)

        # write all the mitigation titles
        mit_index = {}

        mits = get_mit_list_for_technique(techniques[each_technique], weaknesses)

        for i, each_mit in enumerate(mits):
            main_worksheet.write_string(start_pos, 8 + i, "{}\n{}".format(each_mit, mitigations[each_mit].get('name')), header_small_format)
            mit_index[each_mit] = 8 + i

        # write the weaknesses out for each technique and flag the weakness type
        for i, each_weakness in enumerate(techniques[each_technique].get('weaknesses')):
            weakness_info = weaknesses[each_weakness]
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


            # Now do the mitigations
            # mask out whole grid grey for mitigations, and the valid ones will be made white later on
            for i in range(0, max_mits):
                main_worksheet.write_string(start_pos + 1, 8 + i, '', cell_format=blank_grey_format)

            # write a blank cell if the mitigation applies to the weakness being written currently
            for each_mit in weakness_info.get('mitigations'):
                main_worksheet.write_string(start_pos + 1, mit_index[each_mit], 'N', cell_format=blank_white_format) # note we default everythign to N to start with
                main_worksheet.data_validation('{}{}'.format(xl_col_to_name(mit_index[each_mit]), str(start_pos+2)),
                                                        {'validate': 'list',
                                                            'source': ['Y', 'N', 'NA']})

                # If a lab config file is in use, write the status and notes for this mitigation
                if each_mit in lab_config:
                    main_worksheet.write_string('{}{}'.format(xl_col_to_name(mit_index[each_mit]), str(start_pos+2)),
                                                        lab_config[each_mit].get('status'))

                    main_worksheet.write_string('{}{}'.format('AD', str(start_pos+2)),
                                                        lab_config[each_mit].get('notes'))
                else: # write blank to start with
                    main_worksheet.write_string('{}{}'.format(xl_col_to_name(mit_index[each_mit]), str(start_pos+2)),
                                                        "-")


            # write formula to calculate total mitigations etc
            main_worksheet.write_formula(start_pos+1, 8 + max_mits + 0,
                                         '=COUNTIF(' + xl_col_to_name(8) + str(start_pos+2) + ":" + xl_col_to_name(
                                             8+max_mits-1) + str(start_pos+2) + ',"Y")')
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 1,
                                         '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                             8 + max_mits - 1) + str(start_pos + 2) + ',"N")')
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 2,
                                         '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                             8 + max_mits - 1) + str(start_pos + 2) + ',"-")')
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 3,
                                         '=COUNTIF(' + xl_col_to_name(8) + str(start_pos + 2) + ":" + xl_col_to_name(
                                             8 + max_mits - 1) + str(start_pos + 2) + ',"NA")')
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 4,
                                         '=SUM(' + xl_col_to_name(8+max_mits) + str(start_pos+2) + ':' + xl_col_to_name(
                                             8+max_mits+2) + str(start_pos+2) + ')')
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 5,
                                         xl_col_to_name(8+max_mits) + str(start_pos+2) + '&"/"&' + xl_col_to_name(
                                             8+max_mits+4) + str(start_pos+2) + '', header_type_format)
            form = "=IF(AND(" + xl_col_to_name(8 + max_mits + 0) + str(start_pos+2) + "=0," + xl_col_to_name(8 + max_mits + 1) + str(start_pos+2) + ">0),\"x\",\"\")"
            # print(form)
            main_worksheet.write_formula(start_pos + 1, 8 + max_mits + 6,
                                          form , header_type_format)


#=IF(AND(S5=0,T5>0),"x","")

            start_pos+=1

        # # add a grey divider row
        # for i in range(0, 8+max_mits):
        #     main_worksheet.write_string(start_pos, i, '', cell_format=blank_grey_format)
        start_pos += 1

    workbook.close()


if __name__ == "__main__":
    main()




