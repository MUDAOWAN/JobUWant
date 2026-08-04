#!/usr/bin/env bash
set -euo pipefail
export PATH=/home/votally/projects/JobUWant/webapp/.tools/node/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /home/votally/projects/JobUWant/webapp/frontend
exec npm run start -- --hostname 0.0.0.0 --port 3000
