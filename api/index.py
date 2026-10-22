import os
import sys

# Ensure application and root directories are in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

pkg_dir = os.path.join(root_dir, 'smart_parking_system')
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from smart_parking_system.app import app

# Export app for Vercel Serverless Function runtime
