# SOLVE-IT Knowledge Base Library (`solve_it_library`)

A Python library providing a comprehensive interface for loading, parsing, and querying the SOLVE-IT knowledge base data stored in JSON files.

> **Data Directory Requirement:**   
> This library requires the data folder from the SOLVE-IT repository from [https://github.com/SOLVE-IT-DF/solve-it](https://github.com/SOLVE-IT-DF/solve-it).
> The SOLVE-IT knowledge base data (`data` directory) is not **inside** this library. 
> If you do not clone the whole repository including this library together, you must provide the path to its root directory when using this library.

## Key Features

### **Core Functionality**

- **Simple Search**: Keyword/phrase search with AND/OR logic, substring matching, and simplistic relevance scoring
- **Data Validation**: Pydantic models ensure data integrity with error handling
- **Pre-computed Reverse Lookups**: Pre-computed reverse indices enable lookups between techniques, weaknesses, and mitigations
- **Multiple Mappings**: Support for different objective mappings (`solve-it.json`, `carrier.json`, `dfrws.json`)
- **Type Safety**: Type hints throughout for IDE support and error prevention

## Data Models

The SOLVE-IT knowledge base consists of four primary data models:

1. **Technique**: A digital forensic technique used in investigations (includes `CASE_input_classes` and `CASE_output_classes` for CASE/UCO ontology mappings)
2. **Weakness**: A limitation or vulnerability of a technique
3. **Mitigation**: An approach to address or mitigate a weakness
4. **Objective**: A category or goal that organizes techniques (e.g., by investigation phase)

These models have various relationships between them, such as techniques referencing weaknesses, and weaknesses referencing mitigations. For a detailed visualization and explanation of these relationships, see the [Data Model Relationships](./data_model_relationships.md) document.

## Installation & Setup

```python
# Import the KnowledgeBase class
from solve_it_library import KnowledgeBase

# Initialize with path to solve-it repository root (containing 'data' folder)
kb = KnowledgeBase('/path/to/solve-it-repo', 'solve-it.json')
```

## Core API Methods

### **Item Retrieval**
```python
# Get specific items by ID
technique = kb.get_technique("T1002")
weakness = kb.get_weakness("W1001") 
mitigation = kb.get_mitigation("M1001")

# List all IDs (sorted)
technique_ids = kb.list_techniques()    # ['T1001', 'T1002', ...]
weakness_ids = kb.list_weaknesses()     # ['W1001', 'W1002', ...]
mitigation_ids = kb.list_mitigations()  # ['M1001', 'M1002', ...]
```

### **Relationship Queries**

#### Forward Relationships
```python
# Get weaknesses for a technique
weaknesses = kb.get_weaknesses_for_technique("T1002")

# Get mitigations for a weakness  
mitigations = kb.get_mitigations_for_weakness("W1001")
```

#### Reverse Relationships
```python
# Get techniques that reference a specific weakness
techniques = kb.get_techniques_for_weakness("W1001")

# Get weaknesses that reference a specific mitigation
weaknesses = kb.get_weaknesses_for_mitigation("M1001")

# Get techniques that reference a specific mitigation
techniques = kb.get_techniques_for_mitigation("M1001")
```

### **Search**
```python
# Basic keyword search
results = kb.search("network forensics")

# Search specific item types with AND logic
results = kb.search("memory analysis", item_types=["techniques", "weaknesses"])

# Search with OR logic and substring matching
results = kb.search("disk imaging OR memory", search_logic="OR", substring_match=True)

# Search with quoted phrases
results = kb.search('"volatile memory" analysis')

# Results structure:
# {
#   "techniques": [list of matching techniques],
#   "weaknesses": [list of matching weaknesses], 
#   "mitigations": [list of matching mitigations]
# }
```

### **Objective Mappings**
```python
# List available mapping files
mappings = kb.list_available_mappings()  # ['solve-it.json', 'carrier.json', ...]

# Load a different mapping
success = kb.load_objective_mapping("carrier.json")

# List objectives from current mapping
objectives = kb.list_objectives()

# Get techniques for an objective
techniques = kb.get_techniques_for_objective("Data Acquisition")
```

### **Bulk Retrieval**

#### Concise Format (ID and Name Only)
```python
# Get all items with just ID and name
techniques = kb.get_all_techniques_with_name_and_id()
weaknesses = kb.get_all_weaknesses_with_name_and_id()  
mitigations = kb.get_all_mitigations_with_name_and_id()

# Example result: [{"id": "T1001", "name": "Disk Imaging"}, ...]
```

#### Full Detail Format
```python
# Get all items with complete details
techniques = kb.get_all_techniques_with_full_detail()
weaknesses = kb.get_all_weaknesses_with_full_detail()
mitigations = kb.get_all_mitigations_with_full_detail()

# Warning: These methods may return large amounts of data
```

## Backward Compatibility API

For users migrating from `solveitcore.py`, original methods are preserved:

```python
# Previous API methods (100% compatible)
tactics = kb.list_tactics()                    # Returns objective names
tactics_data = kb.tactics                      # Returns objective mapping data
mits = kb.get_mit_list_for_technique("T1002")  # Deduplicated mitigations list
max_mits = kb.get_max_mitigations_per_technique()  # For Excel column sizing
```

## Complete Usage Example

```python
import logging
from solve_it_library import KnowledgeBase

# Configure logging (optional)
logging.basicConfig(level=logging.INFO)

try:
    # Initialize knowledge base
    kb = KnowledgeBase("/path/to/solve-it-repo", "solve-it.json")
    
    # === Basic Usage ===
    
    # Get a specific technique
    technique = kb.get_technique("T1002")
    if technique:
        print(f"Technique: {technique['name']}")
        print(f"Description: {technique['description']}")
    
    # Get related weaknesses and mitigations
    weaknesses = kb.get_weaknesses_for_technique("T1002")
    print(f"Associated weaknesses: {len(weaknesses)}")
    
    for weakness in weaknesses:
        print(f"  - {weakness['id']}: {weakness['name']}")
        mitigations = kb.get_mitigations_for_weakness(weakness['id'])
        print(f"    Mitigations: {[m['id'] for m in mitigations]}")
    
    # === Search ===
    
    # Search for network-related techniques
    results = kb.search("network forensics", item_types=["techniques"])
    network_techniques = results["techniques"]
    print(f"Found {len(network_techniques)} network-related techniques")
    
    # Search for memory analysis with OR logic
    results = kb.search("memory OR volatile", search_logic="OR")
    print(f"Memory analysis results:")
    print(f"  Techniques: {len(results['techniques'])}")
    print(f"  Weaknesses: {len(results['weaknesses'])}")
    print(f"  Mitigations: {len(results['mitigations'])}")
    
    # === Objective Mappings ===
    
    # Work with different mappings
    mappings = kb.list_available_mappings()
    print(f"Available mappings: {mappings}")
    
    # Load carrier-specific mapping
    if "carrier.json" in mappings:
        if kb.load_objective_mapping("carrier.json"):
            carrier_objectives = kb.list_objectives()
            print(f"Carrier objectives: {[obj['name'] for obj in carrier_objectives]}")
    
    # === Reverse Relationships ===
    
    # Find all techniques affected by a specific weakness
    affected_techniques = kb.get_techniques_for_weakness("W1001")
    print(f"Techniques affected by W1001: {[t['id'] for t in affected_techniques]}")
    
    # Find techniques that share weaknesses with T1002
    shared_weakness_techniques = set()
    t1002_weaknesses = kb.get_weaknesses_for_technique("T1002")
    
    for weakness in t1002_weaknesses:
        related_techniques = kb.get_techniques_for_weakness(weakness['id'])
        for tech in related_techniques:
            if tech['id'] != "T1002":  # Exclude T1002 itself
                shared_weakness_techniques.add(tech['id'])
    
    print(f"Techniques sharing weaknesses with T1002: {shared_weakness_techniques}")
    
    # === Bulk Operations ===
    
    # Get summary statistics
    all_techniques = kb.get_all_techniques_with_name_and_id()
    all_weaknesses = kb.get_all_weaknesses_with_name_and_id()
    all_mitigations = kb.get_all_mitigations_with_name_and_id()
    
    print(f"\nKnowledge Base Statistics:")
    print(f"  Techniques: {len(all_techniques)}")
    print(f"  Weaknesses: {len(all_weaknesses)}")
    print(f"  Mitigations: {len(all_mitigations)}")
    
    # === Legacy Compatibility ===
    
    # Use legacy API methods
    tactic_names = kb.list_tactics()
    print(f"Legacy tactics: {tactic_names}")
    
    mitigations_for_t1002 = kb.get_mit_list_for_technique("T1002")
    print(f"Mitigations for T1002 (legacy method): {mitigations_for_t1002}")

except FileNotFoundError as e:
    print(f"Error: {e}")
    print("Please ensure the path to the solve-it repository is correct.")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Migration from `solveitcore.py`

This library is designed as a replacement for `solveitcore.py`:

### **Simple Migration**
```python
# Previous code:
# import solveitcore
# kb = solveitcore.SOLVEIT('data', 'solve-it.json')

# New code:
from solve_it_library import KnowledgeBase  
kb = KnowledgeBase('/path/to/solve-it-repo', 'solve-it.json')

# Existing method calls otherwise work identically.
```

## Error Handling

The library provides comprehensive error handling with detailed logging:

```python
import logging

# Enable debug logging to see detailed information
logging.basicConfig(level=logging.DEBUG)

kb = KnowledgeBase('/path/to/solve-it-repo')

# The library will log:
# - Data loading progress
# - Validation errors in JSON files  
# - Missing file warnings
# - Relationship inconsistencies
# - Search performance information
```

## Performance Considerations

### **Optimized Relationship Queries**
- **Reverse relationship queries** (`get_techniques_for_weakness`, `get_weaknesses_for_mitigation`, `get_techniques_for_mitigation`) use pre-computed indices
- **Index building** occurs once during initialization
- **Memory overhead** for indices is minimal (~<1MB) compared to performance gains

### **General Performance**
- **Bulk retrieval methods** with "full detail" may return large amounts of data
- **Search operations** are optimized with method decomposition for maintainability while preserving performance
- **Data loading** happens once at initialization for optimal query performance
- **Memory usage** scales with knowledge base size (typically minimal)

## Requirements

- Python 3.7+
- Pydantic 2.0+
- Standard library modules: `os`, `json`, `logging`, `typing`

## Support

For issues specific to this library, please check:
1. **File paths** are correct and point to the solve-it repository root
2. **JSON files** in the data directory are valid and complete  
3. **Python version** meets requirements (3.7+)
4. **Pydantic** is installed and up-to-date

For SOLVE-IT framework questions, visit the main repository: [https://github.com/SOLVE-IT-DF/solve-it](https://github.com/SOLVE-IT-DF/solve-it)
