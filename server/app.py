import uvicorn
import os
import sys

# Ensure root dir is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

def main():
    uvicorn.run("main:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
