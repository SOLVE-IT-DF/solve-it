"""
Pydantic models for the SOLVE-IT Knowledge Base.

Defines the data models and validation for the SOLVE-IT knowledge base items
(techniques, weaknesses, mitigations, objectives) using Pydantic.
"""

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


# --- Data Models ---

class Technique(BaseModel):
    """
    Model for a SOLVE-IT technique.

    Attributes:
        id (str): The unique identifier for the technique (e.g., "T0001").
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
    references: List[str] = Field(default_factory=list, description="Reference sources for this technique")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate that the ID follows the expected format."""
        if not v.startswith('T') or not v[1:].isdigit():
            raise ValueError(f"Technique ID must start with 'T' followed by digits, got '{v}'")
        return v


class Weakness(BaseModel):
    """
    Model for a SOLVE-IT weakness.

    Attributes:
        id (str): The unique identifier for the weakness (e.g., "W0001").
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
    description: Optional[str] = Field(None, description="Additional description (if available)")
    mitigations: List[str] = Field(default_factory=list, description="List of mitigation IDs associated with the weakness")
    INCOMP: Optional[str] = Field(None, description="Flag for incompleteness")
    INAC_EX: Optional[str] = Field(None, description="Flag for inaccuracy - existence", alias="INAC-EX")
    INAC_AS: Optional[str] = Field(None, description="Flag for inaccuracy - association", alias="INAC-AS")
    INAC_ALT: Optional[str] = Field(None, description="Flag for inaccuracy - alternative", alias="INAC-ALT")
    INAC_COR: Optional[str] = Field(None, description="Flag for inaccuracy - correctness", alias="INAC-COR")
    MISINT: Optional[str] = Field(None, description="Flag for misinterpretation")
    references: Optional[List[str]] = Field(default_factory=list, description="Reference sources for this weakness")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate that the ID follows the expected format."""
        if not v.startswith('W') or not v[1:].isdigit():
            raise ValueError(f"Weakness ID must start with 'W' followed by digits, got '{v}'")
        return v
    
    # No validator needed - description is optional


class Mitigation(BaseModel):
    """
    Model for a SOLVE-IT mitigation.

    Attributes:
        id (str): The unique identifier for the mitigation (e.g., "M0001").
        name (str): The name of the mitigation - contains the primary description of what this mitigation entails.
        description (Optional[str]): Additional description (if available).
        technique (Optional[str]): Related technique ID (if this mitigation is linked to a technique).
        references (Optional[List[str]]): Reference sources for this mitigation.
    """
    id: str = Field(..., description="Unique identifier for the mitigation")
    name: str = Field(..., description="Name of the mitigation - contains the primary description of what this mitigation entails")
    description: Optional[str] = Field(None, description="Additional description (if available)")
    technique: Optional[str] = Field(None, description="Related technique ID (if this mitigation is linked to a technique)")
    references: Optional[List[str]] = Field(default_factory=list, description="Reference sources for this mitigation")

    @validator('id')
    def validate_id(cls, v: str) -> str:
        """Validate that the ID follows the expected format."""
        if not v.startswith('M') or not v[1:].isdigit():
            raise ValueError(f"Mitigation ID must start with 'M' followed by digits, got '{v}'")
        return v
    
    # No validator needed - description is optional


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

    @validator('techniques')
    def validate_techniques(cls, v: List[str]) -> List[str]:
        """Validate that the technique IDs follow the expected format."""
        for technique_id in v:
            if not technique_id.startswith('T') or not technique_id[1:].isdigit():
                raise ValueError(f"Technique ID must start with 'T' followed by digits, got '{technique_id}'")
        return v


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
