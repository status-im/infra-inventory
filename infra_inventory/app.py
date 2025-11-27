from flask import Flask, render_template, request, jsonify
import json
import os
import threading
import time
import logging
from collections import defaultdict
from .consul_client import ConsulClient
from .config import Config

app = Flask(__name__)
config = Config()

# Set up logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

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

@app.route('/')
def index():
    websites = load_websites()
    environments = sorted(list(set([site['environment'] for site in websites])))
    env_stages, env_tags = get_environment_filters(websites)

    return render_template('index.html',
                         environments=environments,
                         stages=env_stages,
                         tags=env_tags,
                         websites=websites)

@app.route('/filter', methods=['GET'])
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
def get_stages():
    """Get stages for a specific environment"""
    environment = request.args.get('environment', 'all')
    websites = load_websites()
    env_stages, _ = get_environment_filters(websites)
    return jsonify(env_stages.get(environment, []))

@app.route('/get_tags', methods=['GET'])
def get_tags():
    """Get tags for a specific environment"""
    environment = request.args.get('environment', 'all')
    websites = load_websites()
    _, env_tags = get_environment_filters(websites)
    return jsonify(env_tags.get(environment, []))

def run_server():
    logger.info("Starting infra-inventory")

    # Start the initial refresh from Consul
    refresh_websites_from_consul()

    # Start the Flask app
    app.run(debug=config.DEBUG, host='0.0.0.0', port=config.PORT)
