import json
from pathlib import Path


CONFIG_PATH = Path(__file__).parent / "config.json"
def load_config():
    with open(CONFIG_PATH, "r") as file:
        return json.load(file)

def load_available_topics():
    path = Path(__file__).parent / "available_topics.json"

    if not path.exists():
        # fallback to allowed_topics
        return load_config()["ALLOWED_TOPICS"]    

    with open(path, "r") as f:
       data = json.load(f)
       if isinstance(data, list):
           return data
       elif isinstance(data, dict) and "AVAILABLE_TOPICS" in data:
           return data["AVAILABLE_TOPICS"]
       else:
           return load_config()["ALLOWED_TOPICS"]