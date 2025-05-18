# Omni Discord Bot

![Python Version](https://img.shields.io/badge/python-3.12-blue)
![Discord.py Version](https://img.shields.io/badge/discord.py-2.0.1-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 🌟 Features

### 🎨 AI Art Generation
*CC-BY-SA 4.0 via Wikimedia Commons*

### 🔍 Google Search Integration
![Search Example](https://www.gstatic.com/images/branding/product/2x/googleg_96dp.png)  
*Google Logo (Fair Use)*

## 🛠 Installation

```bash
git clone https://github.com/yourusername/omni-discord-bot.git
cd omni-discord-bot
pip install -r requirements.txt
```

### Install dependencies:

```bash
pip install -r requirements.txt
```

### Configuration

1. Create a `config.json` file in the root directory:

```json
{
    "DISCORD_TOKEN": "YOUR_BOT_TOKEN",
    "OWNER_ID": "YOUR_USER_ID",
    "DATABASE": {
        "DB_PATH": "data/omni.db"
    },
    "APIS": {
        "GOOGLE_API_KEY": "YOUR_GOOGLE_API_KEY",
        "CX_ID": "YOUR_CX_ID",
        "DEEP_AI_KEY": "YOUR_DEEP_AI_KEY"
    },
    "SETTINGS": {
        "PREFIX": "!",
        "COOLDOWN": 60,
        "PRESENCE_TEXT": "/help"
    }
}
```

### Run the Bot:

```bash
python bot.py
```

## Usage

### Basic Commands

* `!ping` - Check bot latency.
* `!draw <prompt>` - Generate an image from text.
* `!search <query>` - Search Google.
* `!remind <time> <reminder>` - Set a personal reminder.

### Admin Commands

* `/setup <log_channel> <admin_role>` - Set up the bot for the server.
* `/addscam <domain>` - Add a domain to the scam list.
* `/removescam <domain>` - Remove a domain from the scam list.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
