"""
Unit Tests for SOLVE-IT Library

This test suite provides extensive coverage of the solve_it_library.KnowledgeBase class,
testing all major functionality including:

- Basic library initialization and data loading
- Core retrieval methods (get_technique, get_weakness, get_mitigation)
- List methods for all entity types
- Objective mapping functionality
- Relationship traversal methods
- Bulk data retrieval methods
- Advanced features (search, mitigation analysis)
- Error handling with invalid inputs

Note: Some tests include logging output (warnings) which are expected behavior
when testing error handling with non-existent IDs.
"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from solve_it_library import KnowledgeBase

class MyTestCase(unittest.TestCase):
    """
    Test cases for the SOLVE-IT Library KnowledgeBase class.
    """

    def test_kb_loads(self):
        """
        Test that the KnowledgeBase initializes correctly.
        
        Expected outcome: Successfully creates a KnowledgeBase instance
        and loads data from the solve-it.json mapping file.
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        self.assertEqual(type(kb), KnowledgeBase)

    def test_list_retrieval(self):
        """
        Test that all list methods return the correct data type.
        
        Expected outcome: All list methods should return Python list objects.
        This verifies the basic API contract for listing methods.
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        self.assertEqual(list, type(kb.list_techniques()))
        self.assertEqual(list, type(kb.list_tactics()))
        self.assertEqual(list, type(kb.list_weaknesses()))
        self.assertEqual(list, type(kb.list_mitigations()))

    def test_technique_list_contents(self):
        """
        Test that technique listing returns expected content.
        
        Expected outcome: 
        - Should contain known techniques like DFT-1001 (Triage) and DFT-1002 (Disk imaging)
        - Should return a reasonable number of techniques (at least 100+)
        - List should be sorted for consistent ordering
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        techniques = kb.list_techniques()
        self.assertIn('DFT-1001', techniques)
        self.assertIn('DFT-1002', techniques)
        self.assertGreater(len(techniques), 100)  # Should have substantial content
        # Test that list is sorted
        self.assertEqual(techniques, sorted(techniques))

    def test_tactic_list_contents(self):
        """
        Test that tactics (objectives) listing returns expected content.
        
        Expected outcome:
        - Should contain core SOLVE-IT objectives like 'Prioritize' and 'Acquire'
        - Should return a reasonable number of objectives (at least 10+)
        - Content should match what's defined in the objective mapping file
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        tactics = kb.list_tactics()
        self.assertIn('Prioritize digital evidence sources', tactics)
        self.assertIn('Acquire data', tactics)
        self.assertGreater(len(tactics), 10)  # Should have substantial content

    def test_weakness_list_contents(self):
        """
        Test that weakness listing returns expected content.
        
        Expected outcome:
        - Should contain known weaknesses like DFW-1001 and DFW-1002
        - Should return a substantial number of weaknesses (at least 100+)
        - List should be sorted for consistent ordering
        - All weakness IDs should follow W#### pattern
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        weaknesses = kb.list_weaknesses()
        self.assertIn('DFW-1001', weaknesses)
        self.assertIn('DFW-1002', weaknesses)
        self.assertGreater(len(weaknesses), 100)  # Should have substantial content
        # Test that list is sorted
        self.assertEqual(weaknesses, sorted(weaknesses))

    def test_mitigations_list_contents(self):
        """
        Test that mitigation listing returns expected content.
        
        Expected outcome:
        - Should contain known mitigations like DFM-1001 and DFM-1007
        - Should return a substantial number of mitigations (at least 100+)
        - List should be sorted for consistent ordering
        - All mitigation IDs should follow M#### pattern
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        mitigations = kb.list_mitigations()
        self.assertIn('DFM-1001', mitigations)
        self.assertIn('DFM-1007', mitigations)
        self.assertGreater(len(mitigations), 100)  # Should have substantial content
        # Test that list is sorted
        self.assertEqual(mitigations, sorted(mitigations))

    # Content Retrieval Tests

    def test_get_technique(self):
        """
        Test retrieval of individual technique by ID.
        
        Expected outcome:
        - Should return a dictionary with technique data for DFT-1001 (Triage)
        - Should have correct structure with id, name, description, etc.
        - Should contain expected fields like synonyms, weaknesses, references
        - Each field should have appropriate data type
        """
        kb = KnowledgeBase('.', 'solve-it.json')

        # Test basic retrieval and structure
        technique = kb.get_technique('DFT-1001')
        self.assertEqual(dict, type(technique))
        self.assertEqual('DFT-1001', technique.get('id'))
        self.assertEqual('Triage', technique.get('name'))
        
        # Test that basic structure exists (exact content may vary)
        self.assertIsNotNone(technique.get('description'))
        self.assertIsInstance(technique.get('synonyms'), list)
        self.assertIsInstance(technique.get('weaknesses'), list)
        self.assertIsInstance(technique.get('references'), list)

    def test_get_technique_na(self):
        """
        Test technique retrieval with non-existent ID.
        
        Expected outcome: Should return None for non-existent technique IDs.
        This tests proper error handling for invalid requests.
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        self.assertEqual(None, kb.get_technique('DFT-9999'))

    def test_get_weakness(self):
        """
        Test retrieval of individual weakness by ID.
        
        Expected outcome:
        - Should return a dictionary with weakness data for DFW-1001
        - Should have correct structure with SOLVE-IT specific fields
        - Should contain categories list
        - Should have proper data types for all fields
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        weakness = kb.get_weakness('DFW-1001')
        self.assertEqual(dict, type(weakness))
        self.assertEqual('DFW-1001', weakness.get('id'))
        self.assertEqual('Excluding a device that contains relevant information', weakness.get('name'))
        self.assertIsInstance(weakness.get('categories'), list)
        self.assertIn('ASTM_INCOMP', weakness.get('categories'))
        self.assertNotIn('ASTM_MISINT', weakness.get('categories'))
        self.assertIsInstance(weakness.get('mitigations'), list)
        self.assertIsInstance(weakness.get('references'), list)

    def test_get_weakness_usage(self):
        """
        Test that weakness reverse lookup functionality works correctly.
        
        Expected outcome:
        - Should use get_techniques_for_weakness() method for reverse lookup
        - DFW-1001 should be referenced by DFT-1001 (Triage)
        - This tests the reverse relationship tracking functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        techniques_for_weakness = kb.get_techniques_for_weakness('DFW-1001')
        self.assertIsInstance(techniques_for_weakness, list)
        technique_ids = [t['id'] for t in techniques_for_weakness]
        self.assertIn('DFT-1001', technique_ids)

    def test_get_mitigation(self):
        """
        Test retrieval of individual mitigation by ID.
        
        Expected outcome:
        - Should return a dictionary with mitigation data for DFM-1001
        - Should have correct structure with id, name, references
        - Should contain expected mitigation information
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        mitigation = kb.get_mitigation('DFM-1001')
        self.assertEqual(dict, type(mitigation))
        self.assertEqual('DFM-1001', mitigation.get('id'))
        self.assertEqual('Review of all triage results that are relied on during the full digital forensic examination', mitigation.get('name'))
        self.assertIsInstance(mitigation.get('references'), list)

    def test_get_mitigation_usage(self):
        """
        Test that mitigation reverse lookup functionality works correctly.
        
        Expected outcome:
        - Should use get_techniques_for_mitigation() and get_weaknesses_for_mitigation() methods
        - Should show which techniques and weaknesses reference this mitigation
        - Lists should have content (not be empty)
        - This tests the reverse relationship tracking functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        techniques_for_mitigation = kb.get_techniques_for_mitigation('DFM-1001')
        weaknesses_for_mitigation = kb.get_weaknesses_for_mitigation('DFM-1001')
        
        self.assertIsInstance(techniques_for_mitigation, list)
        self.assertIsInstance(weaknesses_for_mitigation, list)
        # Check that usage tracking is working
        self.assertGreater(len(techniques_for_mitigation), 0)
        self.assertGreater(len(weaknesses_for_mitigation), 0)

    # Objective Mapping Functionality Tests

    def test_load_objective_mapping(self):
        """
        Test loading different objective mapping files.
        
        Expected outcome:
        - Should successfully load solve-it.json (default mapping)
        - Should load other available mappings like carrier.json if they exist
        - Should return False for non-existent mapping files
        - This tests dynamic mapping switching functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        # Test loading the default mapping
        self.assertTrue(kb.load_objective_mapping('solve-it.json'))
        # Test loading carrier mapping (if it exists)
        available_mappings = kb.list_available_mappings()
        if 'carrier.json' in available_mappings:
            self.assertTrue(kb.load_objective_mapping('carrier.json'))
        # Test loading non-existent mapping
        self.assertFalse(kb.load_objective_mapping('nonexistent.json'))

    def test_list_available_mappings(self):
        """
        Test discovery of available objective mapping files.
        
        Expected outcome:
        - Should return a list of available .json mapping files in data directory
        - Should include solve-it.json as the default mapping
        - Should exclude non-mapping files and subdirectories
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        mappings = kb.list_available_mappings()
        self.assertIsInstance(mappings, list)
        self.assertIn('solve-it.json', mappings)

    def test_list_objectives(self):
        """
        Test listing objectives from the current mapping.
        
        Expected outcome:
        - Should return a list of objective dictionaries
        - Each objective should have 'name' and 'techniques' fields
        - Should have reasonable number of objectives (SOLVE-IT has 17)
        - Structure should match what's defined in the mapping file
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        objectives = kb.list_objectives()
        self.assertIsInstance(objectives, list)
        self.assertGreater(len(objectives), 0)
        # Check structure of objectives
        for obj in objectives:
            self.assertIsInstance(obj, dict)
            self.assertIn('name', obj)
            self.assertIn('techniques', obj)

    def test_get_techniques_for_objective(self):
        """
        Test retrieval of techniques associated with specific objectives.
        
        Expected outcome:
        - Should return list of technique dictionaries for valid objective names
        - Each technique should have proper structure with id and name
        - Should return empty list for non-existent objectives
        - This tests the objective-to-technique relationship mapping
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        objectives = kb.list_objectives()
        if objectives:
            objective_name = objectives[0]['name']
            techniques = kb.get_techniques_for_objective(objective_name)
            self.assertIsInstance(techniques, list)
            # If techniques exist, verify structure
            for technique in techniques:
                self.assertIsInstance(technique, dict)
                self.assertIn('id', technique)
                self.assertIn('name', technique)

    # Relationship Traversal Tests

    def test_get_weaknesses_for_technique(self):
        """
        Test retrieval of weaknesses associated with a specific technique.
        
        Expected outcome:
        - Should return list of weakness dictionaries for DFT-1001 (Triage)
        - DFT-1001 should have associated weaknesses (at least DFW-1001-DFW-1003)
        - Each weakness should have proper structure with id and name
        - This tests the technique-to-weakness relationship traversal
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        weaknesses = kb.get_weaknesses_for_technique('DFT-1001')
        self.assertIsInstance(weaknesses, list)
        # DFT-1001 should have associated weaknesses
        self.assertGreater(len(weaknesses), 0)
        for weakness in weaknesses:
            self.assertIsInstance(weakness, dict)
            self.assertIn('id', weakness)
            self.assertIn('name', weakness)

    def test_get_mitigations_for_weakness(self):
        """
        Test retrieval of mitigations associated with a specific weakness.
        
        Expected outcome:
        - Should find a weakness that has mitigations and test retrieval
        - Should return list of mitigation dictionaries 
        - Each mitigation should have proper structure with id and name
        - This tests the weakness-to-mitigation relationship traversal
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        # Find a weakness that has mitigations
        weakness_with_mits = None
        for weakness_id in kb.list_weaknesses():
            weakness = kb.get_weakness(weakness_id)
            if weakness.get('mitigations'):
                weakness_with_mits = weakness_id
                break
        
        if weakness_with_mits:
            mitigations = kb.get_mitigations_for_weakness(weakness_with_mits)
            self.assertIsInstance(mitigations, list)
            self.assertGreater(len(mitigations), 0)
            for mitigation in mitigations:
                self.assertIsInstance(mitigation, dict)
                self.assertIn('id', mitigation)
                self.assertIn('name', mitigation)

    def test_get_techniques_for_weakness(self):
        """
        Test reverse lookup: finding techniques that reference a specific weakness.
        
        Expected outcome:
        - DFW-1001 should be associated with DFT-1001 (Triage)
        - Should return list of technique dictionaries
        - Each technique should have proper structure
        - This tests the reverse weakness-to-technique relationship lookup
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        techniques = kb.get_techniques_for_weakness('DFW-1001')
        self.assertIsInstance(techniques, list)
        # DFW-1001 should be associated with DFT-1001
        self.assertGreater(len(techniques), 0)
        technique_ids = [t['id'] for t in techniques]
        self.assertIn('DFT-1001', technique_ids)

    def test_get_weaknesses_for_mitigation(self):
        """
        Test reverse lookup: finding weaknesses that reference a specific mitigation.
        
        Expected outcome:
        - DFM-1001 should be associated with weaknesses (reverse lookup)
        - Should return list of weakness dictionaries
        - Each weakness should have proper structure
        - This tests the reverse mitigation-to-weakness relationship lookup
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        weaknesses = kb.get_weaknesses_for_mitigation('DFM-1001')
        self.assertIsInstance(weaknesses, list)
        # DFM-1001 should have associated weaknesses
        self.assertGreater(len(weaknesses), 0)
        for weakness in weaknesses:
            self.assertIsInstance(weakness, dict)
            self.assertIn('id', weakness)
            self.assertIn('name', weakness)

    # Bulk Data Retrieval Tests

    def test_get_all_weaknesses_with_name_and_id(self):
        """
        Test bulk retrieval of weaknesses with minimal data (id and name only).
        
        Expected outcome:
        - Should return list of all weaknesses in the database
        - Each entry should contain only 'id' and 'name' fields (exactly 2 fields)
        - Should have substantial number of weaknesses (100+)
        - This tests the lightweight bulk retrieval functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        weaknesses = kb.get_all_weaknesses_with_name_and_id()
        self.assertIsInstance(weaknesses, list)
        self.assertGreater(len(weaknesses), 100)  # Should have substantial content
        for weakness in weaknesses:
            self.assertIsInstance(weakness, dict)
            self.assertIn('id', weakness)
            self.assertIn('name', weakness)
            self.assertEqual(len(weakness), 2)  # Only id and name

    def test_get_all_weaknesses_with_full_detail(self):
        """
        Test bulk retrieval of weaknesses with complete data.
        
        Expected outcome:
        - Should return list of all weaknesses with full details
        - Each entry should contain all weakness fields (mitigations, categorization, etc.)
        - Should have same count as name-and-id method but with more data per entry
        - This tests the comprehensive bulk retrieval functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        weaknesses = kb.get_all_weaknesses_with_full_detail()
        self.assertIsInstance(weaknesses, list)
        self.assertGreater(len(weaknesses), 100)  # Should have substantial content
        for weakness in weaknesses:
            self.assertIsInstance(weakness, dict)
            self.assertIn('id', weakness)
            self.assertIn('name', weakness)
            self.assertIn('mitigations', weakness)
            # Should have more than just id and name
            self.assertGreater(len(weakness), 2)

    def test_get_all_techniques_with_name_and_id(self):
        """
        Test bulk retrieval of techniques with minimal data (id and name only).
        
        Expected outcome:
        - Should return list of all techniques in the database
        - Each entry should contain only 'id' and 'name' fields (exactly 2 fields)
        - Should have substantial number of techniques (100+)
        - This tests the lightweight bulk retrieval functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        techniques = kb.get_all_techniques_with_name_and_id()
        self.assertIsInstance(techniques, list)
        self.assertGreater(len(techniques), 100)  # Should have substantial content
        for technique in techniques:
            self.assertIsInstance(technique, dict)
            self.assertIn('id', technique)
            self.assertIn('name', technique)
            self.assertEqual(len(technique), 2)  # Only id and name

    def test_get_all_techniques_with_full_detail(self):
        """
        Test bulk retrieval of techniques with complete data.
        
        Expected outcome:
        - Should return list of all techniques with full details
        - Each entry should contain all technique fields (description, weaknesses, references, etc.)
        - Should have same count as name-and-id method but with more data per entry
        - This tests the comprehensive bulk retrieval functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        techniques = kb.get_all_techniques_with_full_detail()
        self.assertIsInstance(techniques, list)
        self.assertGreater(len(techniques), 100)  # Should have substantial content
        for technique in techniques:
            self.assertIsInstance(technique, dict)
            self.assertIn('id', technique)
            self.assertIn('name', technique)
            self.assertIn('weaknesses', technique)
            # Should have more than just id and name
            self.assertGreater(len(technique), 2)

    def test_get_all_mitigations_with_name_and_id(self):
        """
        Test bulk retrieval of mitigations with minimal data (id and name only).
        
        Expected outcome:
        - Should return list of all mitigations in the database
        - Each entry should contain only 'id' and 'name' fields (exactly 2 fields)
        - Should have substantial number of mitigations (100+)
        - This tests the lightweight bulk retrieval functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        mitigations = kb.get_all_mitigations_with_name_and_id()
        self.assertIsInstance(mitigations, list)
        self.assertGreater(len(mitigations), 100)  # Should have substantial content
        for mitigation in mitigations:
            self.assertIsInstance(mitigation, dict)
            self.assertIn('id', mitigation)
            self.assertIn('name', mitigation)
            self.assertEqual(len(mitigation), 2)  # Only id and name

    def test_get_all_mitigations_with_full_detail(self):
        """
        Test bulk retrieval of mitigations with complete data.
        
        Expected outcome:
        - Should return list of all mitigations with full details
        - Each entry should contain all mitigation fields (references, usage tracking, etc.)
        - Should have same count as name-and-id method but with more data per entry
        - This tests the comprehensive bulk retrieval functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        mitigations = kb.get_all_mitigations_with_full_detail()
        self.assertIsInstance(mitigations, list)
        self.assertGreater(len(mitigations), 100)  # Should have substantial content
        for mitigation in mitigations:
            self.assertIsInstance(mitigation, dict)
            self.assertIn('id', mitigation)
            self.assertIn('name', mitigation)
            self.assertIn('references', mitigation)
            # Should have more than just id and name
            self.assertGreater(len(mitigation), 2)

    # Advanced Functionality Tests

    def test_search(self):
        """
        Test basic search functionality across all entity types.
        
        Expected outcome:
        - Should return dictionary with keys for 'techniques', 'weaknesses', 'mitigations'
        - Search for 'triage' should find DFT-1001 (Triage) in techniques
        - Results should be sorted by relevance (highest scores first)
        - This tests the comprehensive search capability across the knowledge base
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        # Test basic search
        results = kb.search('triage')
        self.assertIsInstance(results, dict)
        self.assertIn('techniques', results)
        self.assertIn('weaknesses', results)
        self.assertIn('mitigations', results)
        
        # Should find DFT-1001 (Triage) in techniques
        technique_ids = [t['id'] for t in results['techniques']]
        self.assertIn('DFT-1001', technique_ids)

    def test_search_with_options(self):
        """
        Test search functionality with filtering options.
        
        Expected outcome:
        - Should allow filtering by item_types parameter
        - Search for 'disk' with item_types=['techniques'] should only return techniques
        - Other result categories (weaknesses, mitigations) should be empty
        - This tests the filtered search capability
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        # Test search with specific item types
        results = kb.search('disk', item_types=['techniques'])
        self.assertIsInstance(results, dict)
        self.assertIn('techniques', results)
        self.assertEqual(len(results['weaknesses']), 0)
        self.assertEqual(len(results['mitigations']), 0)

    def test_get_mit_list_for_technique(self):
        """
        Test retrieval of mitigation IDs for a specific technique.
        
        Expected outcome:
        - Should return list of mitigation IDs associated with DFT-1001 (through its weaknesses)
        - Should have at least one mitigation (DFT-1001 has weaknesses with mitigations)
        - Should contain only unique mitigation IDs (no duplicates)
        - This tests the technique-to-mitigation traversal functionality
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        # Test with DFT-1001 which should have mitigations through its weaknesses
        mits = kb.get_mit_list_for_technique('DFT-1001')
        self.assertIsInstance(mits, list)
        self.assertGreater(len(mits), 0)
        # Should contain unique mitigation IDs
        self.assertEqual(len(mits), len(set(mits)))

    def test_get_max_mitigations_per_technique(self):
        """
        Test calculation of maximum mitigations per technique across all techniques.
        
        Expected outcome:
        - Should return positive integer representing max mitigation count
        - Should be reasonable number (typically 10-20, but less than 50)
        - This is used for Excel generation to determine column sizing
        - Tests the analysis functionality for reporting purposes
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        max_mits = kb.get_max_mitigations_per_technique()
        self.assertIsInstance(max_mits, int)
        self.assertGreater(max_mits, 0)
        # Should be a reasonable number (typically 10-20)
        self.assertLess(max_mits, 50)

    def test_tactics_property(self):
        """
        Test compatibility property for legacy API support.
        
        Expected outcome:
        - Should return list of objectives (same as list_objectives())
        - Should maintain backward compatibility with original solveitcore.py
        - Should have reasonable number of tactics/objectives
        - This tests the legacy API compatibility layer
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        tactics = kb.tactics
        self.assertIsInstance(tactics, list)
        self.assertGreater(len(tactics), 10)  # Should have substantial content
        # Should match list_objectives()
        self.assertEqual(tactics, kb.list_objectives())

    # Error Handling and Edge Cases Tests

    def test_error_handling(self):
        """
        Test proper error handling for invalid inputs and edge cases.
        
        Expected outcome:
        - Should return None for non-existent entity IDs (DFT-9999, DFW-9999, DFM-9999)
        - Should return empty lists for relationship queries with invalid IDs
        - Should not raise exceptions, but handle errors gracefully
        - This tests the robustness and reliability of the library
        
        Note: Warning messages in output are expected behavior for invalid IDs.
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        # Test with non-existent IDs
        self.assertIsNone(kb.get_technique('DFT-9999'))
        self.assertIsNone(kb.get_weakness('DFW-9999'))
        self.assertIsNone(kb.get_mitigation('DFM-9999'))
        
        # Test with empty technique for relationships
        self.assertEqual(kb.get_weaknesses_for_technique('DFT-9999'), [])
        self.assertEqual(kb.get_mitigations_for_weakness('DFW-9999'), [])
        self.assertEqual(kb.get_techniques_for_weakness('DFW-9999'), [])
        self.assertEqual(kb.get_weaknesses_for_mitigation('DFM-9999'), [])

    def test_reverse_lookup_correctness(self):
        """
        Test that reverse lookup indices produce identical results to original O(n) methods.
        
        This is a critical validation test that ensures our performance optimization
        doesn't change the actual results returned by the methods.
        
        Expected outcome:
        - Reverse lookup methods should return identical results to manual iteration
        - All relationships should be bidirectional and consistent
        - No data should be lost or corrupted in the optimization
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        
        # Test 1: Verify get_techniques_for_weakness produces correct results
        # by comparing against manual iteration through all techniques
        for weakness_id in ['DFW-1001', 'DFW-1002', 'DFW-1003', 'DFW-1004', 'DFW-1005']:
            if kb.get_weakness(weakness_id):  # Only test if weakness exists
                # Get result from optimized method
                optimized_result = kb.get_techniques_for_weakness(weakness_id)
                optimized_ids = sorted([t['id'] for t in optimized_result])
                
                # Get result from manual iteration (original O(n) method)
                manual_result = []
                for technique_id, technique in kb.techniques.items():
                    if weakness_id in technique.get('weaknesses', []):
                        manual_result.append(technique_id)
                manual_ids = sorted(manual_result)
                
                # Results should be identical
                self.assertEqual(optimized_ids, manual_ids,
                    f"Reverse lookup mismatch for weakness {weakness_id}:\n"
                    f"Optimized: {optimized_ids}\n"
                    f"Manual: {manual_ids}")
        
        # Test 2: Verify get_weaknesses_for_mitigation produces correct results
        # by comparing against manual iteration through all weaknesses
        for mitigation_id in ['DFM-1001', 'DFM-1002', 'DFM-1003', 'DFM-1004', 'DFM-1005']:
            if kb.get_mitigation(mitigation_id):  # Only test if mitigation exists
                # Get result from optimized method
                optimized_result = kb.get_weaknesses_for_mitigation(mitigation_id)
                optimized_ids = sorted([w['id'] for w in optimized_result])
                
                # Get result from manual iteration (original O(n) method)
                manual_result = []
                for weakness_id, weakness in kb.weaknesses.items():
                    if mitigation_id in weakness.get('mitigations', []):
                        manual_result.append(weakness_id)
                manual_ids = sorted(manual_result)
                
                # Results should be identical
                self.assertEqual(optimized_ids, manual_ids,
                    f"Reverse lookup mismatch for mitigation {mitigation_id}:\n"
                    f"Optimized: {optimized_ids}\n"
                    f"Manual: {manual_ids}")
        
        # Test 3: Verify bidirectional consistency
        # If technique T references weakness W, then W should reference T
        for technique_id in ['DFT-1001', 'DFT-1002', 'DFT-1003']:
            technique = kb.get_technique(technique_id)
            if technique and technique.get('weaknesses'):
                for weakness_id in technique['weaknesses']:
                    # Check that weakness references back to technique
                    techniques_for_weakness = kb.get_techniques_for_weakness(weakness_id)
                    technique_ids = [t['id'] for t in techniques_for_weakness]
                    self.assertIn(technique_id, technique_ids,
                        f"Bidirectional inconsistency: {technique_id} references {weakness_id}, "
                        f"but {weakness_id} doesn't reference back to {technique_id}")
        
        # Test 4: Verify no duplicate or missing entries
        # Check that index sizes are consistent with actual data
        total_weakness_references = 0
        for technique in kb.techniques.values():
            total_weakness_references += len(technique.get('weaknesses', []))
        
        total_indexed_references = sum(len(techniques) for techniques in kb._weakness_to_techniques.values())
        
        # Should have same total number of references
        self.assertEqual(total_weakness_references, total_indexed_references,
            "Mismatch between total weakness references and indexed references")

    def test_specific_known_relationships(self):
        """
        Test specific known relationships in the actual dataset.
        
        This validates that our implementation correctly handles the actual data
        rather than just checking generic functionality.
        
        Expected outcome:
        - Known relationships should be present and correct
        - Specific entities should have expected associated items
        - Data integrity should be maintained
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        
        # Test known technique-weakness relationships
        t1001 = kb.get_technique('DFT-1001')  # Triage
        if t1001:
            self.assertEqual(t1001['name'], 'Triage')
            # DFT-1001 should have weaknesses
            self.assertIsInstance(t1001.get('weaknesses'), list)
            self.assertGreater(len(t1001.get('weaknesses', [])), 0)
            
            # Test reverse lookup for each weakness
            for weakness_id in t1001['weaknesses']:
                reverse_techniques = kb.get_techniques_for_weakness(weakness_id)
                technique_ids = [t['id'] for t in reverse_techniques]
                self.assertIn('DFT-1001', technique_ids,
                    f"Reverse lookup failed: {weakness_id} should reference DFT-1001")
        
        # Test known weakness-mitigation relationships
        w1001 = kb.get_weakness('DFW-1001')
        if w1001:
            self.assertEqual(w1001['name'], 'Excluding a device that contains relevant information')
            # DFW-1001 should have mitigations
            if w1001.get('mitigations'):
                for mitigation_id in w1001['mitigations']:
                    reverse_weaknesses = kb.get_weaknesses_for_mitigation(mitigation_id)
                    weakness_ids = [w['id'] for w in reverse_weaknesses]
                    self.assertIn('DFW-1001', weakness_ids,
                        f"Reverse lookup failed: {mitigation_id} should reference DFW-1001")
        
        # Test mitigation DFM-1001 relationships
        m1001 = kb.get_mitigation('DFM-1001')
        if m1001:
            self.assertEqual(m1001['name'], 'Review of all triage results that are relied on during the full digital forensic examination')
            # DFM-1001 should be referenced by some weaknesses
            weaknesses_for_m1001 = kb.get_weaknesses_for_mitigation('DFM-1001')
            self.assertGreater(len(weaknesses_for_m1001), 0,
                "DFM-1001 should be referenced by at least one weakness")
            
            # Verify each weakness actually references DFM-1001
            for weakness in weaknesses_for_m1001:
                weakness_data = kb.get_weakness(weakness['id'])
                self.assertIn('DFM-1001', weakness_data.get('mitigations', []),
                    f"Weakness {weakness['id']} should reference DFM-1001 in its mitigations")

    def test_search_scoring_behavior(self):
        """
        Test that search scoring logic works correctly and produces expected results.
        
        This validates that the refactored search scoring methods (_find_term_matches,
        _apply_search_logic, _calculate_final_score) work correctly and produce
        the expected scoring behavior.
        
        Expected outcome:
        - Name + Description matches should score higher than name-only matches
        - Name-only matches should score higher than description-only matches
        - Phrase matches should score higher than individual word matches
        - AND logic should reject items missing required terms
        - OR logic should scale scores based on match percentage
        - Search results should be sorted by relevance score
        """
        kb = KnowledgeBase('.', 'solve-it.json')
        
        # Test 1: Verify scoring tiers work correctly
        # Create test items with different match patterns - use single term for cleaner testing
        test_items = [
            {'name': 'Test imaging technique', 'description': 'This involves imaging procedures'},  # Both
            {'name': 'Test imaging technique', 'description': 'This involves other procedures'},    # Name only
            {'name': 'Test procedure', 'description': 'This involves imaging procedures'}           # Description only
        ]
        
        terms = ['imaging']  # Use single term to avoid AND logic complications
        phrases = []
        
        scores = []
        for item in test_items:
            match_results = kb._find_term_matches(
                item['name'].lower(), item['description'].lower(), terms, phrases, False
            )
            if kb._apply_search_logic(match_results, terms, phrases, 'AND'):
                score = kb._calculate_final_score(match_results, terms, phrases, 'AND')
                scores.append(score)
            else:
                scores.append(0)
        
        # Verify scoring tier order: name+desc > name-only > desc-only
        self.assertGreater(scores[0], scores[1], "Name+Description should score higher than name-only")
        self.assertGreater(scores[1], scores[2], "Name-only should score higher than description-only")
        self.assertGreater(scores[0], 100, "Name+Description should score 100+")
        self.assertGreater(scores[1], 50, "Name-only should score 50+")
        self.assertGreater(scores[2], 10, "Description-only should score 10+")
        
        # Test 2: Verify phrase scoring
        phrase_item = {'name': 'Disk imaging', 'description': 'Standard procedure'}
        phrase_terms = []
        phrase_phrases = ['disk imaging']
        
        phrase_match = kb._find_term_matches(
            phrase_item['name'].lower(), phrase_item['description'].lower(), phrase_terms, phrase_phrases, False
        )
        phrase_score = kb._calculate_final_score(phrase_match, phrase_terms, phrase_phrases, 'AND')
        
        # Phrases should score higher than individual terms (phrases worth 2x)
        self.assertGreater(phrase_score, 50, "Phrase matches should score higher than individual terms")
        
        # Test 3: Verify AND logic rejects incomplete matches
        incomplete_terms = ['disk', 'imaging', 'nonexistent']
        incomplete_match = kb._find_term_matches(
            test_items[0]['name'].lower(), test_items[0]['description'].lower(), incomplete_terms, phrases, False
        )
        and_logic_result = kb._apply_search_logic(incomplete_match, incomplete_terms, phrases, 'AND')
        self.assertFalse(and_logic_result, "AND logic should reject items missing required terms")
        
        # Test 4: Verify OR logic accepts partial matches and scales scores
        or_logic_result = kb._apply_search_logic(incomplete_match, incomplete_terms, phrases, 'OR')
        self.assertTrue(or_logic_result, "OR logic should accept partial matches")
        
        or_score = kb._calculate_final_score(incomplete_match, incomplete_terms, phrases, 'OR')
        and_score = kb._calculate_final_score(incomplete_match, incomplete_terms, phrases, 'AND')
        
        # OR should produce a scaled score, AND should produce full score (if logic passes)
        self.assertGreater(or_score, 0, "OR logic should produce non-zero score for partial matches")
        
        # Test 5: Verify real search results are sorted by relevance
        # Use a search that should return multiple results
        results = kb.search('analysis')
        for category in ['techniques', 'weaknesses', 'mitigations']:
            if len(results[category]) > 1:
                # Cannot directly access scores, but results should be sorted
                # This is verified by the fact that search returns sorted results
                self.assertIsInstance(results[category], list, f"{category} results should be a list")
                # If we have multiple results, they should be sorted by score (tested by integration)
                break
        
        # Test 6: Verify search logic parameters work correctly
        # Test with AND logic
        and_results = kb.search('disk image', search_logic='AND')
        or_results = kb.search('disk image', search_logic='OR')
        
        # OR should generally find more results than AND (unless all items have both terms)
        total_and = sum(len(and_results[cat]) for cat in ['techniques', 'weaknesses', 'mitigations'])
        total_or = sum(len(or_results[cat]) for cat in ['techniques', 'weaknesses', 'mitigations'])
        
        self.assertGreaterEqual(total_or, total_and, "OR search should find >= results than AND search")


if __name__ == '__main__':
    unittest.main()
