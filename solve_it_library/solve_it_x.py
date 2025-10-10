import json
import os
import logging
import sys
import importlib.util
from pathlib import Path


def get_extension_config(project_root):    
    extension_data_path = os.path.join(project_root, 'extension_data')
    extension_config_path = os.path.join(extension_data_path, 'extension_config.json')
    
    if os.path.exists(extension_config_path):
        f = open(os.path.join(extension_data_path, 'extension_config.json'))
        extension_config = json.loads(f.read())
        return extension_config
    else:
        return None


def add_markdown_to_technique(id):
    logging.debug('Called solve-it-x markdown code')    

    project_root = Path(__file__).parent.parent
    extension_config = get_extension_config(project_root)

    if extension_config is None:
        return ""

    total_markdown_to_add = ""

    for each_extension in extension_config.get('extensions'):  
        extension_folder = extension_config.get('extensions').get(each_extension).get('folder_path')
        extension_description = extension_config.get('extensions').get(each_extension).get('description')

        each_extension_path = extension_folder
        logging.debug('f"extension path listed in config: {each_extension_path}"')
        
        # try direct access to path in case it is an absolute path
        if os.path.exists(each_extension_path):
            workable_path = each_extension_path
        # try assuming it is a relative path in the extension_data folder
        elif os.path.exists(os.path.join(project_root, 'extension_data', each_extension_path)):            
            workable_path = os.path.join(project_root, 'extension_data', each_extension_path)
        else:            
            logging.error(f'Extension path {each_extension_path} could not be found, exiting')
            sys.exit(-1)

        extension_code_path = os.path.join(workable_path, 'extension_code.py')

        if os.path.exists(extension_code_path):
            spec = importlib.util.spec_from_file_location(f"temp_import", extension_code_path)
            extension_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(extension_module)

            if hasattr(extension_module, 'get_markdown_for_technique'):
                total_markdown_to_add += (extension_module.get_markdown_for_technique(id))
            
        else:
            logging.error(f'Extension code not found at {extension_code_path} ({os.path.abspath(extension_code_path)})')
            sys.exit(-1)

    return total_markdown_to_add


def add_html():
    return ""


def edit_excel():
    pass

