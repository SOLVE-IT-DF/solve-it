# Migration Guide: Weakness Classes

## What Changed

The weakness JSON format has been migrated from 6 individual ASTM error classification fields to a single `categories` list.

### Before

```json
{
  "id": "DFW-1001",
  "name": "Excluding a device that contains relevant information",
  "INCOMP": "x",
  "INAC-EX": "",
  "INAC-AS": "",
  "INAC-ALT": "",
  "INAC-COR": "",
  "MISINT": "",
  "mitigations": [],
  "references": []
}
```

### After

```json
{
  "id": "DFW-1001",
  "name": "Excluding a device that contains relevant information",
  "categories": ["ASTM_INCOMP"],
  "mitigations": [],
  "references": []
}
```

## Field Mapping

| Old Field | New Code |
|-----------|----------|
| `INCOMP` | `ASTM_INCOMP` |
| `INAC-EX` | `ASTM_INAC_EX` |
| `INAC-AS` | `ASTM_INAC_AS` |
| `INAC-ALT` | `ASTM_INAC_ALT` |
| `INAC-COR` | `ASTM_INAC_COR` |
| `MISINT` | `ASTM_MISINT` |

## How to Detect Old Format

Check for the presence of any old field key:

```python
if "INCOMP" in weakness_dict:
    # Old format
```

## How to Convert

```python
from solve_it_library.models import ASTM_CLASS_MAPPING

def convert_weakness(data):
    classes = []
    for old_key, new_code in ASTM_CLASS_MAPPING.items():
        val = data.get(old_key) or data.get(old_key.replace("-", "_"))
        if val and val.strip().lower() == "x":
            classes.append(new_code)
    # Remove old fields
    for key in list(data.keys()):
        if key in {"INCOMP", "INAC-EX", "INAC-AS", "INAC-ALT", "INAC-COR", "MISINT",
                    "INAC_EX", "INAC_AS", "INAC_ALT", "INAC_COR"}:
            del data[key]
    data["categories"] = classes
    return data
```

## Pydantic Model Changes

The `Weakness` model in `solve_it_library/models.py` has been updated:

- **Removed**: 6 `Optional[str]` fields (`INCOMP`, `INAC_EX` with alias, etc.)
- **Removed**: `model_config = ConfigDict(populate_by_name=True)` (no longer needed)
- **Added**: `categories: List[str]` with validation against `VALID_WEAKNESS_CLASSES`

## Import Changes

The following are now available from `solve_it_library.models`:

```python
from solve_it_library.models import ASTM_CLASS_MAPPING, VALID_WEAKNESS_CLASSES
```

- `ASTM_CLASS_MAPPING`: dict mapping old field names to new codes
- `VALID_WEAKNESS_CLASSES`: set of all valid `ASTM_*` codes

## RDF/Ontology Changes

- **Removed**: 6 `DatatypeProperty` declarations (`mayResultInINCOMP`, etc.)
- **Added**: `ASTMErrorCategory` class with 6 named individuals
- **Added**: `hasWeaknessClass` ObjectProperty (domain: Weakness, range: ASTMErrorCategory)

Old RDF:
```turtle
:weakness1 solveit-core:mayResultInINCOMP true .
```

New RDF:
```turtle
:weakness1 solveit-core:hasWeaknessClass solveit-core:ASTM_INCOMP .
```

## Issue Form Changes

- GitHub issue forms now use a `textarea` field instead of `checkboxes` for weakness classes
- Enter one class code per line (e.g. `ASTM_INCOMP`)
- The textarea can be pre-filled via URL parameters (checkboxes could not)

## Common Patterns to Search For

When updating downstream code, search for these patterns:

- `INCOMP` — old field access
- `INAC-EX` / `INAC_EX` — old hyphenated/underscored field names
- `mayResultIn` — old RDF property prefix
- `ASTM_CLASSES` / `ASTM_FIELDS` — old constant names
- `_astm_key` — old helper function (removed)
- `parse_astm_checkboxes` — old checkbox parser (removed)

## Downstream Repos Requiring Updates

The following repos consume weakness data and may need updates:

- `solve-it-x` — SOLVE-IT extensions
- `solve-it-x-demo-ai-applicability-review-` — AI applicability review demo
- `solve-it-x-demo-mobile-forensics` — Mobile forensics demo
- `solve-it-x-demo-simulated-lab-application` — Simulated lab demo
- `trwm-solveit-helper` — TRWM helper tool
- `solve-it-case-logger-sicl` — CASE logger
