import unittest
import tempfile
import os
import sys
print(os.path.abspath(os.path.curdir))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'reporting_scripts'))
from trwm2json import parse_field_data, find_mitigation_id_by_name, technique_tsv_to_json, mitigations_tsv_to_json, weaknesses_tsv_to_json, process_weakness_mitigations


class TestParseFieldData(unittest.TestCase):
    """Test the parse_field_data function"""
    
    def test_json_parsing(self):
        """Test that valid JSON is parsed correctly"""
        result = parse_field_data("synonyms", '["syn1", "syn2", "syn3"]')
        self.assertEqual(result, ["syn1", "syn2", "syn3"])
    
    def test_csv_parsing(self):
        """Test that CSV with quotes is parsed correctly"""
        result = parse_field_data("references", '"Ref 1, details", "Ref 2, details"')
        self.assertEqual(result, ["Ref 1, details", "Ref 2, details"])
    
    def test_csv_with_trailing_comma(self):
        """Test CSV with trailing comma (empty strings filtered out)"""
        result = parse_field_data("examples", '"Example 1", "Example 2", ')
        self.assertEqual(result, ["Example 1", "Example 2"])
    
    def test_plain_text(self):
        """Test that plain text is returned as-is"""
        result = parse_field_data("references", "single reference")
        self.assertEqual(result, ["single reference"])
    
    def test_single_quoted_field(self):
        """Test single quoted field returns as plain text"""
        result = parse_field_data("references", '"ref single"')
        self.assertEqual(result, ["ref single"])


