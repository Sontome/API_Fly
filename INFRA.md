# Mail Receiver System

Domain chính:
hanvietair.com

Website/API:
Nginx + FastAPI

Mail inbound:
upload@inbound.hanvietair.com

Mail routing:
Gmail Forward -> Postfix -> receiver.py
# DNS

mail2.hanvietair.com
A -> VPS_IP

inbound.hanvietair.com
MX 10 mail2.hanvietair.com
# Paths

Source code:
/root/API_Fly/

Mail receiver runtime:
/opt/mail_receiver/

Attachments:
/data/inbound_mail/YYYY/MM/DD

Logs:
/data/inbound_logs/

Receiver:
/opt/mail_receiver/receiver.py

Cleanup script:
/opt/mail_receiver/cleanup_mail.sh
# Postfix

Aliases:
/etc/aliases

Current alias:

upload: "|/opt/mail_receiver/venv/bin/python /opt/mail_receiver/receiver.py"

Apply aliases:

sudo newaliases
sudo systemctl restart postfix
# Python Venv

Path:
/opt/mail_receiver/venv

Activate:
source /opt/mail_receiver/venv/bin/activate

Install package:
pip install -r requirements.txt
# Cron

Run cleanup every day at 1AM

0 1 * * * /opt/mail_receiver/cleanup_mail.sh >> /data/inbound_logs/cleanup.log 2>&1
# Supabase

Table:
inbound_email

Stored fields:

sender_name
sender_email
subject
file_name
file_path
status
created_at
# Flow

1. Gmail nhận mail
2. Gmail auto forward
3. VPS Postfix receive
4. Postfix gọi receiver.py
5. receiver.py:
   - parse sender
   - parse subject
   - save attachment
   - insert Supabase
6. cleanup cron auto delete old files
# Deploy

Update API:

bash /root/update.sh

update.sh:
- git pull
- restart uvicorn
- copy receiver.py
- copy .env
- restart postfix
# Debug

Mail log:
tail -f /var/log/mail.log

Receiver debug:
tail -f /data/inbound_logs/mail_debug.log

Receiver error:
tail -f /data/inbound_logs/mail_error.log


Gmail
  ↓
Forward
  ↓
Postfix
  ↓
receiver.py
  ↓
Supabase + Filesystem

