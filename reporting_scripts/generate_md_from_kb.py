import sys
import os
import argparse
import logging
import re
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library import KnowledgeBase, SOLVEITDataError
import solve_it_library.solve_it_x as solve_it_x
import extension_data.global_solveit_config as global_solveit_config


def main():
    """Command-line entry point for the script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate a Markdown version of the SOLVE-IT knowledge base")
    parser.add_argument('-o', action='store', type=str, dest='output_file',
                        help="output path for markdown file.")
    args = parser.parse_args()


    # Replace technique organisation configuration file here if needed
    config_file = 'solve-it.json'

    # Calculate the path to the solve-it directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    solve_it_root = os.path.dirname(script_dir)  # Go up from reporting_scripts to solve-it root
    
    try:
        kb = KnowledgeBase(solve_it_root, config_file)
    except SOLVEITDataError as e:
        logging.error(f"Error loading SOLVE-IT knowledge base, exiting.")
        sys.exit(-1)

    print("Using configuration file: {}".format(config_file))    

    # Check for extensions and display information about them
    extension_config = solve_it_x.get_extension_config(solve_it_root)
    if extension_config is not None:        
        
        # Lists any of the built-in fields that are set to not be displayed
        if 'technique_fields' in extension_config:
            for each_visibility_setting in extension_config.get('technique_fields'):
                if extension_config.get('technique_fields').get(each_visibility_setting) is False:
                    print(f"- config: field '{each_visibility_setting}' display set to false")
        else:
            print('Config file in incorrect format (no technique_fields field)')
            sys.exit(-1)

        # Lists any extensions that are in use
        extension_dict = extension_config.get('extensions')
        if len(extension_dict) > 0:
            print("Extensions configured:")
            for each_extension_name in extension_dict:
                each_extension = extension_dict.get(each_extension_name)
                print(f" - {each_extension_name} ({each_extension.get('description')}, path={each_extension.get('folder_path')})")
        else:
            print("No extensions configured")
    else:
        print("No extensions configured")


    # Determine and if necessary create output folder path
    if args.output_file is not None:
        out_folder = os.path.dirname(args.output_file)
        if not os.path.exists(out_folder):
            os.makedirs(out_folder)
        outpath = args.output_file
    else:
        out_folder = 'output'
        if not os.path.exists(out_folder):
            os.mkdir(out_folder)
        outpath = os.path.join(out_folder, 'solve-it.md')

    # Create subfolder for technique, weakness, and mitigation files
    os.makedirs(os.path.join(out_folder, "md_content"), exist_ok=True)

    # This section does the MD generation:

    create_main_markdown(kb, outpath)
    
    write_all_technique_files(kb, outpath, extension_config)
    write_all_weakness_files(kb, outpath, extension_config)

    print(f"Markdown file created at: {outpath}")

    return 0


def objective_name_to_friendly_id(name):
    name = re.sub(' ', '-', name)
    name = re.sub(',._\'', '', name)
    name = name.lower().strip()
    return name


def get_weakness_categories(weakness):
    """
    Returns a formatted string of weakness categories that are marked with 'x' or 'X'.

    Args:
        weakness: A weakness dictionary containing category fields

    Returns:
        A formatted string like "INCOMP, MISINT" or empty string if no categories are marked
    """
    # Note: The fields in the dict use underscores (INAC_EX) due to Pydantic field names,
    # but we display them with hyphens (INAC-EX) for consistency with the JSON files
    category_field_mapping = {
        'INCOMP': 'INCOMP',
        'INAC_EX': 'INAC-EX',
        'INAC_AS': 'INAC-AS',
        'INAC_ALT': 'INAC-ALT',
        'INAC_COR': 'INAC-COR',
        'MISINT': 'MISINT'
    }
    marked_categories = []

    for field_name, display_name in category_field_mapping.items():
        value = weakness.get(field_name, '')
        if value and value.lower() == 'x':
            marked_categories.append(display_name)

    if marked_categories:
        return f"{', '.join(marked_categories)}"
    return ""


def create_main_markdown(kb, outpath):
    """Create the markdown file."""

    with open(outpath, 'w', encoding='utf-8') as mdfile:
        # Write the header
        mdfile.write("# SOLVE-IT Knowledge Base\n\n")
        mdfile.write("This is a generated markdown version of the SOLVE-IT knowledge base. See [GitHub repository](https://github.com/SOLVE-IT-DF/solve-it) for more details.\n\n")

        # Add any prefix from extensions        
        mdfile.write(solve_it_x.add_markdown_to_main_page())
        mdfile.write("\n\n")
        

        # Write table of contents
        mdfile.write(f"# Objective Index\n" )
        for objective in kb.list_objectives():
            mdfile.write(f"- [{objective.get('name')}](#{objective_name_to_friendly_id(objective.get('name'))})\n" )
        mdfile.write(f"\n" )

        mdfile.write(f"# Objectives and Techniques\n" )

        # Write each objective and its techniques
        for objective in kb.list_objectives():
            mdfile.write(f'<a id="{objective_name_to_friendly_id(objective.get('name'))}"></a>\n')
            mdfile.write(f"### {objective.get('name')}\n" )
            mdfile.write(f"*{objective.get('description')}*\n\n")

            for each_technique_id in sorted(objective.get('techniques')):
                technique = kb.get_technique(each_technique_id)
                if technique is None:
                    logging.error(f"Technique {each_technique_id} not found in knowledge base, exiting")
                    sys.exit(-1)

                solveitx_technique_content_suffix = solve_it_x.add_markdown_to_technique_preview_suffix(each_technique_id)

                mdfile.write(f"- {global_solveit_config.get_technique_prefix(kb, each_technique_id)}[{each_technique_id} - {technique.get('name')}](md_content/{each_technique_id}.md){global_solveit_config.get_technique_suffix(kb, each_technique_id)}{solveitx_technique_content_suffix}\n" )
                for each_sub_technique_id in technique.get('subtechniques'):
                    sub_t = kb.get_technique(each_sub_technique_id)
                    if sub_t is None:
                        logging.error(f'Subtechnique {each_sub_technique_id} not found (referred to from {each_technique_id})')
                        sys.exit(-1)

                    mdfile.write(f"    - {global_solveit_config.get_technique_prefix(kb, each_sub_technique_id)}[{each_sub_technique_id} - {sub_t.get('name')}](md_content/{each_sub_technique_id}.md){global_solveit_config.get_technique_suffix(kb, each_technique_id)}\n" )

        # Write footer with generation timestamp
        generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mdfile.write(f"\n\n---\n\n")
        mdfile.write(f"*Markdown generated: {generation_time}*\n")


def write_all_technique_files(kb, outpath, extension_config):
    generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for each_technique_id in kb.list_techniques():
        technique = kb.get_technique(each_technique_id)
        if technique is None:
            logging.error(f"Technique {each_technique_id} not found in knowledge base, exiting")
            sys.exit(-1)
        technique_filepath = os.path.join(os.path.dirname(outpath), 'md_content', each_technique_id + '.md')
        with open(technique_filepath, 'w', encoding='utf-8') as technique_md_file:
            technique_md_file.write(f"[< back to main](../solve-it.md)\n")
            technique_md_file.write(f"# {each_technique_id}\n\n")
            
            if extension_config is not None and extension_config.get('technique_fields').get('id'):
                technique_md_file.write(f"**ID:** {technique.get('id')}\n\n")
            if extension_config is not None and extension_config.get('technique_fields').get('name'):
                technique_md_file.write(f"**Name:** {technique.get('name')}\n\n")
            if extension_config is not None and extension_config.get('technique_fields').get('description'):
                technique_md_file.write(f"**Description:**\n\n")            
                technique_md_file.write(f"{technique.get('description')}\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('synonyms'):
                technique_md_file.write(f"**Synonyms:**\n\n")
                for each_synonym in technique.get('synonyms'):
                    technique_md_file.write(f"{each_synonym}, ")
                technique_md_file.write("\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('details'):
                technique_md_file.write(f"**Details:**\n\n")
                technique_md_file.write(f"{technique.get('details')}\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('subtechniques'):
                technique_md_file.write(f"**Subtechniques:**\n\n")
                for each_sub_technique_id in technique.get('subtechniques'):
                    sub_t = kb.get_technique(each_sub_technique_id)
                    if sub_t is None:
                        logging.error(f'Subtechnique {each_sub_technique_id} not found (referred to from {each_technique_id})')
                        sys.exit(-1)

                    technique_md_file.write(f"- [{each_sub_technique_id} - {sub_t.get('name')}]({each_sub_technique_id}.md)\n")
                technique_md_file.write(f"\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('examples'):
                technique_md_file.write(f"**Examples:**\n\n")
                for each_example in technique.get('examples'):
                    technique_md_file.write(f"- {each_example}\n")
                technique_md_file.write(f"\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('CASE_output_classes'):
                technique_md_file.write(f"**CASE Output Classes:**\n\n")
                for each_case_class in technique.get('CASE_output_classes'):
                    technique_md_file.write(f"    - {each_case_class}\n")
                technique_md_file.write(f"\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('weaknesses'):
                technique_md_file.write(f"**Potential weaknesses and potential mitigations:**\n\n")
                for weakness_id in technique.get('weaknesses'):
                    weakness = kb.get_weakness(weakness_id)
                    if weakness is None:
                        logging.error(f"Weakness {weakness_id} not found (referred to from {each_technique_id})")
                        sys.exit(-1)

                    categories_str = get_weakness_categories(weakness)

                    solveitx_weakness_content_prefix = solve_it_x.add_markdown_to_weakness_preview_prefix(weakness_id)
                    solveitx_weakness_content_suffix = solve_it_x.add_markdown_to_weakness_preview_suffix(weakness_id)                    

                    technique_md_file.write(f"- {solveitx_weakness_content_prefix}[{weakness_id}]({weakness_id}.md): {weakness.get('name')} _({categories_str})_{solveitx_weakness_content_suffix}\n")
                    
                    # This adds all the mitigations
                    for each_mit in weakness.get('mitigations'):
                        mitigation = kb.get_mitigation(each_mit)
                        if mitigation is None:
                            logging.error(f'Mitigation {each_mit} not found (referred to from weakness {weakness_id})')
                            sys.exit(-1)
                        if mitigation.get('technique') is None:
                            technique_md_file.write(f"    - {each_mit}: {mitigation.get('name')} \n")
                        else:
                            technique_md_file.write(f"    - {each_mit}: {mitigation.get('name')} ([{mitigation.get('technique')}]({mitigation.get('technique') +'.md'}))\n")
                technique_md_file.write(f"\n\n")

            if extension_config is not None and extension_config.get('technique_fields').get('references'):
                technique_md_file.write(f"**References:**\n\n")
                for each_reference in technique.get('references'):
                    technique_md_file.write(f"- {each_reference}\n")
                technique_md_file.write(f"\n\n")

            # Add content from SOLVE-IT Extensions
            technique_md_file.write(f"{solve_it_x.add_markdown_to_technique(each_technique_id)}")

            # Write footer with generation timestamp
            technique_md_file.write(f"\n\n---\n\n")
            technique_md_file.write(f"*Markdown generated: {generation_time}*\n")
      

def write_all_weakness_files(kb, outpath, extension_config):
    generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for each_weakness_id in kb.list_weaknesses():
        weakness = kb.get_weakness(each_weakness_id)
        if weakness is None:
            logging.error(f"Weakness {each_weakness_id} not found in knowledge base, exiting")
            sys.exit(-1)
        weakness_filepath = os.path.join(os.path.dirname(outpath), 'md_content', each_weakness_id + '.md')
        with open(weakness_filepath, 'w', encoding='utf-8') as weakness_md_file:
            weakness_md_file.write(f"[< back to main](../solve-it.md)\n")
            weakness_md_file.write(f"# {each_weakness_id}\n\n")
            weakness_md_file.write(f"**Name:** {weakness.get('name')}\n\n")            
            weakness_md_file.write(f"**Weakness classes:** {get_weakness_categories(weakness)}\n\n")
            weakness_md_file.write(f"**Details:** {weakness.get('details')}\n\n")

            # This adds all the mitigations
            weakness_md_file.write(f"**Potential mitigations:**\n\n")
            for each_mit in weakness.get('mitigations'):
                mitigation = kb.get_mitigation(each_mit)
                if mitigation is None:
                    logging.error(f'Mitigation {each_mit} not found (referred to from weakness {each_weakness_id})')
                    sys.exit(-1)
                if mitigation.get('technique') is None:
                    weakness_md_file.write(f"- {each_mit}: {mitigation.get('name')} \n")
                else:
                    weakness_md_file.write(f"- {each_mit}: {mitigation.get('name')} ([{mitigation.get('technique')}]({mitigation.get('technique') +'.md'}))\n")
            weakness_md_file.write(f"\n\n") 

            # This adds all the references
            weakness_md_file.write(f"**References:**\n\n")
            for each_reference in weakness.get('references'):
                weakness_md_file.write(f"- {each_reference}\n")
            weakness_md_file.write(f"\n\n")

            # Add content from SOLVE-IT Extensions
            weakness_md_file.write(f"{solve_it_x.add_markdown_to_weakness(each_weakness_id)}")

            # Write footer with generation timestamp
            weakness_md_file.write(f"\n\n---\n\n")
            weakness_md_file.write(f"*Markdown generated: {generation_time}*\n")


if __name__ == "__main__":
    main()
