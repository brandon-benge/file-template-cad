"""Model-neutral starting point for parametric CAD/BIM composition.

``python-cad`` calls :func:`build_model` with a :class:`BuildContext`.  The
function returns a ``DesignModel``: a stable model identity plus a collection
of ``DesignElement`` objects.  Exporters consume those elements to produce
STEP, IFC, GLB, drawings, quantities, and manifests.

The imports from the source project are deliberately retained as an authoring
palette.  They show the public geometry, element, metadata, placement, IFC,
unit, and standard-library tools typically needed by a substantial model.  An
LLM should use only the imports a new design actually needs as it replaces this
starter; no code should inspect or patch ``python_cad_tools`` internals.
"""

# ruff: noqa: F401  # Approved template palette retained for future model work.

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from build123d import Cone, Plane, Polyline, Sphere, extrude, make_face
from python_cad_tools.context import BuildContext
from python_cad_tools.elements import DesignElement, DesignModel, Dimensions, IfcMapping, MaterialSpec, Placement
from python_cad_tools.geometry import box, cylinder_between, prism_between, sloped_pool
from python_cad_tools.units import FOOT, INCH, MM, Length, mm, to_mm

import config as cfg


def build_model(context: BuildContext) -> DesignModel:
    """Return the smallest valid, model-neutral project definition.

    Extend this function by constructing ``DesignElement`` instances and
    appending them to ``elements`` before returning the model.  Each element
    should keep a stable semantic ``id`` across design revisions and should
    define its geometry together with matching ``Dimensions``, ``Placement``,
    ``MaterialSpec``, and ``IfcMapping`` metadata.

    Recommended authoring flow for an LLM:

    1. Read typed choices from ``config.py``; do not scatter design constants
       through geometry code.
    2. Build geometry with public ``build123d`` and ``python_cad_tools``
       helpers.  Keep datums and coordinate-system assumptions explicit.
    3. Create one ``DesignElement`` for each stable semantic object.  Use clear,
       generic category names and never derive identity from list order.
    4. Mark reference/nonphysical elements intentionally and map physical
       elements to the most accurate IFC class and predefined type available.
    5. Return all elements together in one ``DesignModel``.  Add annotations in
       ``drawing_annotations.py`` rather than embedding drawing presentation
       into the geometry layer.

    ``context`` provides build-time configuration and services.  The neutral
    starter does not need them yet, but real projects should use the context
    instead of performing filesystem writes or global environment lookups.
    """

    del context
    starter_size_mm = to_mm(cfg.STARTER_SIZE)
    elements = [
        DesignElement(
            id="template.starter.element",
            name="Starter Element",
            category="template",
            geometry=box(cfg.STARTER_SIZE, cfg.STARTER_SIZE, cfg.STARTER_SIZE),
            geometry_kind="solid",
            dimensions=Dimensions(
                length_mm=starter_size_mm,
                width_mm=starter_size_mm,
                height_mm=starter_size_mm,
            ),
            material=MaterialSpec(
                id="template.material",
                name="Starter Material",
                category="template",
                color_rgb=(0.65, 0.65, 0.65),
            ),
            ifc_mapping=IfcMapping("IfcBuildingElementProxy", "ELEMENT"),
            properties={
                "template_note": "Replace this element with project-specific geometry.",
            },
        )
    ]

    return DesignModel(
        id="file.template",
        name=cfg.PROJECT_NAME,
        artifact_stem="FileTemplate",
        elements=elements,
        metadata={
            "template": True,
            "authoring_note": "Replace this starter with project-specific elements.",
        },
    )
