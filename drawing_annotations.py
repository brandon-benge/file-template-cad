"""Model-neutral, format-independent drawing annotation provider.

``python-cad`` calls :func:`build_annotations` after it has assembled drawing
sheets and projected model bounds.  This layer adds labels, callouts,
elevations, schedules, and other presentation metadata; it must not construct
or mutate model geometry.

The retained imports form the same annotation palette as the source project.
An LLM can introduce these types incrementally while keeping every annotation
linked to a stable sheet and, where applicable, to stable model element IDs.
"""

# ruff: noqa: F401  # Approved template palette retained for future annotations.

from __future__ import annotations

from python_cad_tools.context import DrawingContext
from python_cad_tools.drawings import (
    DrawingAnnotationSet,
    ElevationMarker,
    SectionCallout,
    SheetAnnotations,
    Table,
    TableRow,
)
from python_cad_tools.units import format_feet_inches, to_mm

PROVIDER_ID = "file.template.annotations"


def build_annotations(context: DrawingContext) -> DrawingAnnotationSet:
    """Return an empty annotation set ready for project-specific additions.

    Before adding an annotation, inspect ``context.sheets`` and select a real
    sheet ID rather than assuming one exists.  Give every annotation a stable,
    descriptive ID; keep callout references consistent with their destination
    sheets; and use source element IDs when a label or schedule describes model
    geometry.  Unit formatting belongs here when it is presentation-specific.

    Return annotations grouped in ``SheetAnnotations`` entries.  Keeping the
    provider empty is valid for the starter and makes the absence of invented
    project-specific drawing content explicit.
    """

    del context
    return DrawingAnnotationSet(provider_id=PROVIDER_ID, sheets=())
