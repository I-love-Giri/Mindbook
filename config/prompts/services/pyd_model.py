from typing import List, Optional
from pydantic import BaseModel, Field


class SubjectClassification(BaseModel):
    subject: Optional[str] = None
    sub_subject: Optional[str] = None
    difficulty: Optional[str] = None
    subjects: List[str] = Field(default_factory=list)