class TestFindMitigationIdByName(unittest.TestCase):
    """Test the find_mitigation_id_by_name function"""
    
    def setUp(self):
        """Set up test data"""
        self.mitigations = [
            {"id": "M1027", "name": "Dual tool verification", "technique": ""},
            {"id": "M1050", "name": "Manual verification of relevant data", "technique": ""},
            {"id": "Mx001", "name": "New mitigation 1", "technique": "T1234"},
            {"id": "MX002", "name": "New mitigation 2", "technique": ""}
        ]
    
    def test_exact_match(self):
        """Test exact name match"""
        result = find_mitigation_id_by_name("Dual tool verification", self.mitigations)
        self.assertEqual(result, "M1027")
    
    def test_case_insensitive_match(self):
        """Test case insensitive matching"""
        result = find_mitigation_id_by_name("DUAL TOOL VERIFICATION", self.mitigations)
        self.assertEqual(result, "M1027")
        
        result = find_mitigation_id_by_name("new mitigation 1", self.mitigations)
        self.assertEqual(result, "Mx001")
    
    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly"""
        result = find_mitigation_id_by_name("  Dual tool verification  ", self.mitigations)
        self.assertEqual(result, "M1027")
    
    def test_not_found(self):
        """Test that None is returned when mitigation not found"""
        result = find_mitigation_id_by_name("Non-existent mitigation", self.mitigations)
        self.assertIsNone(result)
    
    def test_empty_input(self):
        """Test that empty/None input returns None"""
        result = find_mitigation_id_by_name("", self.mitigations)
        self.assertIsNone(result)
        
        result = find_mitigation_id_by_name(None, self.mitigations)
        self.assertIsNone(result)
        
        result = find_mitigation_id_by_name("   ", self.mitigations)
        self.assertIsNone(result)
    
    def test_empty_mitigations_list(self):
        """Test with empty mitigations list"""
        result = find_mitigation_id_by_name("Any name", [])
        self.assertIsNone(result)


class TestTechniqueTsvToJson(unittest.TestCase):
    """Test the technique_tsv_to_json function"""
    
    def test_technique_parsing(self):
        """Test parsing the technique TSV file"""
        test_file = 'tests/test_data/trwm/technique.tsv'
        result = technique_tsv_to_json(test_file)
        
        # Check basic structure
        self.assertIsInstance(result, dict)
        self.assertEqual(result['id'], 'T9999')
        self.assertEqual(result['name'], 'Test technique')
        self.assertEqual(result['description'], 'Description of test technique')
        
        # Check JSON parsing (synonyms, subtechniques)
        self.assertIsInstance(result['synonyms'], list)
        self.assertEqual(len(result['synonyms']), 3)
        self.assertEqual(result['synonyms'][0], 'Synonym1 of test technique')
        
        self.assertIsInstance(result['subtechniques'], list)
        self.assertEqual(len(result['subtechniques']), 0)
        
        # Check CSV parsing (examples, references, CASE_output_classes)
        self.assertIsInstance(result['examples'], list)
        self.assertEqual(len(result['examples']), 3)
        self.assertEqual(result['examples'][0], 'Example1 of test technique')
        
        self.assertIsInstance(result['references'], list)
        self.assertEqual(len(result['references']), 3)
        self.assertEqual(result['references'][0], 'Reference 1, details')
        
        self.assertIsInstance(result['CASE_output_classes'], list)
        self.assertEqual(len(result['CASE_output_classes']), 4)


class TestMitigationsTsvToJson(unittest.TestCase):
    """Test the mitigations_tsv_to_json function"""
    
    def test_mitigations_parsing(self):
        """Test parsing the mitigations TSV file"""
        test_file = 'tests/test_data/trwm/mitigations.tsv'
        result = mitigations_tsv_to_json(test_file)
        
        # Check basic structure
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)
        
        # Check first mitigation (technique field should be removed when empty)
        first_mit = result[0]
        self.assertEqual(first_mit['id'], 'M1027')
        self.assertEqual(first_mit['name'], 'Dual tool verification')
        self.assertNotIn('technique', first_mit)  # Empty technique fields are removed
        self.assertEqual(first_mit['references'], [])
        
        # Check mitigation with references (CSV parsing)
        third_mit = result[2]  # Mx001
        self.assertEqual(third_mit['id'], 'Mx001')
        self.assertEqual(third_mit['name'], 'New mitigation 3')
        self.assertEqual(third_mit['technique'], 'T1234')
        self.assertIsInstance(third_mit['references'], list)
        self.assertEqual(len(third_mit['references']), 2)
        self.assertEqual(third_mit['references'][0], 'reference 1')
        
        # Check mitigation with trailing comma in references
        fourth_mit = result[3]  # MX002
        self.assertEqual(fourth_mit['id'], 'MX002')
        self.assertIsInstance(fourth_mit['references'], list)
        self.assertEqual(len(fourth_mit['references']), 1)  # Empty string should be filtered out
        self.assertEqual(fourth_mit['references'][0], 'reference 3')        


class TestWeaknessesTsvToJson(unittest.TestCase):
    """Test the weaknesses_tsv_to_json function"""
    
    def test_weaknesses_parsing(self):
        """Test parsing the weaknesses TSV file"""
        test_file = 'tests/test_data/trwm/weaknesses.tsv'
        result = weaknesses_tsv_to_json(test_file)
        
        # Check basic structure
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 16)  # Should skip placeholder rows
        
        # Check first weakness
        first_weakness = result[0]
        self.assertEqual(first_weakness['id'], 'Wx001')
        self.assertEqual(first_weakness['name'], 'Weakness 1 for R1')
        
        # Check flag columns
        self.assertEqual(first_weakness['INCOMP'], 'x')
        self.assertEqual(first_weakness['INAC-EX'], '')
        self.assertEqual(first_weakness['INAC-ALT'], '')
        self.assertEqual(first_weakness['INAC-AS'], '')
        self.assertEqual(first_weakness['INAC-COR'], '')
        self.assertEqual(first_weakness['MISINT'], '')
        
        # Check references parsing (plain text)
        self.assertEqual(first_weakness['references'], ['Ref1'])
        
        # Check weakness with CSV references
        third_weakness = result[2]  # Wx003
        self.assertEqual(third_weakness['id'], 'Wx003')
        self.assertIsInstance(third_weakness['references'], list)
        self.assertEqual(len(third_weakness['references']), 2)
        self.assertEqual(third_weakness['references'][0], 'Ref3')
        
        # Check weakness with JSON references
        fourth_weakness = result[3]  # Wx004
        self.assertEqual(fourth_weakness['id'], 'Wx004')
        self.assertIsInstance(fourth_weakness['references'], list)
        self.assertEqual(len(fourth_weakness['references']), 3)
        self.assertEqual(fourth_weakness['references'][0], 'Ref 5')
        
        # Check different flag patterns
        second_weakness = result[1]  # Wx002
        self.assertEqual(second_weakness['INCOMP'], '')
        self.assertEqual(second_weakness['INAC-EX'], 'x')
        
        # Check empty references
        fifth_weakness = result[4]  # Wx005
        self.assertEqual(fifth_weakness['references'], [])


class TestProcessWeaknessMitigations(unittest.TestCase):
    """Test the process_weakness_mitigations function"""
    
    def setUp(self):
        """Set up test data"""
        self.mitigations = [
            {"id": "M1027", "name": "Dual tool verification"},
            {"id": "M1050", "name": "Manual verification of relevant data"},
            {"id": "Mx001", "name": "New mitigation 1", "technique": "T1234"},
            {"id": "Mx003", "name": "New mitigation 2"}
        ]
        
        self.headers = ['id', 'name', 'INCOMP', 'Summary', 'Mitigation 1', 'Mitigation 2', 'Mitigation 3', 'References']
    
    def test_single_mitigation_match(self):
        """Test finding a single mitigation in a weakness row"""
        weakness_row = ['Wx001', 'Test weakness', 'X', 'INCOMP', 'Dual tool verification', '', '', 'Ref1']
        result = process_weakness_mitigations(weakness_row, self.headers, self.mitigations)
        
        self.assertEqual(result, ['M1027'])
    
    def test_multiple_mitigation_matches(self):
        """Test finding multiple mitigations in a weakness row"""
        weakness_row = ['Wx001', 'Test weakness', 'X', 'INCOMP', 'Dual tool verification', 'New mitigation 1', '', 'Ref1']
        result = process_weakness_mitigations(weakness_row, self.headers, self.mitigations)
        
        self.assertEqual(result, ['M1027', 'Mx001'])
    
    def test_no_mitigation_matches(self):
        """Test weakness row with no valid mitigations"""
        weakness_row = ['Wx001', 'Test weakness', 'X', 'INCOMP', '', '', '', 'Ref1']
        result = process_weakness_mitigations(weakness_row, self.headers, self.mitigations)
        
        self.assertEqual(result, [])
    
    def test_mitigation_not_found(self):
        """Test mitigation name that doesn't exist in mitigations list"""
        weakness_row = ['Wx001', 'Test weakness', 'X', 'INCOMP', 'Unknown mitigation', '', '', 'Ref1']
        result = process_weakness_mitigations(weakness_row, self.headers, self.mitigations)
        
        self.assertEqual(result, [])
    
    def test_case_insensitive_matching(self):
        """Test that mitigation matching is case insensitive"""
        weakness_row = ['Wx001', 'Test weakness', 'X', 'INCOMP', 'DUAL TOOL VERIFICATION', '', '', 'Ref1']
        result = process_weakness_mitigations(weakness_row, self.headers, self.mitigations)
        
        self.assertEqual(result, ['M1027'])
    
    def test_handles_correct_headers(self):
        """Test that function handles correctly spelled headers"""
        headers = ['id', 'name', 'INCOMP', 'Summary', 'Mitigation 1', 'Mitigation 2', 'References']
        weakness_row = ['Wx001', 'Test weakness', 'X', 'INCOMP', 'Dual tool verification', 'New mitigation 1', 'Ref1']
        result = process_weakness_mitigations(weakness_row, headers, self.mitigations)
        
        self.assertEqual(result, ['M1027', 'Mx001'])


