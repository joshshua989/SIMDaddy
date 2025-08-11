# SIMDaddy/app.py  — shim that delegates to the real factory
from app import create_app  # this imports create_app from app/__init__.py

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
