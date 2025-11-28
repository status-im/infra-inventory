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

Setup all the environment variables listed in `.env.example` and make sure to have access to a Consul instance at the host and port specified in the environment variables. Create the associated client in Keycloak to have the Authentication working.

```
# Consul configuration
CONSUL_HOST=consul.example.com
CONSUL_PORT=8500
CONSUL_SCHEME=https
CONSUL_TOKEN=your-consul-acl-token

# Refresh configuration (in seconds)
REFRESH_INTERVAL=3600
PORT=5000
LOG_LEVEL=INFO
SECRET_KEY=SomeSecrets

OAUTH_CLIENT_ID=inventory-app
OAUTH_CLIENT_SECRET=Something
OAUTH_ISSUER="http://keycloak.example.org"
OAUTH_SCOPE="openid profile email roles"
```

```bash
./run.py
```


