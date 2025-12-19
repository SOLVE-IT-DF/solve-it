import sys
import os
import argparse
import logging
import re
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from solve_it_library import KnowledgeBase, SOLVEITDataError


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

    # Display information about configured extensions
    kb.display_extension_info()

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
    write_all_weakness_files(kb, outpath)
    write_all_mitigation_files(kb, outpath)

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
        mdfile.write(kb.add_markdown_to_main_page())
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

                solveitx_technique_content_suffix = kb.add_markdown_to_technique_preview_suffix(each_technique_id)

                mdfile.write(f"- {kb.get_technique_prefix(each_technique_id)}[{each_technique_id} - {technique.get('name')}](md_content/{each_technique_id}.md){kb.get_technique_suffix(each_technique_id)}{solveitx_technique_content_suffix}\n" )
                for each_sub_technique_id in technique.get('subtechniques'):
                    sub_t = kb.get_technique(each_sub_technique_id)
                    if sub_t is None:
                        logging.error(f'Subtechnique {each_sub_technique_id} not found (referred to from {each_technique_id})')
                        sys.exit(-1)

                    mdfile.write(f"    - {kb.get_technique_prefix(each_sub_technique_id)}[{each_sub_technique_id} - {sub_t.get('name')}](md_content/{each_sub_technique_id}.md){kb.get_technique_suffix(each_sub_technique_id)}\n" )

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

            if kb.should_display_field('id'):
                technique_md_file.write(f"**ID:** {technique.get('id')}\n\n")
            if kb.should_display_field('name'):
                technique_md_file.write(f"**Name:** {technique.get('name')}\n\n")

            # Display objectives/categories (including parent's objectives for subtechniques)
            objectives = kb.get_objectives_for_technique(each_technique_id)
            if objectives:
                technique_md_file.write(f"**Objective(s):** {', '.join(objectives)}\n\n")

            if kb.should_display_field('description'):
                technique_md_file.write(f"**Description:**\n\n")
                technique_md_file.write(f"{technique.get('description')}\n\n")

            if kb.should_display_field('synonyms'):
                technique_md_file.write(f"**Synonyms:**\n\n")
                for each_synonym in technique.get('synonyms'):
                    technique_md_file.write(f"{each_synonym}, ")
                technique_md_file.write("\n\n")

            if kb.should_display_field('details'):
                technique_md_file.write(f"**Details:**\n\n")
                technique_md_file.write(f"{technique.get('details')}\n\n")

            if kb.should_display_field('subtechniques'):
                technique_md_file.write(f"**Subtechniques:**\n\n")
                for each_sub_technique_id in technique.get('subtechniques'):
                    sub_t = kb.get_technique(each_sub_technique_id)
                    if sub_t is None:
                        logging.error(f'Subtechnique {each_sub_technique_id} not found (referred to from {each_technique_id})')
                        sys.exit(-1)

                    technique_md_file.write(f"- [{each_sub_technique_id} - {sub_t.get('name')}]({each_sub_technique_id}.md)\n")
                technique_md_file.write(f"\n\n")

            if kb.should_display_field('examples'):
                technique_md_file.write(f"**Examples:**\n\n")
                for each_example in technique.get('examples'):
                    technique_md_file.write(f"- {each_example}\n")
                technique_md_file.write(f"\n\n")

            if kb.should_display_field('CASE_output_classes'):
                technique_md_file.write(f"**CASE Output Classes:**\n\n")
                for each_case_class in technique.get('CASE_output_classes'):
                    technique_md_file.write(f"    - {each_case_class}\n")
                technique_md_file.write(f"\n\n")

            if kb.should_display_field('weaknesses'):
                technique_md_file.write(f"**Potential weaknesses and potential mitigations:**\n\n")
                for weakness_id in technique.get('weaknesses'):
                    weakness = kb.get_weakness(weakness_id)
                    if weakness is None:
                        logging.error(f"Weakness {weakness_id} not found (referred to from {each_technique_id})")
                        sys.exit(-1)

                    categories_str = get_weakness_categories(weakness)

                    solveitx_weakness_content_prefix = kb.add_markdown_to_weakness_preview_prefix(weakness_id)
                    solveitx_weakness_content_suffix = kb.add_markdown_to_weakness_preview_suffix(weakness_id)

                    technique_md_file.write(f"- {solveitx_weakness_content_prefix}[{weakness_id}: {weakness.get('name')}]({weakness_id}.md) _({categories_str})_{solveitx_weakness_content_suffix}\n")

                    # This adds all the mitigations
                    for each_mit in weakness.get('mitigations'):
                        mitigation = kb.get_mitigation(each_mit)
                        if mitigation is None:
                            logging.error(f'Mitigation {each_mit} not found (referred to from weakness {weakness_id})')
                            sys.exit(-1)

                        solveitx_mitigation_content_prefix = kb.add_markdown_to_mitigation_preview_prefix(each_mit)
                        solveitx_mitigation_content_suffix = kb.add_markdown_to_mitigation_preview_suffix(each_mit)

                        # Link to mitigation page, and also show related technique if present
                        if mitigation.get('technique') is None:
                            technique_md_file.write(f"    - {solveitx_mitigation_content_prefix}[{each_mit}: {mitigation.get('name')}]({each_mit}.md){solveitx_mitigation_content_suffix}\n")
                        else:
                            technique_md_file.write(f"    - {solveitx_mitigation_content_prefix}[{each_mit}: {mitigation.get('name')}]({each_mit}.md) (links to: [{mitigation.get('technique')}]({mitigation.get('technique')}.md)){solveitx_mitigation_content_suffix}\n")
                technique_md_file.write(f"\n\n")

            if kb.should_display_field('references'):
                technique_md_file.write(f"**References:**\n\n")
                for each_reference in technique.get('references'):
                    technique_md_file.write(f"- {each_reference}\n")
                technique_md_file.write(f"\n\n")

            # Add content from SOLVE-IT Extensions
            technique_md_file.write(f"{kb.add_markdown_to_technique(each_technique_id)}")

            # Write footer with generation timestamp
            technique_md_file.write(f"\n\n---\n\n")
            technique_md_file.write(f"*Markdown generated: {generation_time}*\n")
      

