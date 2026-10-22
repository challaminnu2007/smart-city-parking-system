import os
import sys

# Add smart_parking_system directory to Python path
project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_parking_system')
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from smart_parking_system.app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"============================================================")
    print(f" SMART PARKING MANAGEMENT SYSTEM - SERVER STARTING")
    print(f" Local Address: http://127.0.0.1:{port}")
    print(f"============================================================")
    app.run(host='0.0.0.0', port=port, debug=True)

