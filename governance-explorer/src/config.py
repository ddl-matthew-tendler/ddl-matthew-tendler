import os
def get_api_host() -> str:
    return os.getenv("API_HOST", "https://govqcexploratory.domino.tech")
def get_api_key() -> str:
    return os.getenv("DOMINO_USER_API_KEY", "")
def offline_mode() -> bool:
    return os.getenv("OFFLINE", "false").lower() == "true"
