"""Public CAD model composition entry point.

Role separation:

* ``config.py`` owns typed, user-editable design parameters.
* ``models/`` owns geometry construction, element metadata, and focused model
  collections. Choose boundaries by asking which elements are changed
  together, which helpers and parameters they share, and where one phase's
  derived values become another phase's inputs. Keep each module focused on
  one cohesive responsibility and normally below 400 lines; split it again
  before it becomes difficult to scan. Preserve the existing append order and
  pass shared state explicitly rather than hiding cross-collection coupling in
  globals. Each collection contributes elements to one assembled model; it
  does not create a separate ``DesignModel``.
* This module owns the stable ``python-cad`` entry point only. Keep
  ``build_model(context)`` here so ``model:build_model`` remains unchanged.
* ``drawing_annotations.py`` owns drawing presentation and never constructs
  model geometry.
"""

from python_cad_tools.context import BuildContext
from python_cad_tools.elements import DesignModel

from models.starter_model import build_model as _build_model


def build_model(context: BuildContext) -> DesignModel:
    """Compose the project's single ``DesignModel`` from ``models/``."""
    return _build_model(context)
