# Cleaner Script for Plex and qBittorrent

This script helps you clean up your Plex library and manage your qBittorrent torrents. It can delete old Plex media files and torrents based on specified criteria and send notifications to Discord.

## Features
- Deletes movies and episodes from Plex if they have been watched and are older than a specified number of days.
- Deletes qBittorrent torrents if their ratio or seeding time exceeds specified limits.
- Sends notifications to Discord.
- Test mode to simulate deletions without actually performing them.

## Requirements
- Python 3
- Required Python packages: `requests`, `discord.py`, `plexapi`

## Installation
1. Clone the repository.
2. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
3. Create a configuration file `Cleaner.conf` based on the provided `Cleaner.default` file. Update the settings as needed.

## Configuration
Create a `Cleaner.conf` file with the following format:

```json
{
    "plex": {
        "host": "127.0.0.1",
        "port": "32400",
        "token": "YOUR_PLEX_TOKEN"
    },
    "qBittorrent": {
        "url": "http://localhost:8080",
        "username": "admin",
        "password": "adminadmin",
        "min_ratio": 2.0,
        "min_seed_time_days": 1  # Minimum seed time in days
    },
    "discord_webhook_url": "YOUR_DISCORD_WEBHOOK_URL",
    "keep_movies": ["Movie 1", "Movie 2"],
    "keep_shows": ["Show 1", "Show 2"],
    "days_to_keep": 30,
    "test_mode": true  # Set to true to enable test mode
}


```
## How to Obtain Plex Token
- Open Plex Web App.

- Open the browser’s Developer Tools (usually by pressing F12).
- Go to the “Network” tab.
- Refresh the page.
- Look for a network request to a Plex resource (e.g., “library”, “media”, etc.).
- In the headers of this request, look for an X-Plex-Token entry. This is your Plex Token.

## Running the Script
- ./Cleaner.py
- Or schedule it to run daily using cron: crontab -e 0 2 * * * /path/to/Cleaner.py

## Notes
- Ensure the script has execute permissions:
chmod +x /path/to/Cleaner.py
- The .default section in the configuration file should be removed or renamed before use.
