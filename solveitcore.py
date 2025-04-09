import os
import json

class SOLVEIT(object):

    def __init__(self, path_to_data_folder, objective_config_file='solve-it.json'):
        self.path_to_weaknesses = os.path.join(path_to_data_folder, 'weaknesses')
        self.path_to_mitigations = os.path.join(path_to_data_folder, 'mitigations')
        self.path_to_techniques = os.path.join(path_to_data_folder, 'techniques')

        path_to_objective_file = os.path.join(path_to_data_folder, objective_config_file)

        self.tactics = self.__load_tactics(path_to_objective_file)
        self.techniques = self.__load_techniques(self.path_to_techniques)
        self.weaknesses = self.__load_weaknesses(self.path_to_weaknesses)
        self.mitigations = self.__load_mitigations(self.path_to_mitigations)

        self.__update_weakness_usages()
        self.__update_mitigation_usages()

    def __load_tactics(self, path_to_tactics_list):
        f = open(path_to_tactics_list)
        tactics_list = json.loads(f.read())
        f.close()
        return tactics_list

    def __load_techniques(self, path_to_techniques):
        '''Loads techniques from on disk json into dictionary'''
        techniques = {}
        for each in os.listdir(path_to_techniques):
            if each[-4:] == 'json':
                technique_path = os.path.join(path_to_techniques, each)
                f = open(technique_path)
                try:
                    tech_dict = json.loads(f.read())
                except json.decoder.JSONDecodeError:
                    print('error loading JSON from {}'.format(technique_path))
                    quit()
                techniques[tech_dict.get('id')] = tech_dict
                f.close()
        return techniques

    def __load_weaknesses(self, path_to_weaknesses):
        '''Loads weaknesses from on disk json into dictionary'''
        weaknesses = {}
        for each in os.listdir(path_to_weaknesses):
            if each[-4:] == 'json':
                f = open(os.path.join(path_to_weaknesses, each))
                weakness_dict = json.loads(f.read())
                weaknesses[weakness_dict.get('id')] = weakness_dict
                weaknesses[weakness_dict.get('id')]['in_techniques'] = []
                f.close()
        return weaknesses

    def __load_mitigations(self, path_to_mitigations):
        '''Loads mitigations from on disk json into dictionary'''
        mitigations = {}
        for each in os.listdir(path_to_mitigations):
            if each[-4:] == 'json':
                f = open(os.path.join(path_to_mitigations, each))
                mit_dict = json.loads(f.read())
                mitigations[mit_dict.get('id')] = mit_dict
                mitigations[mit_dict.get('id')]['in_techniques'] = []
                mitigations[mit_dict.get('id')]['in_weaknesses'] = []
                f.close()
        return mitigations

    def __update_mitigation_usages(self):
        '''Adds a list of all techniques and weaknesses that reference the mitigation'''
        for each_technique in self.techniques:
            for each_weakness in self.techniques[each_technique].get('weaknesses'):
                for each_mitigation in self.weaknesses[each_weakness].get('mitigations'):
                    if each_weakness not in self.mitigations[each_mitigation]['in_weaknesses']:
                        self.mitigations[each_mitigation]['in_weaknesses'].append(each_weakness)
                    if each_technique not in self.mitigations[each_mitigation]['in_techniques']:
                        self.mitigations[each_mitigation]['in_techniques'].append(each_technique)
        return self.mitigations

    def __update_weakness_usages(self):
        '''Adds a list of all techniques that reference the weakness'''
        for each_technique in self.techniques:
            for each_weakness in self.techniques[each_technique].get('weaknesses'):
                if each_technique not in self.weaknesses[each_weakness]['in_techniques']:
                    self.weaknesses[each_weakness]['in_techniques'].append(each_technique)
        return self.weaknesses


    def list_tactics(self):
        out_list = []
        for each_tactic in self.tactics:
            out_list.append(each_tactic.get('name'))
        return out_list

    def list_techniques(self):
        out_list = []
        for each_technique in self.techniques:
            out_list.append(each_technique)
        return sorted(out_list)

    def list_weaknesses(self):
        out_list = []
        for each_weakness in self.weaknesses:
            out_list.append(each_weakness)
        return sorted(out_list)

    def list_mitigations(self):
        out_list = []
        for each_mitigation in self.mitigations:
            out_list.append(each_mitigation)
        return sorted(out_list)

    def get_technique(self, t_id):
        if t_id in self.techniques:
            return self.techniques[t_id]
        else:
            return None

    def get_weakness(self, w_id):
        if w_id in self.weaknesses:
            return self.weaknesses[w_id]
        else:
            return None

    def get_mitigation(self, m_id):
        if m_id in self.mitigations:
            return self.mitigations[m_id]
        else:
            return None


    def get_mit_list_for_technique(self, t_id):
        mit_list_for_this_technique = []
        t = self.get_technique(t_id)
        for each_weakness in t.get('weaknesses'):
            weakness_info = self.get_weakness(each_weakness)

            for each_mitigation in weakness_info.get('mitigations'):
                if each_mitigation not in mit_list_for_this_technique:
                    mit_list_for_this_technique.append(each_mitigation)

        return mit_list_for_this_technique


    def get_max_mitigations_per_technique(self):
        max_mits = 0
        for each_technique in self.list_techniques():
            mits = self.get_mit_list_for_technique(each_technique)

            if len(mits) > max_mits:
                max_mits = len(mits)

        return max_mits