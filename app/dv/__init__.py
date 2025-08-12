
# app/dv/__init__.py

from flask import Blueprint

# DV blueprint uses the unified SIMDaddy template/static roots
dv_bp = Blueprint(
    "dv",
    __name__,
    template_folder="../../templates/dv",
    static_folder="../../static"
)

from . import routes  # keep at bottom
