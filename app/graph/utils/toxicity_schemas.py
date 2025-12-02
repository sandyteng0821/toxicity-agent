# app/graph/utils/schema_tools.py (append these schemas)
# =============================================================================
# NOAEL and DAP Schemas for Structured Output
# =============================================================================

from pydantic import BaseModel, Field
from typing import Optional, Literal


class NOAELUpdateSchema(BaseModel):
    """Schema for NOAEL imputation structured output."""
    
    inci_name: str = Field(
        description="INCI name of the ingredient (uppercase)"
    )
    value: float = Field(
        description="NOAEL value (numeric only, without unit)"
    )
    unit: str = Field(
        default="mg/kg bw/day",
        description="Unit of NOAEL value"
    )
    experiment_target: str = Field(
        default="Rats",
        description="Test species (e.g., Rats, Mice, Rabbits)"
    )
    source: str = Field(
        description="Data source (e.g., CIR, ECHA, OECD, SCCS)"
    )
    study_duration: str = Field(
        default="90-day",
        description="Study duration (e.g., 90-day, 28-day)"
    )
    note: str = Field(
        description="Detailed study description in Chinese"
    )
    reference_title: str = Field(
        description="Reference document title"
    )
    reference_link: Optional[str] = Field(
        default=None,
        description="URL to reference document"
    )
    statement: str = Field(
        description="Brief statement summarizing the basis for NOAEL determination"
    )


class DAPUpdateSchema(BaseModel):
    """Schema for DAP (Dermal Absorption Percentage) imputation structured output."""
    
    inci_name: str = Field(
        description="INCI name of the ingredient (uppercase)"
    )
    value: float = Field(
        description="DAP value (numeric only, percentage without % symbol)"
    )
    unit: str = Field(
        default="%",
        description="Unit of DAP value"
    )
    experiment_target: str = Field(
        default="Human skin",
        description="Test target (e.g., Human skin, Rat skin)"
    )
    source: str = Field(
        description="Data source (e.g., CIR, ECHA, SCCS, expert)"
    )
    study_duration: str = Field(
        default="theoretical",
        description="Study type (e.g., in vitro, in vivo, theoretical)"
    )
    note: str = Field(
        description="Detailed explanation of DAP determination in Chinese"
    )
    reference_title: str = Field(
        description="Reference document title"
    )
    reference_link: Optional[str] = Field(
        default=None,
        description="URL to reference document"
    )
    statement: str = Field(
        description="Brief statement summarizing the basis for DAP determination"
    )


class ToxicityTaskClassification(BaseModel):
    """Schema for classifying toxicity correction form task type."""
    
    task_type: Literal["noael", "dap", "both", "unknown"] = Field(
        description="Type of imputation task: noael, dap, both, or unknown"
    )
    has_noael_data: bool = Field(
        description="Whether the text contains NOAEL/Repeated Dose Toxicity data"
    )
    has_dap_data: bool = Field(
        description="Whether the text contains DAP/Percutaneous Absorption data"
    )
    inci_name: Optional[str] = Field(
        default=None,
        description="Extracted INCI name if found"
    )
