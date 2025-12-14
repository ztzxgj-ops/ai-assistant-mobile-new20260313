#!/bin/bash
cd /var/www/ai-assistant
python3 assistant_web.py > server.log 2>&1 &
echo $! > service.pid
sleep 2
ps aux | grep assistant_web | grep -v grep
echo "Service started"
