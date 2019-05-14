# HealthChecker_nginx_swarm
This is a little python2 program that can be used like a service that checks for pre configured docker swarm services and update nginx.conf if any changes are detected.


How to Execute like a service:

Create the file /lib/systemd/system/healthchecker.service

[Unit]
Description=HealthChecker

[Service]
Type=simple
ExecStart=/usr/bin/python2.7 /dados/healthCheck/hc.py
StandardInput=tty-force

[Install]
WantedBy=multi-user.target



systemctl start healthchecker.service

systemctl status healthchecker.service

systemctl enable healthchecker.service