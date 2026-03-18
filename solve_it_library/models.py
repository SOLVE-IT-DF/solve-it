"""
Pydantic models for the SOLVE-IT Knowledge Base.

Defines the data models and validation for the SOLVE-IT knowledge base items
(techniques, weaknesses, mitigations, objectives) using Pydantic.
"""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator, root_validator


# --- Custom Exceptions ---

class SolveItValidationError(Exception):
    """Base exception for validation errors in the SOLVE-IT knowledge base."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class TechniqueValidationError(SolveItValidationError):
    """Exception raised when a technique fails validation."""
    pass


class WeaknessValidationError(SolveItValidationError):
    """Exception raised when a weakness fails validation."""
    pass


class MitigationValidationError(SolveItValidationError):
    """Exception raised when a mitigation fails validation."""
    pass


class ObjectiveValidationError(SolveItValidationError):
    """Exception raised when an objective fails validation."""
    pass


class CitationValidationError(SolveItValidationError):
    """Exception raised when a citation fails validation."""
    pass


# --- Reference entry validator ---

def _validate_reference_entries(v: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
    """Validate that references are dicts with DFCite_id and relevance_summary_280 fields."""
    if v is None:
        return v
    for i, entry in enumerate(v):
        if not isinstance(entry, dict):
            raise ValueError(
                f"Reference entry {i} must be a dict with 'DFCite_id' and 'relevance_summary_280', got {type(entry).__name__}"
            )
        if "DFCite_id" not in entry:
            raise ValueError(
                f"Reference entry {i} is missing required field 'DFCite_id'"
            )
        if not entry["DFCite_id"].startswith("DFCite-"):
            raise ValueError(
                f"Reference entry {i} DFCite_id must start with 'DFCite-', got '{entry['DFCite_id']}'"
            )
    return v


# --- Data Models ---

class CitationFiles:
    """Represents a citation loaded from .bib and/or .txt files in data/references/.

    At least one of bibtex or plaintext must be present.
    The ID is derived from the filename (e.g. DFCite-1001.bib -> DFCite-1001).
    """

    CITE_ID_RE = re.compile(r'^DFCite-\d{4,6}$')

    def __init__(self, cite_id: str, bibtex: Optional[str] = None, plaintext: Optional[str] = None):
        if not self.CITE_ID_RE.match(cite_id):
            raise ValueError(f"Citation ID must match 'DFCite-NNNN', got '{cite_id}'")
        if not bibtex and not plaintext:
            raise ValueError(f"Citation {cite_id} must have at least a .bib or .txt file")
        self.id = cite_id
        self.bibtex = bibtex
        self.plaintext = plaintext


class Technique(BaseModel):
    """
    Model for a SOLVE-IT technique.

    Attributes:
        id (str): The unique identifier for the technique (e.g., "DFT-1001").
        name (str): The name of the technique.
        description (str): A description of the technique.
        synonyms (List[str]): Alternative names for the technique.
        details (Optional[str]): Detailed information about the technique.
        subtechniques (List[str]): A list of sub-technique identifiers.
        examples (List[str]): Examples of tools or implementations.
        weaknesses (List[str]): A list of weakness IDs associated with the technique.
        CASE_input_classes (List[str]): CASE ontology input classes.
        CASE_output_classes (List[str]): CASE ontology output classes.
        references (List[str]): Reference sources for this technique.
    """
    id: str = Field(..., description="Unique identifier for the technique")
    name: str = Field(..., description="Name of the technique")
    description: str = Field(..., description="Description of the technique")
    synonyms: List[str] = Field(default_factory=list, description="Alternative names for the technique")
    details: Optional[str] = Field(None, description="Detailed information about the technique")
    subtechniques: List[str] = Field(default_factory=list, description="List of sub-technique identifiers")
    examples: List[str] = Field(default_factory=list, description="Examples of tools or implementations")
    weaknesses: List[str] = Field(default_factory=list, description="List of weakness IDs associated with the technique")
    CASE_input_classes: List[str] = Field(default_factory=list, description="CASE ontology input classes")
    CASE_output_classes: List[str] = Field(default_factory=list, description="CASE ontology output classes")
    references: List[Dict[str, str]] = Field(default_factory=list, description="Reference entries with DFCite_id and relevance_summary_280")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate that the ID follows the expected format."""
        if not v.startswith('DFT-') or not v[4:].isdigit() or not (4 <= len(v[4:]) <= 6):
            raise ValueError(f"Technique ID must be 'DFT-' followed by 4-6 digits, got '{v}'")
        return v

    @validator('references')
    def validate_references(cls, v):
        return _validate_reference_entries(v)


