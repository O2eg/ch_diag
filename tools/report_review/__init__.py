"""Reusable report-matrix generator for human review."""

from .config import ReviewConfig, load_review_config
from .matrix import ReportCase, build_cases

__all__ = ["ReportCase", "ReviewConfig", "build_cases", "load_review_config"]
