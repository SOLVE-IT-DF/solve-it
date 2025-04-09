import unittest
import solveitcore

class MyTestCase(unittest.TestCase):

    def test_kb_loads(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(type(kb), solveitcore.SOLVEIT)

    def test_list_retrieval(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(list, type(kb.list_techniques()))
        self.assertEqual(list, type(kb.list_tactics()))
        self.assertEqual(list, type(kb.list_weaknesses()))
        self.assertEqual(list, type(kb.list_mitigations()))

    def test_technique_list_contents(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(['T1001'], kb.list_techniques())

    def test_tactic_list_contents(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(['Prioritise', 'Acquire'], kb.list_tactics())

    def test_weakness_list_contents(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(['W1001', 'W1002', 'W1003'], kb.list_weaknesses())

    def test_mitigations_list_contents(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(['M1001', 'M1007', 'M1008'], kb.list_mitigations())

    # Content retreival

    def test_get_technique(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')

        self.assertEqual(dict, type(kb.get_technique('T1001')))
        self.assertEqual('T1001', kb.get_technique('T1001').get('id'))
        self.assertEqual('Triage', kb.get_technique('T1001').get('name'))
        self.assertEqual('Digital forensic triage is a partial forensic examination conducted under (significant) time and resource constraints. (Roussev et al 2013).',
                         kb.get_technique('T1001').get('description'))
        self.assertEqual([], kb.get_technique('T1001').get('synonyms'))
        self.assertEqual('Involves the ranking of apprehended digital items in terms of their importance to a case and likelihood that the contain the data require (Wilson-Kovacs 2020). It can involve multiple techniques to identify devices of most interest such as keyword searching, hash matching, media review etc.',
                         kb.get_technique('T1001').get('details'))
        self.assertEqual([], kb.get_technique('T1001').get('subtechniques'))
        self.assertEqual([], kb.get_technique('T1001').get('examples'))
        self.assertEqual(["W1001", "W1002", "W1003"], kb.get_technique('T1001').get('weaknesses'))
        self.assertEqual([], kb.get_technique('T1001').get('CASE_output_classes'))
        self.assertEqual(["Roussev, V., Quates, C. and Martell, R., 2013. Real-time digital forensics and triage. Digital Investigation, 10(2), pp.158-167.",
        "Wilson-Kovacs, D., 2020. Effective resource management in digital forensics: An exploratory analysis of triage practices in four English constabularies. Policing: an international journal, 43(1), pp.77-90."],
                         kb.get_technique('T1001').get('references'))

    def test_get_technique_na(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')

        self.assertEqual(None, kb.get_technique('T9999'))

    def test_get_weakness(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(dict, type(kb.get_weakness('W1001')))
        self.assertEqual('W1001', kb.get_weakness('W1001').get('id'))
        self.assertEqual('Excluding a device that contains relevant information', kb.get_weakness('W1001').get('name'))
        self.assertEqual('x', kb.get_weakness('W1001').get('INCOMP'))
        self.assertEqual('', kb.get_weakness('W1001').get('INAC-EX'))
        self.assertEqual('', kb.get_weakness('W1001').get('INAC-AS'))
        self.assertEqual('', kb.get_weakness('W1001').get('INAC-ALT'))
        self.assertEqual('', kb.get_weakness('W1001').get('INAC-ALT'))
        self.assertEqual('', kb.get_weakness('W1001').get('MISINT'))
        self.assertEqual([], kb.get_weakness('W1001').get('mitigations'))
        self.assertEqual([], kb.get_weakness('W1001').get('references'))

    def test_get_weakness_usage(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(['T1001'], kb.get_weakness('W1001').get('in_techniques'))

    def test_get_mitigation(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(dict, type(kb.get_mitigation('M1001')))
        self.assertEqual('M1001', kb.get_mitigation('M1001').get('id'))
        self.assertEqual('Review of all triage results that are relied on during the full digital forensic examination', kb.get_mitigation('M1001').get('name'))
        self.assertEqual([], kb.get_mitigation('M1001').get('references'))

    def test_get_mitigation_usage(self):
        kb = solveitcore.SOLVEIT('data', 'solve-it-test.json')
        self.assertEqual(['T1001'], kb.get_mitigation('M1001').get('in_techniques'))
        self.assertEqual(['W1003'], kb.get_mitigation('M1001').get('in_weaknesses'))



if __name__ == '__main__':
    unittest.main()
