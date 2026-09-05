# EliteHosting - VPS Deployment & Domain Setup Guide (`elitehosting.in`)

Yeh guide aapko step-by-step batayegi ki **EliteHosting** ko apne Linux VPS (Ubuntu/Debian) par kaise deploy karein aur apne custom domain **`elitehosting.in`** se SSL certificate ke saath kaise connect karein.

---

## 📋 System Requirements (Prerequisites)
1. **Linux VPS**: Ubuntu 20.04 / 22.04 / 24.04 LTS (Minimum 1GB RAM, 2GB+ Recommended).
2. **Domain**: `elitehosting.in` (DNS Management Access e.g., Cloudflare, GoDaddy, Namecheap, NameSilo, etc.).
3. **SSH Access**: Root or Sudo user access on your VPS.

---

## 🚀 Step 1: VPS System Update & Package Installation

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

## 📦 Step 2: Clone Codebase & Virtual Environment Setup

Apne project codebase ko VPS par clone/download karein:

```bash
# App directory create karein
cd /var/www || cd ~
git clone <your-repository-url> elitehosting
cd elitehosting

# Python Virtual Environment create aur activate karein
python3 -m venv venv
source venv/bin/activate

# Required Dependencies install karein
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server ke liye
```

---

## ⚙️ Step 3: Environment Variables Configure Karein

Environment variables set karne ke liye `/etc/systemd/system/elitehosting.service` create karenge ya `.env` file use kar sakte hain.

Sample `.env` file banao:
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

## 🛠️ Step 4: Systemd Background Service Setup

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
ExecStart=/root/elitehosting/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5000 app:app
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

## 🌐 Step 5: DNS Records Configuration (`elitehosting.in`)

Apne Domain Provider (Cloudflare, GoDaddy, Namecheap, etc.) ke DNS panel me jayein aur yeh DNS A Records add karein:

| Type | Name | IPv4 Address / Target | TTL |
| :--- | :--- | :--- | :--- |
| **A** | `@` | `<YOUR_VPS_IP_ADDRESS>` | Auto / 2 min |
| **A** | `www` | `<YOUR_VPS_IP_ADDRESS>` | Auto / 2 min |
| **A** | `*` *(Optional for Subdomains)* | `<YOUR_VPS_IP_ADDRESS>` | Auto / 2 min |

*(Note: Replace `<YOUR_VPS_IP_ADDRESS>` with your actual VPS IP e.g. `103.x.x.x`).*

---

## 🔒 Step 6: Nginx Reverse Proxy & Free SSL Setup

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

        # WebSocket support (Agar live streaming logs required ho)
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

### Free HTTPS/SSL Certificate Install Karein (Certbot):
```bash
sudo certbot --nginx -d elitehosting.in -d www.elitehosting.in
```
Certbot automatic Nginx config modify karke HTTPS enable kar dega aur SSL redirect setup kar dega.

---

## 🔍 Step 7: Verification & Useful Commands

### Service Logs Check Karein:
```bash
# Application logs dekhne ke liye:
sudo journalctl -u elitehosting -f -n 100

# Docker containers check karne ke liye:
docker ps -a
```

### Service Restart / Update Code:
```bash
cd /root/elitehosting
git fetch origin && git reset --hard origin/main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart elitehosting
```

Ab aap browser me **`https://elitehosting.in`** open karke apni site access kar sakte hain! 🚀
