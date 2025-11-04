# ekcx-web
East Kent Cyclocross website

## Setup with uv

### Install uv

Install uv using the official installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or via pip:

```bash
pip install uv
```

### Install dependencies

Since this is an application (not a package), install dependencies using the requirements file:

```bash
uv pip install -r requirements.txt
```

Or install dependencies directly:

```bash
uv pip install "fastapi>=0.109.0" "uvicorn>=0.26.0" "gunicorn>=21.2.0" "jinja2>=3.1.3" "pandas>=2.3.3" "openpyxl>=3.1.5"
```

This will create a virtual environment at `.venv` and install all dependencies.

### Run the server

Activate the virtual environment and run the server:

```bash
source .venv/bin/activate
```

For development, run with uvicorn:

```bash
uvicorn main:app --reload
```

The server will be available at `http://localhost:8000`

For production, run with gunicorn (matching the systemd service configuration):

```bash
gunicorn main:app --workers 2 -k worker.MyUvicornWorker --bind unix:ekcx.sock
```

### Alternative: Using uv run with venv activation

You can also use `uv run` by activating the venv first:

```bash
source .venv/bin/activate
uv run uvicorn main:app --reload
```
