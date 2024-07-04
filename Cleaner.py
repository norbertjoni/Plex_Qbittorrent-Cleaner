#!/usr/bin/env python3
import requests
import json
import logging
import os
from datetime import datetime, timedelta
from plexapi.server import PlexServer

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load configuration
with open('Cleaner.conf', 'r') as config_file:
    config = json.load(config_file)

# Plex settings
PLEX_HOST = config['plex']['host']
PLEX_PORT = config['plex']['port']
PLEX_TOKEN = config['plex']['token']
KEEP_MOVIES = config['keep_movies']
KEEP_SHOWS = config['keep_shows']
DAYS_TO_KEEP = config['days_to_keep']
TEST_MODE = config.get('test_mode', False)

# qBittorrent settings
QB_URL = config['qBittorrent']['url']
QB_USERNAME = config['qBittorrent']['username']
QB_PASSWORD = config['qBittorrent']['password']
MIN_RATIO = config['qBittorrent']['min_ratio']
MIN_SEED_TIME_DAYS = config['qBittorrent']['min_seed_time_days']

# Discord settings
DISCORD_WEBHOOK_URL = config['discord_webhook_url']

def send_discord_message(message):
    try:
        payload = {
            "content": message
        }
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            logger.info("Discord message sent successfully")
        else:
            logger.error(f"Failed to send Discord message: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send Discord message: {e}")

# Plex functions
def get_plex_server():
    baseurl = f"http://{PLEX_HOST}:{PLEX_PORT}"
    return PlexServer(baseurl, PLEX_TOKEN)

def cleanup_plex():
    plex = get_plex_server()
    for section in plex.library.sections():
        if section.type == 'movie':
            cleanup_movies(section)
        elif section.type == 'show':
            cleanup_shows(section)

def cleanup_movies(section):
    for movie in section.all():
        logger.debug(f"Checking movie: {movie.title}")
        if movie.title in KEEP_MOVIES:
            logger.debug(f"Skipping movie (kept): {movie.title}")
            continue
        last_viewed = movie.lastViewedAt
        if last_viewed:
            logger.debug(f"Movie {movie.title} last viewed at {last_viewed}")
        else:
            logger.debug(f"Movie {movie.title} has never been viewed")
        if last_viewed and (datetime.now() - last_viewed).days > DAYS_TO_KEEP:
            message = f"Deleting movie: {movie.title} (last viewed: {last_viewed})"
            logger.info(message)
            send_discord_message(message)
            if not TEST_MODE:
                movie.delete()
        else:
            logger.debug(f"Movie {movie.title} not old enough to delete (days: {(datetime.now() - last_viewed).days if last_viewed else 'N/A'})")

def cleanup_shows(section):
    for show in section.all():
        logger.debug(f"Checking show: {show.title}")
        if show.title in KEEP_SHOWS:
            logger.debug(f"Skipping show (kept): {show.title}")
            continue
        for episode in show.episodes():
            last_viewed = episode.lastViewedAt
            if last_viewed:
                logger.debug(f"Episode {episode.title} of show {show.title} last viewed at {last_viewed}")
            else:
                logger.debug(f"Episode {episode.title} of show {show.title} has never been viewed")
            if last_viewed and (datetime.now() - last_viewed).days > DAYS_TO_KEEP:
                message = f"Deleting episode: {episode.title} from show {show.title} (last viewed: {last_viewed})"
                logger.info(message)
                send_discord_message(message)
                if not TEST_MODE:
                    episode.delete()
            else:
                logger.debug(f"Episode {episode.title} of show {show.title} not old enough to delete (days: {(datetime.now() - last_viewed).days if last_viewed else 'N/A'})")

# qBittorrent functions
def login_qbittorrent():
    payload = {'username': QB_USERNAME, 'password': QB_PASSWORD}
    response = requests.post(f'{QB_URL}/api/v2/auth/login', data=payload)
    if response.status_code == 200:
        logger.info("Logged in to qBittorrent")
        return response.cookies
    else:
        logger.error("Failed to log in to qBittorrent")
        return None

def get_qbittorrent_torrents(cookies):
    response = requests.get(f'{QB_URL}/api/v2/torrents/info', cookies=cookies)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error("Failed to fetch torrent list")
        return []

def get_free_space(cookies):
    response = requests.get(f'{QB_URL}/api/v2/sync/maindata', cookies=cookies)
    if response.status_code == 200:
        data = response.json()
        return data['server_state']['free_space_on_disk']
    else:
        logger.error("Failed to fetch free space")
        return None

def delete_qbittorrent_torrent(cookies, torrent_hash, delete_files=True):
    payload = {'hashes': torrent_hash, 'deleteFiles': delete_files}
    response = requests.post(f'{QB_URL}/api/v2/torrents/delete', data=payload, cookies=cookies)
    if response.status_code == 200:
        logger.info(f"Deleted torrent: {torrent_hash}")
    else:
        logger.error(f"Failed to delete torrent: {torrent_hash}")
        send_discord_message(f"Failed to delete torrent: {torrent_hash}")

async def main():
    # Plex cleanup
    cleanup_plex()
    
    # qBittorrent cleanup
    cookies = login_qbittorrent()
    if not cookies:
        send_discord_message("Failed to log in to qBittorrent")
        return

    torrents = get_qbittorrent_torrents(cookies)
    if not torrents:
        send_discord_message("Failed to fetch torrent list")
        return

    initial_free_space = get_free_space(cookies)
    if initial_free_space is None:
        send_discord_message("Failed to fetch free space")
        return

    for torrent in torrents:
        torrent_hash = torrent['hash']
        torrent_name = torrent['name']
        ratio = torrent['ratio']
        seed_time = torrent['seeding_time'] / 3600  # converting to hours
        seed_time_days = seed_time / 24  # converting to days

        if ratio >= MIN_RATIO or seed_time_days >= MIN_SEED_TIME_DAYS:
            reason = f"Ratio: {ratio}" if ratio >= MIN_RATIO else f"Seed Time: {seed_time_days:.2f} days"
            if not TEST_MODE:
                delete_qbittorrent_torrent(cookies, torrent_hash)
            new_free_space = get_free_space(cookies)
            if new_free_space is not None:
                free_space_change = new_free_space - initial_free_space
                message = (
                    f"Torrent {'deleted' if not TEST_MODE else 'would be deleted'}: {torrent_name}\n"
                    f"Reason: {reason}\n"
                    f"Initial free space: {initial_free_space / (1024**3):.2f} GB\n"
                    f"New free space: {new_free_space / (1024**3):.2f} GB\n"
                    f"Free space change: {free_space_change / (1024**3):.2f} GB"
                )
                send_discord_message(message)
                logger.info(message)
            else:
                send_discord_message(f"{'Deleted' if not TEST_MODE else 'Would delete'} torrent: {torrent_name}, but failed to fetch new free space")
                logger.info(f"{'Deleted' if not TEST_MODE else 'Would delete'} torrent: {torrent_name}, but failed to fetch new free space")
        else:
            logger.info(f"Torrent kept: {torrent_name} (Ratio: {ratio}, Seed Time: {seed_time_days:.2f} days)")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
