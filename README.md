# EliteHosting - VPS Deployment & Domain Setup Guide (`elitehosting.in`)

## ⚡ Instant 2-Command Quick Start (Turant Live Karein)

Website aur Telegram Bot Hosting platform ko start karne ke liye bas yeh **2 commands** run karein:

```bash
# Command 1: Dependencies install karein
pip install -r requirements.txt

# Command 2: Application start karein
python3 app.py
```

Aapki site **http://0.0.0.0:5000** par live ho jayegi!

---

## 📋 System Requirements (Prerequisites)
1. **Linux VPS**: Ubuntu 20.04 / 22.04 / 24.04 LTS (Minimum 1GB RAM, 2GB+ Recommended).
2. **Domain**: `elitehosting.in` (DNS Management Access e.g., Cloudflare, GoDaddy, Namecheap, NameSilo, etc.).
3. **SSH Access**: Root or Sudo user access on your VPS.

---

## 🚀 VPS Deployment & Domain Setup Steps (`elitehosting.in`)

### Step 1: VPS System Update & Package Installation
Apne VPS me SSH ke zariye log in karein aur zaroori packages (Python3, Git, Docker, Nginx, Certbot) install karein:

```bash
# System packages update karein
sudo apt update && sudo apt upgrade -y

# Python, Git, Nginx, Certbot install karein
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx docker.io

# Docker service start aur enable karein
sudo systemctl enable --now docker

# Ensure current user can run docker (or run as root)
sudo usermod -aG docker $USER
```

---

### Step 2: Clone Codebase & Virtual Environment Setup
Apne project codebase ko VPS par clone/download karein:

```bash
# App directory create karein
cd /var/www || cd ~
git clone <your-repository-url> elitehosting
cd elitehosting

# Python Virtual Environment create aur activate karein
python3 -m venv venv
source venv/bin/activate

# 2 Commands:
pip install -r requirements.txt
python3 app.py
```

---

### Step 3: Environment Variables Configure Karein (Optional)
Environment variables set karne ke liye `.env` file create karein:

```bash
cat << 'ENVEF' > .env
FLASK_SECRET_KEY=super-secret-random-key-change-this
DATABASE_URL=sqlite:///elitehosting.db
# PostgreSql use karna ho to Neon DB URL dalein:
# DATABASE_URL=postgresql://user:password@ep-xyz.neon.tech/neondb?sslmode=require
ADMIN_USER=rajpapa
ADMIN_PASS=28@RajPapa
ENVEF
```

---

### Step 4: Systemd Background Service Setup (24/7 Live Runtime)
Application ko 24/7 background me chalane ke liye Systemd service banayein:

Create file `/etc/systemd/system/elitehosting.service`:

```ini
[Unit]
Description=EliteHosting Flask Application
After=network.target docker.service
Requires=docker.service

[Service]
User=root
WorkingDirectory=/root/elitehosting
Environment="PATH=/root/elitehosting/venv/bin"
Environment="FLASK_SECRET_KEY=super-secret-random-key-change-this"
Environment="DATABASE_URL=sqlite:///elitehosting.db"
Environment="ADMIN_USER=rajpapa"
Environment="ADMIN_PASS=28@RajPapa"
ExecStart=/root/elitehosting/venv/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Service start aur enable karein:
```bash
sudo systemctl daemon-reload
sudo systemctl enable elitehosting
sudo systemctl start elitehosting

