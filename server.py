import os
import json
import re
import shutil
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = 8080
CAMPAIGNS_DIR = "campaigns"
os.makedirs(CAMPAIGNS_DIR, exist_ok=True)

if os.path.exists("campaign.json") and not os.path.exists(os.path.join(CAMPAIGNS_DIR, "default.json")):
    try:
        shutil.copyfile("campaign.json", os.path.join(CAMPAIGNS_DIR, "default.json"))
    except Exception:
        pass

def sanitize_id(cid: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9_\-]', '', cid)
    return cleaned if cleaned else "default"

class DnDServer(SimpleHTTPRequestHandler):
    def address_string(self):
        return self.client_address[0]

    # Намертво отрубаем кэш для ВСЕХ файлов (включая index.html)
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _get_campaign_path(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        cid = sanitize_id(qs.get("id", ["default"])[0])
        return os.path.join(CAMPAIGNS_DIR, f"{cid}.json")
		
    def do_GET(self):
        parsed = urlparse(self.path)
        
   # Список всех существующих кампаний
        if parsed.path == "/api/campaigns":
            files = []
            if os.path.exists(CAMPAIGNS_DIR):
                for f in os.listdir(CAMPAIGNS_DIR):
                    if f.endswith(".json"):
                        files.append(f[:-5])
            files.sort()

            payload = json.dumps(files, ensure_ascii=False).encode("utf-8")
            
            # Прямая улика: печатаем в черное окно, что именно сервер шлет клиенту
            print(f"[API] Отправляю список для {self.client_address[0]}: {files}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload))) # <-- Сообщаем точный размер
            self.end_headers()
            self.wfile.write(payload)
            return

        elif parsed.path == "/api/campaign":
		
            parsed = urlparse(self.path)
            if parsed.path == "/api/campaign":
                filepath = self._get_campaign_path()
                if os.path.exists(filepath):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    with open(filepath, "rb") as f:
                        self.wfile.write(f.read())
                    print(f"[GET] Отдан файл: {filepath}")
                else:
                    self.send_response(404)
                    self.end_headers()
                    print(f"[GET] Файл не найден (404): {filepath}")
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/campaign":
            filepath = self._get_campaign_path()
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"saved"}')
                print(f"[POST] УСПЕШНО ЗАПИСАН: {filepath} ({length} байт)")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                print(f"[POST] Ошибка: {e}")
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DnDServer)
    print(f"Сервер запущен. Порт: {PORT}")
    print(f"Сейвы хранятся в папке: {os.path.abspath(CAMPAIGNS_DIR)}")
    server.serve_forever()