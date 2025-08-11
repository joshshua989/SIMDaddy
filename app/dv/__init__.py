
# app/dv/__init__.py

from flask import Blueprint

# Blueprint configured to use the unified SIMDaddy template/static roots
# dv package is SIMDaddy/app/dv; go up to SIMDaddy/ then into templates/static
dv_bp = Blueprint(
    "dv",
    __name__,
    template_folder="../../templates/dv",
    static_folder="../../static"
)

from . import routes  # noqa: E402,F401
a