# Status check karein
sudo systemctl status elitehosting
```

---

### Step 5: DNS Records Configuration (`elitehosting.in`)
Apne Domain Provider (Cloudflare, GoDaddy, Namecheap, etc.) ke DNS panel me jayein aur yeh DNS A Records add karein:

| Type | Name | IPv4 Address / Target | TTL |
| :--- | :--- | :--- | :--- |
| **A** | `@` | `<YOUR_VPS_IP_ADDRESS>` | Auto / 2 min |
| **A** | `www` | `<YOUR_VPS_IP_ADDRESS>` | Auto / 2 min |
| **A** | `*` *(Optional for Subdomains)* | `<YOUR_VPS_IP_ADDRESS>` | Auto / 2 min |

*(Note: Replace `<YOUR_VPS_IP_ADDRESS>` with your actual VPS IP e.g. `103.x.x.x`).*

---

### Step 6: Nginx Reverse Proxy & Free SSL Setup
Nginx configuration file create karein `/etc/nginx/sites-available/elitehosting.in`:

```nginx
server {
    listen 80;
    server_name elitehosting.in www.elitehosting.in *.elitehosting.in;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Nginx site enable karein aur syntax test karein:
```bash
sudo ln -s /etc/nginx/sites-available/elitehosting.in /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Free HTTPS/SSL Certificate Install Karein (Certbot):
```bash
sudo certbot --nginx -d elitehosting.in -d www.elitehosting.in
```

---

### Step 7: Verification & Useful Commands

#### Service Logs Check Karein:
```bash
# Application logs dekhne ke liye:
sudo journalctl -u elitehosting -f -n 100

# Docker containers check karne ke liye:
docker ps -a
```

#### Service Restart / Update Code:
```bash
cd /root/elitehosting
git fetch origin && git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart elitehosting
```

Ab aap browser me **`https://elitehosting.in`** open karke apni site access kar sakte hain! 🚀

---

## 🎵 Music Bot Custom Link Configuration & Deployment Guide (Hindi & English)

### 🌟 Overview (Dynamic Link System)
Agar aapke pass ek **Telegram Music Bot** ka code (Yukki, AnonX, Fallen, Alexa, Vamix, Pyrogram/Telethon bots, etc.) hai, to code me koi bhi link **hardcode mat karein**. Saare links ko `.env` (Environment Variables) se load karwayein. Taki jab koi user aapki hosting website (`elitehosting.in`) par jaye, to wo dashboard me bas apne links (Support group, Channel, Owner link, Images, Stream links) `.env` me dale aur uske apne custom links ke sath Music Bot seconds me ready ho jaye!

---

### 🔑 Standard Music Bot Environment Variables List

Aap apne Music Bot codebase me niche diye gaye `.env` keys use karein:

| Environment Variable | Description | Example Value |
| :--- | :--- | :--- |
| `BOT_TOKEN` | Telegram Bot Token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `API_ID` | Telegram API ID | `1234567` |
| `API_HASH` | Telegram API Hash | `abcdef1234567890abcdef1234567890` |
| `MONGO_DB_URI` | MongoDB Database Connection URL | `mongodb+srv://user:pass@cluster.mongodb.net/dbname` |
| `OWNER_ID` | Bot Owner Telegram User ID | `123456789` |
| **`SUPPORT_CHAT`** | **Support Group Link** | `https://t.me/YourSupportGroup` |
| **`SUPPORT_CHANNEL`** | **Official Updates Channel Link** | `https://t.me/YourChannel` |
| **`OWNER_LINK`** | **Bot Owner Telegram Profile Link** | `https://t.me/YourTelegramUsername` |
| **`STREAM_URL`** | **Custom Live Stream / Audio Server URL** | `https://your-stream-server.com/live` |
| **`UPSTREAM_REPO`** | **GitHub Upstream Repo URL** | `https://github.com/YourUsername/YourMusicBot` |
| **`START_IMG_URL`** | **Start Command Welcome Image/GIF URL** | `https://telegra.ph/file/your_image.jpg` |
| **`PING_IMG_URL`** | **Ping Command Image URL** | `https://telegra.ph/file/your_ping_image.jpg` |

---

### 💻 Code Example: Dynamic Link Integration in Python

Apne Music Bot Python code (e.g. `config.py` ya `vars.py`) me links ko is tarah set karein:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Basic Bot Configs
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
MONGO_DB_URI = os.getenv("MONGO_DB_URI", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# 🔗 Dynamic Links (Env Se Change Hongi)
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/EliteHostingSupport")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/EliteHosting")
OWNER_LINK = os.getenv("OWNER_LINK", "https://t.me/rajpapa")
STREAM_URL = os.getenv("STREAM_URL", "https://stream.elitehosting.in")
UPSTREAM_REPO = os.getenv("UPSTREAM_REPO", "https://github.com/vinitraj1231-debug/Eli")
START_IMG_URL = os.getenv("START_IMG_URL", "https://telegra.ph/file/default_start.jpg")
PING_IMG_URL = os.getenv("PING_IMG_URL", "https://telegra.ph/file/default_ping.jpg")
```

Bot ke Start/Help/Ping Inline Keyboard Buttons me variables use karein:

```python
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import config

start_buttons = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("➕ Add Me To Group", url=f"https://t.me/{bot_username}?startgroup=true"),
    ],
    [
        InlineKeyboardButton("💬 Support Group", url=config.SUPPORT_CHAT),
        InlineKeyboardButton("📢 Channel", url=config.SUPPORT_CHANNEL),
    ],
    [
        InlineKeyboardButton("👤 Owner", url=config.OWNER_LINK),
        InlineKeyboardButton("🌐 Upstream Repo", url=config.UPSTREAM_REPO),
    ]
])
```

---

### 🚀 Website Me Deploy Karne Ka Tarika (For Users)

1. **Dashboard me Jayein**: `https://elitehosting.in/dashboard` par login karein.
2. **Deploy Tab me Jayein**: GitHub URL ya ZIP Upload select karein.
3. **🎵 Click "Load Music Bot Env Template"**:
   - Environment Variables section me **"🎵 Load Music Bot Env Template"** button par click karein.
   - Saare Music Bot links aur tokens aamne-saamne aa jayenge.
4. **Apne Links Aur Token Fill Karein**:
   - `BOT_TOKEN`, `API_ID`, `API_HASH`, `MONGO_DB_URI` me apna credential dalein.
   - `SUPPORT_CHAT`, `SUPPORT_CHANNEL`, `OWNER_LINK` me apna group/channel link dalein.
5. **Deploy Par Click Karein**:
   - Bot turant container me build hoke live ho jayega aur aapke diye gaye saare links bot buttons me automatically lag jayenge!
