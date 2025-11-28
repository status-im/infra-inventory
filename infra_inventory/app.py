from flask import Flask, render_template, request, jsonify, redirect, redirect, url_for, abort, session
from authlib.integrations.flask_client import OAuth, token_update
from functools import wraps
import json
import os
import threading
import time
import logging
from collections import defaultdict
from .consul_client import ConsulClient
from .config import Config

config = Config()
app = Flask(__name__)
app.config.update({
    'SECRET_KEY': config.SECRET_KEY,
})
oauth= OAuth(app=app)
oauth.register(
    name="keycloak",
    client_id=config.OAUTH_CLIENT_ID,
    client_secret=config.OAUTH_CLIENT_SECRET,
    server_metadata_url=f'{config.OAUTH_ISSUER}/.well-known/openid-configuration',
    userinfo_endpoint=f'{config.OAUTH_ISSUER}/protocol/openid-connect/userinfo',
    client_kwargs={
        'scope': config.OAUTH_SCOPE
    }
)

# Set up logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Keycloak Auth verificaiton
def requires_keycloak_session(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        app.logger.debug('session %s', session )
        user=session.get('user')
        if user is None:
            return redirect('/')
        return view(*args, **kwargs)
    return decorated

# Render Helper
def render_page():
    return render_template(
        'upload.html',
        wallet_files=get_list_file('wallets'),
        bank_files=get_list_file('bank'),
        tokens_files=get_list_file('tokens')
    )

# Global variable to store websites data
websites_data = []

def load_websites():
    """Load websites data from JSON file or refresh from Consul"""
    global websites_data

    # Try to load from file first
    if os.path.exists('websites.json'):
        try:
            with open('websites.json') as f:
                websites_data = json.load(f)
            logger.info("Loaded websites data from JSON file")
        except Exception as e:
            logger.error(f"Error loading websites from JSON file: {e}")
            websites_data = []

    return websites_data

def refresh_websites_from_consul():
    """Refresh websites data from Consul and save to JSON file"""
    global websites_data

    logger.info("Refreshing websites data from Consul...")
    consul_client = ConsulClient()
    websites = consul_client.get_websites_from_consul()

    if websites:
        websites_data = websites
        try:
            with open('websites.json', 'w') as f:
                json.dump(websites_data, f, indent=2)
            logger.info("Successfully refreshed and saved websites data")
        except Exception as e:
            logger.error(f"Error saving websites data to JSON file: {e}")
    else:
        logger.warning("No websites data received from Consul")

    # Schedule next refresh
    threading.Timer(config.REFRESH_INTERVAL, refresh_websites_from_consul).start()

def get_environment_filters(websites):
    """Generate environment-specific filters for stages and tags"""
    env_stages = defaultdict(set)
    env_tags = defaultdict(set)

    for site in websites:
        env = site['environment']
        env_stages[env].add(site['stage'])
        for tag in site['tags']:
            env_tags[env].add(tag)

    # Convert sets to sorted lists
    env_stages = {env: sorted(stages) for env, stages in env_stages.items()}
    env_tags = {env: sorted(tags) for env, tags in env_tags.items()}

    # Add 'all' environment with all unique values
    all_stages = set()
    all_tags = set()

    for stages in env_stages.values():
        all_stages.update(stages)

    for tags in env_tags.values():
        all_tags.update(tags)

    env_stages['all'] = sorted(all_stages)
    env_tags['all'] = sorted(all_tags)

    return env_stages, env_tags

@app.route('/health')
def health():
    return '{"status":"healthy"}'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/inventory')
@requires_keycloak_session
def inventory():
    websites = load_websites()
    environments = sorted(list(set([site['environment'] for site in websites])))
    env_stages, env_tags = get_environment_filters(websites)
    return render_template('inventory.html',
                         environments=environments,
                         stages=env_stages,
                         tags=env_tags,
                         websites=websites)


@app.route('/filter', methods=['GET'])
@requires_keycloak_session
def filter_websites():
    websites = load_websites()
    search_term = request.args.get('search', '').lower()

    # Get filter parameters from query string
    env_filter = request.args.get('environment', '').split(',')
    stage_filter = request.args.get('stage', '').split(',')
    tag_filter = request.args.get('tag', '').split(',')

    # Apply filters
    filtered = []
    for site in websites:
        # Check if site matches search term
        search_match = not search_term or (
            search_term in site['name'].lower() or
            search_term in site['description'].lower() or
            any(search_term in tag.lower() for tag in site['tags'])
        )

        # Check if site matches other filters
        env_match = not env_filter[0] or site['environment'] in env_filter
        stage_match = not stage_filter[0] or site['stage'] in stage_filter
        tag_match = not tag_filter[0] or any(tag in site['tags'] for tag in tag_filter)

        if search_match and env_match and stage_match and tag_match:
            filtered.append(site)

    return jsonify(filtered)

@app.route('/get_stages', methods=['GET'])
@requires_keycloak_session
def get_stages():
    """Get stages for a specific environment"""
    environment = request.args.get('environment', 'all')
    websites = load_websites()
    env_stages, _ = get_environment_filters(websites)
    return jsonify(env_stages.get(environment, []))

@app.route('/get_tags', methods=['GET'])
@requires_keycloak_session
def get_tags():
    """Get tags for a specific environment"""
    environment = request.args.get('environment', 'all')
    websites = load_websites()
    _, env_tags = get_environment_filters(websites)
    return jsonify(env_tags.get(environment, []))

# Authentications routes
@app.route('/login')
def login():
    redirect_uri = url_for('auth', _external=True)
    return oauth.keycloak.authorize_redirect(redirect_uri)


@app.route('/auth')
def auth():
    tokenResponse = oauth.keycloak.authorize_access_token()
    # extracting roles
    if tokenResponse['userinfo']:
        session['user']=tokenResponse['userinfo']
        return redirect('/inventory')
    else:
        abort(403)
    return redirect('/')

@app.route('/logout')
def logout():
    tokenResponse = session.get('tokenResponse')

    if tokenResponse is not None:
        # propagate logout to Keycloak
        refreshToken = tokenResponse['refresh_token']
        endSessionEndpoint = f'{issuer}/protocol/openid-connect/logout'
        requests.post(endSessionEndpoint, data={
            "client_id": clientId,
            "client_secret": clientSecret,
            "refresh_token": refreshToken,
        })
    session.pop('user', None)
    session.pop('tokenResponse', None)
    return redirect('/')

def run_server():
    logger.info("Starting infra-inventory")

    # Start the initial refresh from Consul
    refresh_websites_from_consul()

    # Start the Flask app
    app.run(debug=config.DEBUG, host='0.0.0.0', port=config.PORT)
