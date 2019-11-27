#!/usr/bin/env python3
import os
import subprocess
import sys
import json

import cgitb
import uuid

print()
print()
cgitb.enable(logdir="/tmp")

script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(os.path.dirname(script_dir))

body = json.loads(sys.stdin.read(int(os.environ["CONTENT_LENGTH"])))
for change in body['push']['changes']:
    for commit in change['commits']:
        tdir = os.path.join(script_dir, 'pquic_repo_%s' % (str(uuid.uuid4())[:8]))
        subprocess.Popen(['/usr/bin/bash', os.path.join(base_dir, 'test_commit.sh'), tdir, commit['hash']])#, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        break  # Only test the head commit
