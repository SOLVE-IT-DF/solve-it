

"""
This provides default code for determining what colour is used 
for presenting techniques in the main list of techniques.
"""
def get_colour_for_technique(kb, t_id):
    t = kb.get_technique(t_id)
    
    # checks number of weaknesses and returns 
    # a different colour for those with zero
    # (as a proxy for how well developed the 
    # technique is)

    if len(t.get('weaknesses')) == 0:
        return "#fdf3f2" # placeholder
    elif (t.get('description') is None or t.get('description') == "") or len(kb.get_mit_list_for_technique(t_id)) == 0:
        return "#fdf8ee" # partial
    else:
        return "#f0faf5" # stable


"""
This provides default code for determining what prefix is added to techniques in the main list
"""
def get_technique_prefix(kb, t_id):
    t = kb.get_technique(t_id)

    if len(t.get('weaknesses')) == 0:
        return "🔴 " # consider this as placeholder
    elif (t.get('description') is None or t.get('description') == "") or len(kb.get_mit_list_for_technique(t_id)) == 0:
        return "🟡 " # consider this as partially populated
    else:
        return "🟢 " # consider this as a release candidate

"""
This provides default code for determining what suffix is added to techniques in the main list
"""
def get_technique_suffix(kb, t_id):
    return ""