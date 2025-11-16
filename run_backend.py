#!/usr/bin/env python3
"""
Run only the backend server (for use with Next.js frontend)
"""
from backend.server import backend_app

if __name__ == '__main__':
    print("Starting backend server on http://localhost:8000")
    print("Frontend should be running separately on http://localhost:3000")
    backend_app.run(host='0.0.0.0', port=8000, debug=True)

