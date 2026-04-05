"""
run.py — Development entry point.
Production: use `gunicorn "run:application"` or your WSGI server of choice.
"""
from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run(debug=True, host="127.0.0.1", port=5000)
