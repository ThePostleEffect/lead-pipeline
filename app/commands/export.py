"""export command — export leads to .xlsx workbook."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.exporter import export_workbook
from app.models import Lead, SourceLog, SourceType

logger = logging.getLogger(__name__)


def run_export(input_path: Path, xlsx_path: Path) -> Path:
    """Load leads from JSON and export to an Excel workbook."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    leads = [Lead(**record) for record in raw]

    # Build a basic source log from the input file
    source_log = SourceLog(
        source_name="json_import",
        source_type=SourceType.MANUAL,
        source_url=str(input_path),
        leads_found=len(leads),
        leads_kept=len(leads),
        notes=f"Imported from {input_path.name}",
    )

    path = export_workbook(leads, [source_log], xlsx_path)
    print(f"Exported {len(leads)} leads to {path}")
    return path
