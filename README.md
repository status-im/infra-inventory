# Infra Inventory

This repository contains a Python Flask application to create a web page showing all the Application hosted by IFT.

## Development

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
poetry install
```

### Run

Setup all the environment variables listed in `.env.example` and make sure to have access to a Consul instance at the host and port specified in the environment variables.

```bash
./run.py
```


