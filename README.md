# 🚀 EliteHosting Domain & VPS Hosting Setup Guide (`elitehosting.in`)

## ⚠️ Sabse Pehle Yeh Samjhein (Why `python3 app.py` isn't enough):

Jab aap `python3 app.py` chalate hain, toh server terminal me yeh dikhata hai:
```text
 Web Service: http://0.0.0.0:5000
 * Running on http://127.0.0.1:5000
```
Iska matlab hai ki aapki Flask App **sirf VPS ke andar Port 5000 par chal rahi hai**.

Lekin jab koi browser me **`elitehosting.in`** type karta hai:
1. Browser internet par **Port 80 (HTTP)** ya **Port 443 (HTTPS)** par aapke domain ko dhundhta hai.
2. Iske liye aapko **Domain ka DNS (A Record)** VPS ki Public IP se jodna hota hai.
3. VPS me **Nginx Reverse Proxy** lagana hota hai jo Port 80/443 ki request ko aapki Flask App (**Port 5000**) par redirect kare.

---

## ⚡ Complete Setup Checklist (Domain Live Karne Ke 6 Steps)

Follow these exact steps to point **`elitehosting.in`** to your VPS and make it live with HTTPS SSL:

---

### Step 1: VPS Public IP Check Karein
Apne VPS terminal me run karein aur apni **Public IPv4 Address** note karein:
```bash
curl -4 ifconfig.me
```
*(Example Output: `103.187.x.x` — Yeh aapki VPS Public IP hai)*

---

### Step 2: DNS Settings Configure Karein (Domain Provider)
Apne Domain Provider (Cloudflare, GoDaddy, Namecheap, Hostinger, NameSilo, etc.) ke **DNS Management** panel me jayein aur yeh **3 DNS Records** add karein:

| Record Type | Name / Host | Target / Value (IPv4) | TTL | Proxy Status (Cloudflare) |
| :--- | :--- | :--- | :--- | :--- |
| **A** | `@` | `YOUR_VPS_PUBLIC_IP` | Auto / 2 min | DNS Only (ya Proxied) |
| **A** | `www` | `YOUR_VPS_PUBLIC_IP` | Auto / 2 min | DNS Only (ya Proxied) |
| **A** | `*` | `YOUR_VPS_PUBLIC_IP` | Auto / 2 min | DNS Only (ya Proxied) |

*(Note: `YOUR_VPS_PUBLIC_IP` ki jagah Step 1 wali IP dalein, e.g. `103.187.x.x`)*

---

### Step 3: VPS Firewall Ports Open Karein
VPS me HTTP, HTTPS aur Port 5000 allow karein:

```bash
# Ubuntu UFW Firewall enable & open ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp
sudo ufw --force enable
```
*(Agar aap AWS / GCP / DigitalOcean / Oracle Cloud use kar rahe hain, toh unke Cloud Panel Security Groups me bhi Port 80 aur 443 inbound open karein).*

---

### Step 4: Systemd Service Banayein (App ko 24/7 Running Rakhne Ke Liye)
Agar aap terminal band kar denge toh `python3 app.py` ruk jayega. Isliye ise background service banayein:

Create file `/etc/systemd/system/elitehosting.service`:

Paste this configuration (apne path aur credentials ke mutabiq):
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

Enable & Start Service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable elitehosting
sudo systemctl start elitehosting

# Check Status (Active running dikhna chahiye)
sudo systemctl status elitehosting
```

---

### Step 5: Nginx Reverse Proxy Setup Karein (Port 80 -> Port 5000)

Nginx install karein:
```bash
sudo apt update
sudo apt install -y nginx docker.io
sudo systemctl enable --now docker
```

Nginx site config file banayein `/etc/nginx/sites-available/elitehosting.in`:

Paste this content:
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

Enable site & Restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/elitehosting.in /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

### Step 6: Free SSL / HTTPS Certificate Install Karein (Certbot)

Certbot install karein aur SSL enable karein:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d elitehosting.in -d www.elitehosting.in
```

Certbot aapke Nginx config ko automatically update kar dega aur site par `https://` enable ho jayega!

---

## 🛠️ Troubleshooting & Quick Solutions

### 1. "Site Can't Be Reached" / Timeout
- **Cause**: DNS Records nahi jude ya Firewall blocked hai.
- **Fix**:
  1. Terminal me `ping elitehosting.in` run karke check karein ki VPS IP aa rahi hai ya nahi.
  2. `sudo ufw status` check karein ki Port 80 aur 443 open hain.

### 2. "502 Bad Gateway" Error
- **Cause**: Nginx chal raha hai lekin Flask App (Port 5000) band hai.
- **Fix**:
  - `sudo systemctl status elitehosting` run karein.
  - Logs dekhein: `sudo journalctl -u elitehosting -f -n 50`
  - Restart karein: `sudo systemctl restart elitehosting`

### 3. Cloudflare SSL Redirection Loop (Too Many Redirects)
- **Fix**: Cloudflare Dashboard me **SSL/TLS** tab me jayein aur mode ko **"Full"** ya **"Full (Strict)"** par set karein.

---

## 📋 Useful Daily Commands Summary

```bash
# App Status Check:
sudo systemctl status elitehosting

# App Restart:
sudo systemctl restart elitehosting

# App Live Logs:
sudo journalctl -u elitehosting -f -n 100

# Nginx Status & Restart:
sudo systemctl status nginx
sudo systemctl restart nginx

# Docker Containers Status:
docker ps -a
```

🎉 Ab aapka **`https://elitehosting.in`** fully live aur accessible hoga!
