# VPS Deployment Guide for Expense Tracking System

## 1. Prepare Your VPS

- Update system:
  ```
  sudo apt update && sudo apt upgrade -y
  ```
- Install Python 3, pip, and venv:
  ```
  sudo apt install python3 python3-pip python3-venv -y
  ```
- (Optional) Install Git:
  ```
  sudo apt install git -y
  ```

## 2. Clone Your Project

- Clone your repository:
  ```
  git clone https://github.com/yourusername/your-repo.git
  cd your-repo
  ```

## 3. Set Up Python Environment

- Create and activate a virtual environment:
  ```
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- Install dependencies:
  ```
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

## 4. Configure Environment Variables

- Copy `.env.example` to `.env`:
  ```
  cp .env.example .env
  ```
- Edit `.env` and fill in all production values (WhatsApp API keys, Django secret, DB, etc.):
  ```
  nano .env
  ```

## 5. Django Setup

- Run migrations:
  ```
  python manage.py migrate
  ```
- Create a superuser:
  ```
  python manage.py createsuperuser
  ```
- Collect static files:
  ```
  python manage.py collectstatic
  ```

## 6. Test Locally

- Run the Django server to verify:
  ```
  python manage.py runserver 0.0.0.0:8000
  ```
- Visit `http://your-vps-ip:8000` to check.

## 7. Set Up Gunicorn (Production WSGI Server)

- Install Gunicorn:
  ```
  pip install gunicorn
  ```
- Test Gunicorn:
  ```
  gunicorn expense_tracker.wsgi:application --bind 0.0.0.0:8000
  ```

## 8. Set Up Nginx (Reverse Proxy)

- Install Nginx:
  ```
  sudo apt install nginx -y
  ```
- Configure Nginx:
  ```
  sudo nano /etc/nginx/sites-available/expense_tracker
  ```
  Example config:
  ```
  server {
      listen 80;
      server_name your_domain_or_ip;

      location = /favicon.ico { access_log off; log_not_found off; }
      location /static/ {
          root /path/to/your/project;
      }
      location /media/ {
          root /path/to/your/project;
      }

      location / {
          proxy_pass http://127.0.0.1:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```
- Enable the config:
  ```
  sudo ln -s /etc/nginx/sites-available/expense_tracker /etc/nginx/sites-enabled
  sudo nginx -t
  sudo systemctl restart nginx
  ```

## 9. Set Up Gunicorn as a Systemd Service

- Create a service file:
  ```
  sudo nano /etc/systemd/system/gunicorn.service
  ```
  Example:
  ```
  [Unit]
  Description=gunicorn daemon
  After=network.target

  [Service]
  User=youruser
  Group=www-data
  WorkingDirectory=/path/to/your/project
  ExecStart=/path/to/your/project/.venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/path/to/your/project/gunicorn.sock expense_tracker.wsgi:application

  [Install]
  WantedBy=multi-user.target
  ```
- Start and enable Gunicorn:
  ```
  sudo systemctl start gunicorn
  sudo systemctl enable gunicorn
  ```

## 10. Final Steps

- Open firewall ports if needed (80, 443).
- Set up HTTPS (recommended: use Certbot for free SSL).
- Point your domain to the VPS IP.
- Set up WhatsApp webhook URL in Meta dashboard to `https://yourdomain.com/whatsapp/webhook/`.

---

For any issues, check logs and ensure all environment variables are set correctly.
