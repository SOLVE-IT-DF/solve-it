import sys
import os
import argparse
import logging
import re
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library import KnowledgeBase, SOLVEITDataError
from solve_it_library.solve_it_x import add_markdown_to_technique, get_extension_config


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
    extension_config = get_extension_config(solve_it_root)
    if extension_config is not None:        
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
    
    write_all_technique_files(kb, outpath)

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

        # Write table of contents
        mdfile.write(f"# Objective Index\n" )
        for objective in kb.list_objectives():
            mdfile.write(f"- [{objective.get('name')}](#{objective_name_to_friendly_id(objective.get('name'))})\n" )
        mdfile.write(f"\n" )

        mdfile.write(f"# Objectives and Techniques\n" )

        # Write each tactic and its techniques
        for objective in kb.list_objectives():
            mdfile.write(f'<a id="{objective_name_to_friendly_id(objective.get('name'))}"></a>\n')
            mdfile.write(f"### {objective.get('name')}\n" )
            mdfile.write(f"*{objective.get('description')}*\n\n")

            for each_technique_id in sorted(objective.get('techniques')):
                technique = kb.get_technique(each_technique_id)
                if technique is None:
                    logging.error(f"Technique {each_technique_id} not found in knowledge base, exiting")
                    sys.exit(-1)
                mdfile.write(f"- [{each_technique_id} - {technique.get('name')}](md_content/{each_technique_id}.md)\n" )
                for each_sub_technique_id in technique.get('subtechniques'):
                    sub_t = kb.get_technique(each_sub_technique_id)
                    if sub_t is None:
                        logging.error(f'Subtechnique {each_sub_technique_id} not found (referred to from {each_technique_id})')
                        sys.exit(-1)
                    mdfile.write(f"    - [{each_sub_technique_id} - {sub_t.get('name')}](md_content/{each_sub_technique_id}.md)\n" )

        # Write footer with generation timestamp
        generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mdfile.write(f"\n\n---\n\n")
        mdfile.write(f"*Markdown generated: {generation_time}*\n")


def write_all_technique_files(kb, outpath):
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
            technique_md_file.write(f"**ID:** {technique.get('id')}\n\n")
            technique_md_file.write(f"**Name:** {technique.get('name')}\n\n")
            technique_md_file.write(f"**Description:**\n\n")
            technique_md_file.write(f"{technique.get('description')}\n\n")

            technique_md_file.write(f"**Synonyms:**\n\n")
            for each_synonym in technique.get('synonyms'):
                technique_md_file.write(f"{each_synonym}, ")
            technique_md_file.write("\n\n")

            technique_md_file.write(f"**Details:**\n\n")
            technique_md_file.write(f"{technique.get('details')}\n\n")

            technique_md_file.write(f"**Subtechniques:**\n\n")
            for each_sub_technique_id in technique.get('subtechniques'):
                sub_t = kb.get_technique(each_sub_technique_id)
                if sub_t is None:
                    logging.error(f'Subtechnique {each_sub_technique_id} not found (referred to from {each_technique_id})')
                    sys.exit(-1)
                technique_md_file.write(f"- [{each_sub_technique_id} - {sub_t.get('name')}]({each_sub_technique_id}.md)\n")
            technique_md_file.write(f"\n\n")


            technique_md_file.write(f"**Examples:**\n\n")
            for each_example in technique.get('examples'):
                technique_md_file.write(f"- {each_example}\n")
            technique_md_file.write(f"\n\n")

            technique_md_file.write(f"**CASE Output Classes:**\n\n")
            for each_case_class in technique.get('CASE_output_classes'):
                technique_md_file.write(f"    - {each_case_class}\n")
            technique_md_file.write(f"\n\n")

            technique_md_file.write(f"**Potential weaknesses and mitigations:**\n\n")
            for weakness_id in technique.get('weaknesses'):
                weakness = kb.get_weakness(weakness_id)
                if weakness is None:
                    logging.error(f"Weakness {weakness_id} not found (referred to from {each_technique_id})")
                    sys.exit(-1)

                categories_str = get_weakness_categories(weakness)

                technique_md_file.write(f"- {weakness_id}: {weakness.get('name')} _({categories_str})_\n")
                
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

            technique_md_file.write(f"**References:**\n\n")
            for each_reference in technique.get('references'):
                technique_md_file.write(f"- {each_reference}\n")
            technique_md_file.write(f"\n\n")

            # Add content from SOLVE-IT Extensions
            technique_md_file.write(f"{add_markdown_to_technique(each_technique_id)}")

            # Write footer with generation timestamp
            technique_md_file.write(f"\n\n---\n\n")
            technique_md_file.write(f"*Markdown generated: {generation_time}*\n")
      
    

if __name__ == "__main__":
    main()
