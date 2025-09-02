import os
import xlsxwriter
import sys
import datetime
import argparse
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from solve_it_library import KnowledgeBase

# Configure logging to show info and errors to console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def format_headings_in_workbook(workbook, tactics):
    header_format = workbook.add_format()
    header_format.set_bold()
    header_format.set_align('vcenter')
    header_format.set_align('center')
    header_format.set_border(style=1)
    header_format.set_text_wrap()
    header_format.set_bg_color('#b5b8b7')

    worksheet = workbook.get_worksheet_by_name('Main')

    # format header row and columns
    worksheet.set_row(0, 50)
    worksheet.set_column(0, len(tactics), 20)

    # write headers
    for i in range(0,len(tactics)):
        worksheet.write_string(0, i, tactics[i].get('name'), header_format)
        worksheet.write_comment(0, i, tactics[i].get('description'), {'font_size': 12, 'width': 200, 'height': 200})

    return workbook

def format_techinque_sheet(worksheet):
    worksheet.set_row(0, 40)
    return worksheet


if __name__ == '__main__':

    """Command-line entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate an Excel version of the SOLVE-IT knowledge base")
    parser.add_argument('-o', action='store', type=str, dest='output_file',
                        help="output path for spreadsheet.")
    args = parser.parse_args()


    # Replace technique organisation configuration file here if needed
    config_file = 'solve-it.json'

    # Calculate the path to the solve-it directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    solve_it_root = os.path.dirname(script_dir)  # Go up from reporting_scripts to solve-it root
    
    kb = KnowledgeBase(solve_it_root, config_file)

    print("Using configuration file: {}".format(config_file))

    tactics_name_list = kb.list_tactics()

    # Determine and if necessary create output folder path
    if args.output_file is not None:
        out_folder = os.path.dirname(args.output_file)
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        outpath = args.output_file
    else:
        if not os.path.exists('output'):
            os.mkdir('output')
        outpath = os.path.join('output', 'solve-it.xlsx')


    print("Output will be to: {}".format(outpath))

    workbook = xlsxwriter.Workbook(outpath)

    # Create all the worksheets
    print('Creating worksheets...')

    workbook.add_worksheet(name='Main')
    workbook.set_size(2000, 1024)
    format_headings_in_workbook(workbook, kb.tactics)
    print("- added 'main' worksheet")

    info_sheet = workbook.add_worksheet(name='Info')
    techniques_sheet = workbook.add_worksheet(name='Techniques')
    weaknesses_sheet = workbook.add_worksheet(name='Weaknesses')
    mitigations_sheet = workbook.add_worksheet(name='Mitigations')

    # Adds some stats into the workbook
    info_sheet.set_column(0, 0, 20)
    info_sheet.set_column(1, 1, 30)
    info_sheet.write_string(0, 0, "Property")
    info_sheet.write_string(0, 1, "Value")
    info_sheet.write_string(1, 0, "Workbook generated")
    info_sheet.write_string(1, 1, datetime.datetime.now(tz=datetime.timezone.utc).isoformat())
    info_sheet.write_string(2, 0, "Number of techniques")
    info_sheet.write_number(2, 1, len(kb.list_techniques()))
    info_sheet.write_string(3, 0, "Number of weaknesses")
    info_sheet.write_number(3, 1, len(kb.list_weaknesses()))
    info_sheet.write_string(4, 0, "Number of mitigations")
    info_sheet.write_number(4, 1, len(kb.list_mitigations()))


    for each_technique_id in sorted(kb.list_techniques()):
        technique_name = kb.get_technique(each_technique_id).get('name')
        workbook.add_worksheet(each_technique_id)

    for i, each_technique in enumerate(sorted(kb.list_techniques())):
        techniques_sheet.write_string(i, 0, each_technique)
        techniques_sheet.write_string(i, 1, kb.get_technique(each_technique).get('name'))
        techniques_sheet.write_number(i, 2, len(kb.get_technique(each_technique).get('weaknesses', [])))
        total_mits = 0
        for each_weakness in kb.get_technique(each_technique).get('weaknesses', []):
            total_mits += len(kb.get_weakness(each_weakness).get('mitigations', []))
        techniques_sheet.write_number(i, 3, total_mits)
        techniques_sheet.write_string(0, 2, "Weaknesses")
        techniques_sheet.write_string(0, 3, "Mitigations")

    print("- populated 'all techniques' worksheet")

    for i, each_weakness in enumerate(sorted(kb.list_weaknesses())):
        weaknesses_sheet.write_string(i+1, 0, each_weakness)
        weaknesses_sheet.write_string(i+1, 1, kb.get_weakness(each_weakness).get('name'))
        weaknesses_sheet.write_number(i+1, 2, len(kb.get_weakness(each_weakness).get('mitigations', [])))
        if len(kb.get_weakness(each_weakness).get('mitigations', [])) == 0:
            weaknesses_sheet.write_string(i+1, 3, "x")
        techniques_for_weakness = kb.get_techniques_for_weakness(each_weakness)
        technique_ids = [t['id'] for t in techniques_for_weakness]
        weaknesses_sheet.write_string(i + 1, 4, str(technique_ids))

        if kb.get_weakness(each_weakness).get('INCOMP') in ['x', 'X']:
            weaknesses_sheet.write_string(i + 1, 5, 'X')
        if kb.get_weakness(each_weakness).get('INAC_EX') in ['x', 'X']:
            weaknesses_sheet.write_string(i + 1, 6, 'X')
        if kb.get_weakness(each_weakness).get('INAC_ALT') in ['x', 'X']:
            weaknesses_sheet.write_string(i + 1, 7, 'X')
        if kb.get_weakness(each_weakness).get('INAC_AS') in ['x', 'X']:
            weaknesses_sheet.write_string(i + 1, 8, 'X')
        if kb.get_weakness(each_weakness).get('INAC_COR') in ['x', 'X']:
            weaknesses_sheet.write_string(i + 1, 9, 'X')
        if kb.get_weakness(each_weakness).get('MISINT') in ['x', 'X']:
            weaknesses_sheet.write_string(i + 1, 10, 'X')

    # write some headers for weakness sheet
    weaknesses_sheet.write_string(0, 0, "ID")
    weaknesses_sheet.write_string(0, 1, "Description")
    weaknesses_sheet.write_string(0, 2, "Mitigations")
    weaknesses_sheet.write_string(0, 3, "Has none")
    weaknesses_sheet.write_string(0, 4, "In technique")
    weaknesses_sheet.write_string(0, 5, "INCOMP")
    weaknesses_sheet.write_string(0, 6, "INAC-EX")
    weaknesses_sheet.write_string(0, 7, "INAC-ALT")
    weaknesses_sheet.write_string(0, 8, "INAC-AS")
    weaknesses_sheet.write_string(0, 9, "INAC-COR")
    weaknesses_sheet.write_string(0, 10, "MISINT")

    print("- populated 'all weaknesses' worksheet")

    for i, each_mitigation in enumerate(sorted(kb.list_mitigations())):
        mitigations_sheet.write_string(i+1, 0, each_mitigation)
        mitigations_sheet.write_string(i+1, 1, kb.get_mitigation(each_mitigation).get('name'))
        techniques_for_mitigation = kb.get_techniques_for_mitigation(each_mitigation)
        technique_ids = [t['id'] for t in techniques_for_mitigation]
        mitigations_sheet.write_string(i+1, 2, str(technique_ids))
        
        weaknesses_for_mitigation = kb.get_weaknesses_for_mitigation(each_mitigation)
        weakness_ids = [w['id'] for w in weaknesses_for_mitigation]
        mitigations_sheet.write_string(i+1, 3, str(weakness_ids))
        mitigations_sheet.write_number(i + 1, 4, len(weakness_ids))

    # write some headers for weakness sheet
    mitigations_sheet.write_string(0, 0, "ID")
    mitigations_sheet.write_string(0, 1, "Description")
    mitigations_sheet.write_string(0, 2, "In techniques")
    mitigations_sheet.write_string(0, 3, "In weakness")
    mitigations_sheet.write_string(0, 4, "Weakness occurances")

    print("- populated 'all techniques' worksheet")

    # records max row written so far for populating techniques in main
    tactics_row_indexes = {}
    for each in kb.list_tactics():
        tactics_row_indexes[each] = 1

    # set format for techniques in main
    technique_format = workbook.add_format()
    technique_format.set_bold(False)
    technique_format.set_align('vcenter')
    technique_format.set_align('center')
    technique_format.set_border(style=1)
    technique_format.set_text_wrap()
    technique_format.set_bg_color("#F3F3F3")

    # Set format to see which ones have some content populated
    technique_format2 = workbook.add_format()
    technique_format2.set_bold(False)
    technique_format2.set_align('vcenter')
    technique_format2.set_align('center')
    technique_format2.set_text_wrap()
    technique_format2.set_border(style=1)
    technique_format2.set_bg_color("#E9E9E9")

    # subtechqniue format 1
    sub_technique_format1 = workbook.add_format()
    sub_technique_format1.set_bold(False)
    sub_technique_format1.set_align('vcenter')
    sub_technique_format1.set_align('center')
    sub_technique_format1.set_border(style=1)
    sub_technique_format1.set_text_wrap()
    sub_technique_format1.set_indent(3)


    # set format for centralised x marks
    weakness_type_format = workbook.add_format()
    weakness_type_format.set_align('center')
    weakness_type_format.set_align('vcenter')

    # -------------------------------------------------------------------------------------------

    print("Updating 'main' worksheet with links to techniques...")
    main_worksheet = workbook.get_worksheet_by_name('Main')
    main_worksheet.set_default_row(60)

    techniques_added = []

    for each_tactic in kb.tactics:
        tactic = each_tactic.get('name')
        column = tactics_name_list.index(tactic)

        for each_technique_id in sorted(each_tactic.get('techniques')):
            if each_technique_id not in techniques_added:
                each_technique = kb.get_technique(each_technique_id)
                if each_technique is None:
                    raise ValueError("Technique {} not found".format(each_technique_id))

                technique_name = each_technique.get('name')
                subtechniques = each_technique.get('subtechniques')

                # Does the formatting based on if weaknesses are present or not
                try:
                    row = tactics_row_indexes[tactic]
                    if len(each_technique['weaknesses']) == 0:
                        the_format = technique_format
                    else:
                        the_format = technique_format2

                    main_worksheet.write_url(row, column, 'internal:{}!A1'.format(each_technique_id),
                                             string=technique_name + '\n' + each_technique_id,
                                             cell_format=the_format)
                    techniques_added.append(each_technique_id)
                    tactics_row_indexes[tactic] += 1

                    # check for subtechqniues and do those first before moving on
                    for each_subtechnique_id in subtechniques:
                        row = tactics_row_indexes[tactic]
                        each_subtechnique = kb.get_technique(each_subtechnique_id)
                        if each_subtechnique is None:
                            raise ValueError(f'Subtechnqiue {each_subtechnique_id} not found. ({each_technique_id})')
                            sys.exit(-1)


                        main_worksheet.write_url(row, column, 'internal:{}!A1'.format(each_subtechnique.get('id')),
                                                 string='> ' + each_subtechnique.get('name') + '\n' + each_subtechnique.get('id'),
                                                 cell_format=sub_technique_format1)

                        if len(each_subtechnique.get('subtechniques')) > 0:
                            logging.error(f'Nested subtechniques are not currently supported')
                            logging.error(f"{str(each_subtechnique.get('subtechniques'))}")
                            sys.exit(-1)

                        techniques_added.append(each_subtechnique_id)
                        tactics_row_indexes[tactic] += 1

                except KeyError:
                    print('Technique {} ({}) had a tactic not found in the tactics ({})'.format(each_technique_id,
                                                                                                technique_name,
                                                                                                tactic))
    print("- 'main' worksheet updated")
    # ---------------------------------------------------------------------------------------------------------------
    # check if any are missed from index sheet

    for each in kb.list_techniques():
        if each not in techniques_added and each != "T1000":  # T1000 is demo technique so not expected to be referenced
            print("WARNING: Technique {} exists, but is not indexed in sheet".format(each))



    # ----------------------------------------------------------------------------------------------------------------
    print('Adding the individual techniques sheets...')
    for each_technique_id in kb.list_techniques():
        technique_name = kb.get_technique(each_technique_id).get('name')

        # find tactics that it belongs to
        parent_tactics = []
        for each_tactic in kb.tactics:
            if each_technique_id in each_tactic.get('techniques'):
                parent_tactics.append(each_tactic.get('name'))

        worksheet = workbook.get_worksheet_by_name(each_technique_id)

        technique_format = workbook.add_format()
        technique_format.set_text_wrap()

        bold_format = workbook.add_format()
        bold_format.set_bold()
        bold_format.set_text_wrap()

        worksheet.write_url(0, 2, 'internal:Main!A1', string='back to main')

        worksheet.set_column(0, 0, 30)
        worksheet.set_column(1, 1, 50)
        worksheet.set_column(8, 8, 60)

        worksheet.write_string(0, 0, 'Technique name: ', bold_format)
        worksheet.write_string(0, 1, technique_name)
        worksheet.write_string(1, 0, 'Technique ID: ', bold_format)
        worksheet.write_string(1, 1, each_technique_id)
        worksheet.write_string(2, 0, 'Category: ', bold_format)
        worksheet.write_string(2, 1, str(parent_tactics))

        worksheet.write_string(3, 0, 'Description: ', bold_format)
        description = kb.get_technique(each_technique_id).get('description') or ''
        worksheet.write_string(3, 1, description, cell_format=technique_format)
        worksheet.write_string(4, 0, 'Synonyms: ', bold_format)
        synonyms = kb.get_technique(each_technique_id).get('synonyms') or []
        worksheet.write_string(4, 1, str(synonyms))
        worksheet.write_string(5, 0, 'Details: ', bold_format)
        details = kb.get_technique(each_technique_id).get('details') or ''
        worksheet.write_string(5, 1, details, cell_format=technique_format)
        worksheet.write_string(6, 0, 'Subtechniques: ', bold_format)
        subtechniques = kb.get_technique(each_technique_id).get('subtechniques') or []

        # note - this needs nicer formatting eventually
        sub_techniques_out = [sub_t + ':' + kb.get_technique(sub_t).get('name') for sub_t in subtechniques]
        worksheet.write_string(6, 1, str(sub_techniques_out))

        worksheet.write_string(7, 0, 'CASE output entities: ', bold_format)
        case_output = kb.get_technique(each_technique_id).get('CASE_output_classes') or []
        worksheet.write_string(7, 1, str(case_output))

        worksheet.write_string(8, 0, 'Examples: ', bold_format)
        examples = kb.get_technique(each_technique_id).get('examples') or []
        worksheet.write_string(8, 1, str(examples), cell_format=technique_format)

        worksheet.write_string(10, 0, 'Potential Weaknesses:', bold_format)

        worksheet.write_string(11, 0, 'Weakness ID:', bold_format)
        worksheet.write_string(11, 1, 'Detail:', bold_format)
        worksheet.write_string(11, 2, 'INCOMP', bold_format)
        worksheet.write_string(11, 3, 'INAC-EX', bold_format)
        worksheet.write_string(11, 4, 'INAC-AS', bold_format)
        worksheet.write_string(11, 5, 'INAC-ALT', bold_format)
        worksheet.write_string(11, 6, 'INAC-COR', bold_format)
        worksheet.write_string(11, 7, 'MISINT', bold_format)
        worksheet.write_string(11, 8, 'Potential Mitigations', bold_format)

        i = 0
        mit_list_for_this_technique = []
        err_list_start_row = 12
        for each_weakness in kb.get_technique(each_technique_id).get('weaknesses'):
            weakness_info = kb.get_weakness(each_weakness)

            try:
                worksheet.write_string(err_list_start_row + i, 0, each_weakness)   # write ID
                worksheet.write_string(err_list_start_row + i, 1, weakness_info.get('name'), cell_format=technique_format)
                worksheet.write_string(err_list_start_row + i, 2, weakness_info.get('INCOMP', ''), cell_format=weakness_type_format)
                worksheet.write_string(err_list_start_row + i, 3, weakness_info.get('INAC_EX', ''), cell_format=weakness_type_format)
                worksheet.write_string(err_list_start_row + i, 4, weakness_info.get('INAC_AS', ''), cell_format=weakness_type_format)
                worksheet.write_string(err_list_start_row + i, 5, weakness_info.get('INAC_ALT', ''), cell_format=weakness_type_format)
                worksheet.write_string(err_list_start_row + i, 6, weakness_info.get('INAC_COR', ''), cell_format=weakness_type_format)
                worksheet.write_string(err_list_start_row + i, 7, weakness_info.get('MISINT', ''), cell_format=weakness_type_format)
            except AttributeError:
                print('attribute error with {} in {}'.format(each_weakness, each_technique_id))
                quit()

            # Write the mitigations at the end of each weakness
            mit_string = ''
            for each_mitigation in weakness_info.get('mitigations'):
                mit_string = mit_string + each_mitigation + ','
                mit_list_for_this_technique.append(each_mitigation)

            worksheet.write_string(err_list_start_row + i, 8, mit_string, cell_format=technique_format)
            i = i+1

        mitigation_start_row = err_list_start_row + i + 1
        worksheet.write_string(mitigation_start_row, 0, 'Potential Mitigations:', bold_format)

        # ----------------------------------------------------------------------------------------------------------------
        # build list of *all* mitigations for this technique
        mits_written = []
        for each_mitigation in mit_list_for_this_technique:
            if each_mitigation not in mits_written:
                mits_written.append(each_mitigation)

        # do the write of the full mitigations list
        i = 1
        for each_mit in sorted(mits_written):
            worksheet.write_string(mitigation_start_row + i, 0, each_mit)
            try:
                if kb.get_mitigation(each_mit).get('technique') is not None: # there is a link to a technique
                    cell_str = kb.get_mitigation(each_mit).get('name')  + ' ({})'.format( kb.get_mitigation(each_mit).get('technique'))
                    worksheet.write_url(mitigation_start_row + i, 1, 'internal:{}!A1'.format(kb.get_mitigation(each_mit).get('technique')),
                                        string=cell_str,
                                        cell_format=technique_format)
                else:
                    worksheet.write_string(mitigation_start_row + i, 1, kb.get_mitigation(each_mit).get('name'), cell_format=technique_format)
            except AttributeError:
                print("Mitigation not found '{}'".format(each_mit))
                quit()
            mits_written.append(each_mit)
            i += 1

        # ----------------------------------------------------------------------------------------------------------------
        #   Write references
        # ----------------------------------------------------------------------------------------------------------------

        # build big refs dict:
        references = {}
        # References from Technique
        technique_refs = kb.get_technique(each_technique_id).get('references') or []
        for each_reference in technique_refs:
            if each_reference in references:
                if each_technique_id not in references[each_reference]:
                    references[each_reference].append(each_technique_id)
            else:
                references[each_reference] = [each_technique_id,]

        # References from weaknesses within technique
        technique_weaknesses = kb.get_technique(each_technique_id).get('weaknesses', [])
        for each_weakness_id in technique_weaknesses:
            weakness_refs = kb.get_weakness(each_weakness_id).get('references') or []
            for each_reference in weakness_refs:
                if each_reference in references:
                    if each_weakness_id not in references[each_reference]:
                        references[each_reference].append(each_weakness_id)
                else:
                    references[each_reference] = [each_weakness_id, ]

        # References from mitigations within technique
        tech_mits = mits_written
        for each_mit_id in tech_mits:
            mitigation_refs = kb.get_mitigation(each_mit_id).get('references') or []
            for each_reference in mitigation_refs:
                if each_reference in references:
                    if each_mit_id not in references[each_reference]:
                        references[each_reference].append(each_mit_id)
                else:
                    references[each_reference] = [each_mit_id,]


        # write the header
        refs_start = mitigation_start_row + i + 2
        worksheet.write_string(refs_start, 0, 'References:', bold_format)
        i = 0

        # write the actual references, with indication as to whether they came from T, E or M
        for each_reference in references:
            # worksheet.setrow(refs_start+i+1, 100)
            worksheet.merge_range("B" + str(refs_start+i+1) + ":H" + str(refs_start+i+1), "")
            worksheet.write_string(refs_start + i, 1, each_reference, cell_format=technique_format)
            worksheet.write_string(refs_start + i, 8, str(references.get(each_reference)), cell_format=technique_format)
            i += 1
    print("- all individual techniques worksheets updated")

    workbook.close()
