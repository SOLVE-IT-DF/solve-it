import json
import os
import logging
import sys
import importlib.util
from pathlib import Path


def get_extension_config(project_root):
    """
    Loads the extension_configuration file from the extension_data folder. 

    Returns the config information as a dictionary. 
    """
    extension_data_path = os.path.join(project_root, 'extension_data')
    extension_config_path = os.path.join(extension_data_path, 'extension_config.json')

    if os.path.exists(extension_config_path):
        f = open(os.path.join(extension_data_path, 'extension_config.json'))
        extension_config = json.loads(f.read())
        return extension_config
    else:
        return None


def resolve_extension_path(extension_path, project_root):
    """Resolve extension path, trying absolute then relative to extension_data.

    Returns the resolved path, or exits with error if not found.
    """
    # try direct access to path in case it is an absolute path
    if os.path.exists(extension_path):
        return extension_path
    # try assuming it is a relative path in the extension_data folder
    elif os.path.exists(os.path.join(project_root, 'extension_data', extension_path)):
        return os.path.join(project_root, 'extension_data', extension_path)
    else:
        logging.error(f'Extension path {extension_path} could not be found, exiting')
        sys.exit(-1)


def load_module_from_path(module_path, module_name="temp_import"):
    """Dynamically load a Python module from a file path.

    Returns the loaded module object.
    """
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_extension_module(extension_folder, project_root):
    """Load an extension module from its folder path.

    Args:
        extension_folder: The folder path from extension config (absolute or relative)
        project_root: The project root directory

    Returns:
        The loaded extension module object
    """
    logging.debug(f'extension path listed in config: {extension_folder}')

    workable_path = resolve_extension_path(extension_folder, project_root)
    extension_code_path = os.path.join(workable_path, 'extension_code.py')

    if os.path.exists(extension_code_path):
        return load_module_from_path(extension_code_path)
    else:
        logging.error(f'Extension code not found at {extension_code_path} ({os.path.abspath(extension_code_path)})')
        sys.exit(-1)


def add_markdown_to_main_page():
    logging.debug('Called solve-it-x main markdown code')    

    project_root = Path(__file__).parent.parent
    extension_config = get_extension_config(project_root)

    if extension_config is None:
        return ""

    total_markdown_to_add = ""

    for each_extension in extension_config.get('extensions'):
        extension_folder = extension_config.get('extensions').get(each_extension).get('folder_path')

        extension_module = load_extension_module(extension_folder, project_root)

        if hasattr(extension_module, 'get_markdown_generic'):
            total_markdown_to_add += extension_module.get_markdown_generic()

    return total_markdown_to_add



def add_markdown_to_technique(t_id):
    logging.debug('Called solve-it-x technique markdown code')    

    project_root = Path(__file__).parent.parent
    extension_config = get_extension_config(project_root)

    if extension_config is None:
        return ""

    total_markdown_to_add = ""

    for each_extension in extension_config.get('extensions'):
        extension_folder = extension_config.get('extensions').get(each_extension).get('folder_path')

        extension_module = load_extension_module(extension_folder, project_root)

        if hasattr(extension_module, 'get_markdown_for_technique'):
            total_markdown_to_add += extension_module.get_markdown_for_technique(t_id)

    return total_markdown_to_add



def add_markdown_to_weakness(w_id):
    return ""


def add_markdown_to_mitigation(m_id):
    return ""

def add_html_to_main_page():
    return ""

def add_html_to_technique(t_id):
    return ""

def add_html_to_weakness(w_id):
    return ""

def add_html_to_mitigation(m_id):
    return ""


def edit_excel_technique(t_id, workbook, worksheet, start_row):
    logging.debug('Called solve-it-x technique Excel code')    

    project_root = Path(__file__).parent.parent
    extension_config = get_extension_config(project_root)

    if extension_config is None:
        return worksheet

    if len(extension_config.get('extensions')) > 0:
        bold_format2 = workbook.add_format()
        bold_format2.set_bold()
        bold_format2.set_text_wrap()
        worksheet.write_string(start_row, 0, "SOLVE-IT-X:", cell_format=bold_format2)

    for each_extension in extension_config.get('extensions'):
        extension_folder = extension_config.get('extensions').get(each_extension).get('folder_path')

        extension_module = load_extension_module(extension_folder, project_root)

        if hasattr(extension_module, 'get_excel_for_technique'):
            worksheet = extension_module.get_excel_for_technique(t_id, worksheet, start_row+2)

    return worksheet