def write_all_weakness_files(kb, outpath):
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

            # Find and list techniques that reference this weakness
            techniques_with_weakness = []
            for technique_id in kb.list_techniques():
                technique = kb.get_technique(technique_id)
                if each_weakness_id in technique.get('weaknesses', []):
                    techniques_with_weakness.append(technique_id)

            if techniques_with_weakness:
                weakness_md_file.write(f"**Present in techniques:**\n\n")
                for technique_id in techniques_with_weakness:
                    technique = kb.get_technique(technique_id)
                    weakness_md_file.write(f"- [{technique_id}: {technique.get('name')}]({technique_id}.md)\n")
                weakness_md_file.write(f"\n\n")

            # This adds all the mitigations
            weakness_md_file.write(f"**Potential mitigations:**\n\n")
            for each_mit in weakness.get('mitigations'):
                mitigation = kb.get_mitigation(each_mit)
                if mitigation is None:
                    logging.error(f'Mitigation {each_mit} not found (referred to from weakness {each_weakness_id})')
                    sys.exit(-1)

                solveitx_mitigation_content_prefix = kb.add_markdown_to_mitigation_preview_prefix(each_mit)
                solveitx_mitigation_content_suffix = kb.add_markdown_to_mitigation_preview_suffix(each_mit)

                # Link to mitigation page, and also show related technique if present
                if mitigation.get('technique') is None:
                    weakness_md_file.write(f"- {solveitx_mitigation_content_prefix}[{each_mit}: {mitigation.get('name')}]({each_mit}.md){solveitx_mitigation_content_suffix}\n")
                else:
                    weakness_md_file.write(f"- {solveitx_mitigation_content_prefix}[{each_mit}: {mitigation.get('name')}]({each_mit}.md) (links to: [{mitigation.get('technique')}]({mitigation.get('technique')}.md)){solveitx_mitigation_content_suffix}\n")
            weakness_md_file.write(f"\n\n") 

            # This adds all the references
            weakness_md_file.write(f"**References:**\n\n")
            for each_reference in weakness.get('references'):
                weakness_md_file.write(f"- {each_reference}\n")
            weakness_md_file.write(f"\n\n")

            # Add content from SOLVE-IT Extensions
            weakness_md_file.write(f"{kb.add_markdown_to_weakness(each_weakness_id)}")

            # Write footer with generation timestamp
            weakness_md_file.write(f"\n\n---\n\n")
            weakness_md_file.write(f"*Markdown generated: {generation_time}*\n")


def write_all_mitigation_files(kb, outpath):
    generation_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for each_mitigation_id in kb.list_mitigations():
        mitigation = kb.get_mitigation(each_mitigation_id)
        if mitigation is None:
            logging.error(f"Mitigation {each_mitigation_id} not found in knowledge base, exiting")
            sys.exit(-1)
        mitigation_filepath = os.path.join(os.path.dirname(outpath), 'md_content', each_mitigation_id + '.md')
        with open(mitigation_filepath, 'w', encoding='utf-8') as mitigation_md_file:
            mitigation_md_file.write(f"[< back to main](../solve-it.md)\n")
            mitigation_md_file.write(f"# {each_mitigation_id}\n\n")
            mitigation_md_file.write(f"**Name:** {mitigation.get('name')}\n\n")
            mitigation_md_file.write(f"**Details:** {mitigation.get('details')}\n\n")

            # Add technique reference if present
            if mitigation.get('technique'):
                linked_technique = kb.get_technique(mitigation.get('technique'))
                if linked_technique:
                    mitigation_md_file.write(f"**Linked technique:** [{mitigation.get('technique')}: {linked_technique.get('name')}]({mitigation.get('technique')}.md)\n\n")
                else:
                    mitigation_md_file.write(f"**Linked technique:** [{mitigation.get('technique')}]({mitigation.get('technique')}.md)\n\n")

            # Find and list weaknesses that reference this mitigation
            weaknesses_using_mitigation = []
            for weakness_id in kb.list_weaknesses():
                weakness = kb.get_weakness(weakness_id)
                if each_mitigation_id in weakness.get('mitigations', []):
                    weaknesses_using_mitigation.append(weakness_id)

            if weaknesses_using_mitigation:
                mitigation_md_file.write(f"**Potentially mitigates:**\n\n")
                for weakness_id in weaknesses_using_mitigation:
                    weakness = kb.get_weakness(weakness_id)
                    mitigation_md_file.write(f"- [{weakness_id}: {weakness.get('name')}]({weakness_id}.md)\n")
                mitigation_md_file.write(f"\n\n")

            # Add references if present
            if mitigation.get('references'):
                mitigation_md_file.write(f"**References:**\n\n")
                for each_reference in mitigation.get('references'):
                    mitigation_md_file.write(f"- {each_reference}\n")
                mitigation_md_file.write(f"\n\n")

            # Add content from SOLVE-IT Extensions
            mitigation_md_file.write(f"{kb.add_markdown_to_mitigation(each_mitigation_id)}")

            # Write footer with generation timestamp
            mitigation_md_file.write(f"\n\n---\n\n")
            mitigation_md_file.write(f"*Markdown generated: {generation_time}*\n")


if __name__ == "__main__":
    main()
