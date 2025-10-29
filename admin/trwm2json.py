import os
import argparse
import csv
import json
import io
import logging
import sys
import re

logging.basicConfig(encoding='utf-8', level=logging.INFO)


def process_weakness_mitigations(weakness_row, headers, mitigations_list):
    """Process mitigation columns in a weakness row and return list of mitigation IDs"""
    mitigation_ids = []
    
    # Find mitigation columns (columns that start with "Mitigation")
    mitigation_columns = []
    for i, header in enumerate(headers):
        if 'mitigation' in header.lower():
            mitigation_columns.append(i)
    
    logging.debug(f"Found mitigation columns: {[headers[i] for i in mitigation_columns]}")
    
    # Process each mitigation column
    for col_index in mitigation_columns:
        if col_index < len(weakness_row):
            mitigation_name = weakness_row[col_index].strip()
            if mitigation_name:  # Skip empty cells
                mitigation_id = find_mitigation_id_by_name(mitigation_name, mitigations_list)
                if mitigation_id:
                    mitigation_ids.append(mitigation_id)
                    logging.debug(f"Mapped '{mitigation_name}' -> {mitigation_id}")
                else:
                    logging.warning(f"Could not find mitigation ID for: '{mitigation_name}'")
    
    return mitigation_ids


def find_mitigation_id_by_name(mitigation_name, mitigations_list):
    """Search for a mitigation by name and return its ID"""
    if not mitigation_name or not mitigation_name.strip():
        return None
    
    search_name = mitigation_name.strip().lower()
    
    for mitigation in mitigations_list:
        if 'name' in mitigation and 'id' in mitigation:
            mitigation_name_lower = mitigation['name'].strip().lower()
            if mitigation_name_lower == search_name:
                logging.debug(f"Found mitigation '{mitigation_name}' -> ID: {mitigation['id']}")
                return mitigation['id']
    
    logging.debug(f"Mitigation '{mitigation_name}' not found")
    return None