class TestWeaknessesTsvToJsonWithMitigations(unittest.TestCase):
    """Test the weaknesses_tsv_to_json function with mitigation processing"""
    
    def test_weaknesses_with_mitigations(self):
        """Test parsing weaknesses TSV with mitigation mapping"""
        # First get mitigations
        mitigations_file = 'tests/test_data/trwm/mitigations.tsv'
        mitigations = mitigations_tsv_to_json(mitigations_file)
        
        # Then parse weaknesses with mitigation mapping
        weaknesses_file = 'tests/test_data/trwm/weaknesses.tsv'
        result = weaknesses_tsv_to_json(weaknesses_file, mitigations)
        
        # Check basic structure
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 16)
        
        # Check that mitigations field exists
        for weakness in result:
            self.assertIn('mitigations', weakness)
            self.assertIsInstance(weakness['mitigations'], list)
        
        # Check first weakness - should have mapped mitigations
        first_weakness = result[0]  # Wx001 with "Manual verification of relevant data" and "New mitigation 1"
        self.assertEqual(first_weakness['id'], 'Wx001')
        self.assertIn('M1050', first_weakness['mitigations'])  # Manual verification of relevant data
        # Note: "New mitigation 1" should map to MX002 based on test data
        
        # Check weakness with "Dual tool verification"
        fourth_weakness = result[3]  # Wx004 with "Dual tool verification"
        self.assertEqual(fourth_weakness['id'], 'Wx004')
        self.assertIn('M1027', fourth_weakness['mitigations'])  # Dual tool verification


class TestBlankIdValidation(unittest.TestCase):
    """Test validation of blank IDs"""
    
    def test_blank_technique_id_raises_error(self):
        """Test that blank technique ID causes system exit"""
        test_file = 'tests/test_data/trwm/blank_technique.tsv'
        with self.assertRaises(SystemExit) as cm:
            technique_tsv_to_json(test_file)
        self.assertEqual(cm.exception.code, 1)
    
    def test_blank_mitigation_id_raises_error(self):
        """Test that blank mitigation ID causes system exit"""
        test_file = 'tests/test_data/trwm/blank_mitigations.tsv'
        with self.assertRaises(SystemExit) as cm:
            mitigations_tsv_to_json(test_file)
        self.assertEqual(cm.exception.code, 1)
    
    def test_blank_weakness_id_raises_error(self):
        """Test that blank weakness ID causes system exit"""
        test_file = 'tests/test_data/trwm/blank_weaknesses.tsv'
        with self.assertRaises(SystemExit) as cm:
            weaknesses_tsv_to_json(test_file)
        self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()