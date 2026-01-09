#!/usr/bin/env python3
import sys
import subprocess
import os

# Proxy to the system python or a specific project python
# For now, as requested, pass to system python
subprocess.run([sys.executable] + sys.argv[1:])