def parse_field_data(field_name, data):
    """Parse field data using JSON -> CSV -> Plain text priority"""
    # check if field is already json:
    try:
        decoded_json = json.loads(data)
        logging.debug(f"decoded {field_name} as JSON")
        # For reference fields, ensure we return a list even if JSON is a single string
        if isinstance(decoded_json, str):
            return [decoded_json]
        else:
            return decoded_json
    except json.JSONDecodeError:
        logging.debug(data)
        # Check if it's simple text in quotes (single quoted field with no CSV separators)
        # Use regex to detect multiple quoted CSV fields separated by comma and optional whitespace
        csv_pattern = r'"[^"]*",\s*"[^"]*"'
        if data.strip().startswith('"') and data.strip().endswith('"') and not re.search(csv_pattern, data):
            # Single quoted field - return as single item list 
            if data.strip().strip('"'):
                result = [data.strip().strip('"')]             
            else:
                result = []
            logging.debug(f"decoded {field_name} as single quoted CSV")
            return result

        # Then try CSV decoding        
        try:
            csv_reader = csv.reader(io.StringIO(data), delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
            csv_rows = list(csv_reader)
            csv_row = []
            for row in csv_rows:
                csv_row.extend(row)
            # If we get multiple fields, it's CSV
            logging.debug(f"trying to decode {field_name} as CSV")

            if len(csv_row) > 1:
                result = [item.strip() for item in csv_row if item.strip()]
                logging.debug(f"decoded {field_name} as CSV")
                return result
            else:
                # Single field or not CSV, continue to text processing
                raise StopIteration
        except (StopIteration, csv.Error):
            # not CSV, return as plain text
            logging.debug(f"decoding {field_name} as plain text")
            return [data]


def technique_tsv_to_json(tsv_path):
    result = {}
    
    with open(tsv_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split('\t', 1)  # Split on first tab only
            if len(parts) >= 2:
                field_name = parts[0].strip().rstrip(':')
                data = parts[1].strip()
                
                fields_to_process_as_lists = ['synonyms', 'subtechniques', 'examples', 'references', 'case_output_classes']
                if field_name.lower() in fields_to_process_as_lists:                    
                    result[field_name] = parse_field_data(field_name, data)                        
                else:
                    result[field_name] = data
    
    # adds in any missing fields
    if "id" not in result:
        result["id"] = "Txxxx"

    if "subtechniques" not in result:
        result["subtechniques"] = []

    # Validate that technique ID is not blank or default placeholder
    if not result.get('id') or result['id'].strip() == '' or result['id'] == 'Txxxx':
        print(f"ERROR: Technique ID is blank in file: {tsv_path}", file=sys.stderr)
        sys.exit(1)

    return result


def mitigations_tsv_to_json(tsv_path):
    mitigations = []
    headers = []
    
    with open(tsv_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t', quoting=csv.QUOTE_NONE)
        
        # Read header row
        headers = next(reader)
        headers = [header.strip() for header in headers]
        logging.debug(f"Headers: {headers}")
        
        # Process each data row
        for row in reader:
            if len(row) >= len(headers):
                mitigation = {}
                for i, header in enumerate(headers):
                    data = row[i].strip() if i < len(row) else ""
                    
                    fields_to_process_as_lists = ['references']
                    if header.lower() in fields_to_process_as_lists:
                        if data:
                            mitigation[header] = parse_field_data(header, data)
                        else:
                            mitigation[header] = []
                    else:
                        # Store as plain text for other fields
                        # Skip empty technique fields
                        if header.lower() == 'technique' and not data:
                            continue
                        mitigation[header] = data
                        logging.debug(f"storing {header} as plain text")
                
                # Validate that mitigation ID is not blank
                if not mitigation.get('id') or mitigation['id'].strip() == '':
                    print(f"ERROR: Mitigation ID is blank in file: {tsv_path}", file=sys.stderr)
                    sys.exit(1)
                
                logging.debug(f"Finished processing {mitigation['id']}")
                mitigations.append(mitigation)
    
    return mitigations
    

def weaknesses_tsv_to_json(tsv_path, mitigations_list=None):
    weaknesses = []
    flag_columns = ['INCOMP', 'INAC-EX', 'INAC-ALT', 'INAC-AS', 'INAC-COR', 'MISINT']
    
    with open(tsv_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter='\t', quoting=csv.QUOTE_NONE)
        
        # Read header row
        headers = next(reader)
        headers = [header.strip() for header in headers]
        logging.debug(f"Weakness headers: {headers}")
        
        # Process each data row
        for row in reader:
            if len(row) >= 2:
                # Check for blank IDs, but allow placeholder rows
                id_field = row[0].strip()
                if not id_field or id_field == '-':
                    # Check if this is a placeholder row (name field is also empty/dash)
                    name_field = row[1].strip() if len(row) > 1 else ""
                    if not name_field or name_field == '-':
                        continue  # Skip placeholder rows
                    else:
                        # This has a blank ID but non-empty name - this is an error
                        print(f"ERROR: Weakness ID is blank in file: {tsv_path}", file=sys.stderr)
                        sys.exit(1)
                
                weakness = {}
                
                # Process each column based on header
                for i, header in enumerate(headers):
                    if i >= len(row):
                        continue
                        
                    data = row[i].strip()
                    
                    fields_to_process_as_lists = ['references']
                    if header == 'id':
                        weakness['id'] = data
                        logging.debug(f"storing id as plain text: {data}")
                    elif header == 'name':
                        weakness['name'] = data
                        logging.debug(f"storing name as plain text: {data}")
                    elif header in flag_columns:
                        # Flag columns: "X" becomes "x", empty becomes ""
                        weakness[header] = data.lower() if data.upper() == 'X' else ""
                        logging.debug(f"storing {header} flag: {weakness[header]}")
                    elif header.lower() in fields_to_process_as_lists:
                        # Use parse_field_data for list fields
                        if data:
                            weakness[header] = parse_field_data(header, data)
                        else:
                            weakness[header] = []
                    # Skip Summary and individual Mitigation columns - we'll process them separately
                
                # Process mitigation columns and add mitigations field
                if mitigations_list:
                    weakness['mitigations'] = process_weakness_mitigations(row, headers, mitigations_list)
                else:
                    weakness['mitigations'] = []
                
                if weakness:  # Only add if we have data
                    weaknesses.append(weakness)
    
    return weaknesses





def main():
    parser = argparse.ArgumentParser(description='Convert TRWM TSV files to JSON format')
    
    parser.add_argument('technique_tsv', 
                       help='Path to the technique.tsv file')
    parser.add_argument('weaknesses_tsv', 
                       help='Path to the weaknesses.tsv file')  
    parser.add_argument('mitigations_tsv', 
                       help='Path to the mitigations.tsv file')
    parser.add_argument('-o', '--output', 
                       default='.', 
                       help='Output folder (default: current directory)')
    
    args = parser.parse_args()
    
    print("Using:")
    print(f"Technique TSV: {args.technique_tsv}")
    print(f"Weaknesses TSV: {args.weaknesses_tsv}")
    print(f"Mitigations TSV: {args.mitigations_tsv}")
    
    
    technique_json = technique_tsv_to_json(args.technique_tsv)
    print("Converted technique data:")
    print(json.dumps(technique_json, indent=2))
    
    mitigations_json = mitigations_tsv_to_json(args.mitigations_tsv)
    print("Converted mitigation data:")
    print(json.dumps(mitigations_json, indent=2))
    
    weaknesses_json = weaknesses_tsv_to_json(args.weaknesses_tsv, mitigations_json)
    print("Converted weakness data:")
    print(json.dumps(weaknesses_json, indent=2))
    
    # Add weaknesses field to technique with all weakness IDs
    weakness_ids = [weakness.get('id') for weakness in weaknesses_json if weakness.get('id')]
    technique_json['weaknesses'] = weakness_ids
    print(f"\nAdded {len(weakness_ids)} weakness IDs to technique: {weakness_ids}")
    
    # Write JSON files
    print("\nWriting JSON files...")
    
    # Write technique JSON file using the technique ID
    technique_id = technique_json.get('id', 'unknown')
    technique_filename = f"{technique_id}.json"
    technique_path = os.path.join(args.output, technique_filename)
    
    with open(technique_path, 'w', encoding='utf-8') as output_file:
        json.dump(technique_json, output_file, indent=2)
    print(f"Technique JSON saved to: {technique_path}")
    
    # Write individual mitigation JSON files
    print(f"Writing {len(mitigations_json)} mitigation files...")
    for mitigation in mitigations_json:
        mitigation_id = mitigation.get('id', 'unknown')
        mitigation_filename = f"{mitigation_id}.json"
        mitigation_path = os.path.join(args.output, mitigation_filename)
        
        with open(mitigation_path, 'w', encoding='utf-8') as output_file:
            json.dump(mitigation, output_file, indent=2)
        print(f"  Mitigation {mitigation_id} saved to: {mitigation_filename}")
    
    # Write individual weakness JSON files
    print(f"Writing {len(weaknesses_json)} weakness files...")
    for weakness in weaknesses_json:
        weakness_id = weakness.get('id', 'unknown')
        weakness_filename = f"{weakness_id}.json"
        weakness_path = os.path.join(args.output, weakness_filename)
        
        with open(weakness_path, 'w', encoding='utf-8') as output_file:
            json.dump(weakness, output_file, indent=2)
        print(f"  Weakness {weakness_id} saved to: {weakness_filename}")
    
    print(f"\nAll files written to output directory: {args.output}")




    # # Write JSON to file using the technique ID
    # technique_id = technique_json.get('id', 'unknown')
    # output_filename = f"{technique_id}.json"
    # output_path = os.path.join(args.output, output_filename)
    
    # with open(output_path, 'w', encoding='utf-8') as output_file:
    #     json.dump(technique_json, output_file, indent=2)
    
    # print(f"\nTechnique JSON saved to: {output_path}")


    


if __name__ == '__main__':
    main()