class Weakness(BaseModel):
    """
    Model for a SOLVE-IT weakness.

    Attributes:
        id (str): The unique identifier for the weakness (e.g., "DFW-1001").
        name (str): The name of the weakness - contains the primary description of what this weakness entails.
        description (Optional[str]): Additional description (if available).
        mitigations (List[str]): A list of mitigation IDs associated with the weakness.
        INCOMP (Optional[str]): Flag for incompleteness.
        INAC-EX (Optional[str]): Flag for inaccuracy - existence.
        INAC-AS (Optional[str]): Flag for inaccuracy - association.
        INAC-ALT (Optional[str]): Flag for inaccuracy - alternative.
        INAC-COR (Optional[str]): Flag for inaccuracy - correctness.
        MISINT (Optional[str]): Flag for misinterpretation.
        references (Optional[List[str]]): Reference sources for this weakness.
    """
    id: str = Field(..., description="Unique identifier for the weakness")
    name: str = Field(..., description="Name of the weakness - contains the primary description of what this weakness entails")
    description: str = Field("", description="Additional description (if available)")
    mitigations: List[str] = Field(default_factory=list, description="List of mitigation IDs associated with the weakness")
    INCOMP: Optional[str] = Field(None, description="Flag for incompleteness")
    INAC_EX: Optional[str] = Field(None, description="Flag for inaccuracy - existence", alias="INAC-EX")
    INAC_AS: Optional[str] = Field(None, description="Flag for inaccuracy - association", alias="INAC-AS")
    INAC_ALT: Optional[str] = Field(None, description="Flag for inaccuracy - alternative", alias="INAC-ALT")
    INAC_COR: Optional[str] = Field(None, description="Flag for inaccuracy - correctness", alias="INAC-COR")
    MISINT: Optional[str] = Field(None, description="Flag for misinterpretation")
    references: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Reference entries with DFCite_id and relevance_summary_280")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate that the ID follows the expected format."""
        if not v.startswith('DFW-') or not v[4:].isdigit() or not (4 <= len(v[4:]) <= 6):
            raise ValueError(f"Weakness ID must be 'DFW-' followed by 4-6 digits, got '{v}'")
        return v

    @validator('references')
    def validate_references(cls, v):
        return _validate_reference_entries(v)


class Mitigation(BaseModel):
    """
    Model for a SOLVE-IT mitigation.

    Attributes:
        id (str): The unique identifier for the mitigation (e.g., "DFM-1001").
        name (str): The name of the mitigation - contains the primary description of what this mitigation entails.
        description (Optional[str]): Additional description (if available).
        technique (Optional[str]): Related technique ID (if this mitigation is linked to a technique).
        references (Optional[List[str]]): Reference sources for this mitigation.
    """
    id: str = Field(..., description="Unique identifier for the mitigation")
    name: str = Field(..., description="Name of the mitigation - contains the primary description of what this mitigation entails")
    description: str = Field("", description="Additional description (if available)")
    technique: Optional[str] = Field(None, description="Related technique ID (if this mitigation is linked to a technique)")
    references: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Reference entries with DFCite_id and relevance_summary_280")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate that the ID follows the expected format."""
        if not v.startswith('DFM-') or not v[4:].isdigit() or not (4 <= len(v[4:]) <= 6):
            raise ValueError(f"Mitigation ID must be 'DFM-' followed by 4-6 digits, got '{v}'")
        return v

    @validator('references')
    def validate_references(cls, v):
        return _validate_reference_entries(v)


class Objective(BaseModel):
    """
    Model for a SOLVE-IT objective.

    Attributes:
        id (Optional[str]): The unique identifier for the objective (e.g. DFO-1001).
        sort_order (Optional[int]): The display ordering position of the objective.
        name (str): The name of the objective.
        description (str): A description of the objective.
        techniques (List[str]): A list of technique IDs associated with the objective.
    """
    id: Optional[str] = Field(None, description="Unique identifier for the objective (e.g. DFO-1001)")
    sort_order: Optional[int] = Field(None, description="Display ordering position of the objective")
    name: str = Field(..., description="Name of the objective")
    description: str = Field(..., description="Description of the objective")
    techniques: List[str] = Field(default_factory=list, description="List of technique IDs associated with the objective")
    references: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Reference entries with DFCite_id and relevance_summary_280")

    @validator('techniques')
    def validate_techniques(cls, v: List[str]) -> List[str]:
        """Validate that the technique IDs follow the expected format."""
        for technique_id in v:
            if not technique_id.startswith('DFT-') or not technique_id[4:].isdigit():
                raise ValueError(f"Technique ID must start with 'DFT-' followed by digits, got '{technique_id}'")
        return v

    @validator('references')
    def validate_references(cls, v):
        return _validate_reference_entries(v)


# --- Error Codes ---

class ErrorCodes:
    """
    Error codes for the SOLVE-IT knowledge base.

    These codes are used to provide more specific error information
    beyond the generic '1' used for "not found" errors.
    """
    # General errors
    NOT_FOUND = 1
    VALIDATION_ERROR = 2
    INTERNAL_ERROR = 3
    
    # Specific validation errors
    INVALID_ID_FORMAT = 101
    MISSING_REQUIRED_FIELD = 102
    INVALID_REFERENCE = 103
    
    # File-related errors
    FILE_NOT_FOUND = 201
    INVALID_JSON = 202
    PERMISSION_DENIED = 203
    
    # Mapping-related errors
    MAPPING_NOT_FOUND = 301
    INVALID_MAPPING_FORMAT = 302
    
    # Search-related errors
    INVALID_SEARCH_PARAMS = 401
