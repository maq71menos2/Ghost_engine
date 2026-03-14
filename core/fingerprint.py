import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Prioridad: Los más fáciles de capturar primero
FINGERPRINTS = [
    {"service": "AWS S3", "pattern": "NoSuchBucket", "status": "VULN_EASY"},
    {"service": "Heroku", "pattern": "No such app", "status": "VULN_EASY"},
    {"service": "Surge.sh", "pattern": "project not found", "status": "VULN_EASY"},
    {"service": "GitHub Pages", "pattern": "There isn't a GitHub Pages site here", "status": "VULN_VERIFY_RISK"},
    {"service": "Ghost.io", "pattern": "The thing you were looking for is no longer here", "status": "VULN_EASY"}
]

def check_vulnerability(domain):
    try:
        # Probamos con HTTP y HTTPS para no perder nada
        url = f"http://{domain}"
        response = requests.get(url, timeout=5, verify=False, allow_redirects=True)
        content = response.text

        for fp in FINGERPRINTS:
            if fp["pattern"] in content:
                return {"vulnerable": True, "service": fp["service"], "priority": fp["status"]}
        
        return {"vulnerable": False, "service": None, "priority": "SAFE"}
    except:
        return {"vulnerable": False, "service": None, "priority": "ERROR"}
