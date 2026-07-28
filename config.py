"""Central, typed design parameters for a new CAD project.

An LLM or human author should put user-editable dimensions, material choices,
colors, clearances, and layout values in this module.  Geometry belongs in
``model.py`` and drawing-only presentation belongs in
``drawing_annotations.py``.

Prefer values carrying a unit (for example ``12 * INCH``) over bare numbers.
Keep one authoritative value for each design decision and derive related
values from it so later edits cannot silently make the model inconsistent.
The imported unit constants are intentionally retained as the standard
starting palette; remove one only when the project no longer needs it.
"""

# ruff: noqa: F401  # Template palette: future designs may use any retained unit.

from python_cad_tools.units import FOOT, INCH, MM

# Keep the display name generic until the template is adapted to a real
# project.  ``model.build_model`` reads this value when it creates the model
# metadata, so it is the first project-specific string an author should change.
PROJECT_NAME = "File Template"

# A visible physical element is required by drawing-inclusive validation. This
# neutral size drives the single starter solid in ``model.py`` and is meant to
# be replaced, renamed, or removed as soon as a real design is introduced.
STARTER_SIZE = 1 * FOOT

# Add project parameters below in small, clearly named sections.  A useful
# order is: overall datums and extents, component dimensions, materials/colors,
# then derived spacing or placement values.  Comments should explain design
# intent and constraints, not merely restate a numeric value.
