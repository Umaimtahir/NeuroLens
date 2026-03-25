"""
Pydantic response models for the Activity Classifier API.

Backward-compatible: the `activity` field still exists as a property
that returns `primary_activity` so existing clients don't break.

New in granular classification update:
  application      — detected application name (e.g. "VS Code", "Discord")
  specific_context — what the user is doing (e.g. "Python (Debugging)")
  detected_file    — open file if any (e.g. "main.py")
  app_context      — additional context hint (e.g. "Breakpoint active")
  fused_label      — multi-app combined label when multitasking
"""
from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, computed_field


class ContentDetails(BaseModel):
    """Deep details about the specific interaction."""
    file: Optional[str] = Field(default=None, description="Detailed file name if any")
    domain: Optional[str] = Field(default=None, description="App domain/type")
    interaction: Optional[str] = Field(default=None, description="scrolling, typing, passive, etc")
    media_playing: Optional[bool] = Field(default=False)
    typing_active: Optional[bool] = Field(default=False)

class ContentInfo(BaseModel):
    category: str = Field(..., description="Broad taxonomy category")
    subcategory: str = Field(..., description="Specific activity subcategory")
    activity: str = Field(..., description="Human readable full activity label")
    application: Optional[str] = Field(default=None, description="Detected app name")
    site: Optional[str] = Field(default=None, description="Website domain if browser")
    title: str = Field(default="", description="Window title")
    details: ContentDetails = Field(default_factory=ContentDetails)
    confidence: float = Field(..., description="0.0 to 1.0 confidence")

class ContextInfo(BaseModel):
    duration_current: int = Field(default=0, description="Seconds spent in current un-interrupted activity")
    session_duration: int = Field(default=0, description="Total running session seconds")
    input_activity: str = Field(default="idle", description="typing, mouse, both, idle")
    window_state: Optional[str] = Field(default="focused", description="Window state info")

class CorrelationInfo(BaseModel):
    content_type_code: str = Field(..., description="Structured code for Emotion Correlation mapping")
    activity_intensity: str = Field(default="low", description="high, medium, low, none")
    focus_indicator: str = Field(default="neutral", description="deep_work, neutral, distracted")
    break_recommended: bool = Field(default=False, description="Heuristic to recommend breaks")

class ActivityResult(BaseModel):
    """
    Main API Response Model. Nested strictly for NeuroLens Emotion-Content Correlation.
    """
    timestamp: str = Field(..., description="ISO 8601 Timestamp with TZ")
    session_id: str = Field(..., description="UUID for current app session")
    
    content: ContentInfo
    context: ContextInfo
    for_correlation: CorrelationInfo
    
    # Internal metrics for logging
    method: str = Field(default="unknown")
    processing_time_ms: float = Field(default=0.0)
    
    @computed_field  # type: ignore[misc]
    @property
    def activity(self) -> str:
        """Backward-compatible alias for older clients."""
        return self.content.activity

class FlatActivityResult(BaseModel):
    """Flattened schema specifically for NeuroLens frontend/sync."""
    timestamp: str
    activity: str
    category: str
    subcategory: str
    application: str
    site: Optional[str] = None
    confidence: float
    duration: int

class ErrorResponse(BaseModel):
    detail: str
