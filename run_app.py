import sys
import os
from app import app

def main():
    # Ensure the current directory is in the Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    app.run(host='localhost', port=9000, debug=True)

if __name__ == "__main__":
    main()