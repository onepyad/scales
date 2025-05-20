[Unit]
Description=Flask API service on 5000 port
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/sbin/wsh/api.py
Restart=always
User=scales
Group=scales

[Install]
WantedBy=multi-user.target
