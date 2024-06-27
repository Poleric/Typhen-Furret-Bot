Typhen-Furret-Bot
=================

a personal bot with a variety of features, usually just random stuff.

Usage
-----

### Prerequisites

- [Docker](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Create a `.env` file in the root directory with the following contents, and replace the values in it.
```ini
DISCORD_BOT_TOKEN=your_discord_bot_token_here
LAVALINK_SERVER_PASSWORD=whatever_as_server_password
UID=1000
GID=1000
```

then run

```bash
docker compose up -d
```