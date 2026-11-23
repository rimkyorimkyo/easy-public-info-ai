import csv
import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from analyzer import analyze_text, compare_information
from glm_client import GLMClient, GLMConfigurationError


ROOT = os.path.dirname(os.path.abspath(__file__))
MAX_TEXT_LENGTH = 12000


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError:
        pass


load_env_file(os.path.join(ROOT, ".env"))


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            self.handle_status()
        elif path == "/api/samples":
            self.handle_samples()
        else:
            super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/convert":
            self.handle_convert()
        else:
            self.send_json(404, {"success": False, "error": "요청한 주소를 찾을 수 없습니다."})

    def handle_status(self):
        client = GLMClient()
        if not client.is_configured:
            self.send_json(200, {
                "success": True,
                "api_key": "미설정",
                "status": "not_configured",
                "message": "GLM_API_KEY가 설정되지 않았습니다. 서버 환경변수 또는 .env에 키를 설정하세요.",
                "model": client.model,
            })
            return

        try:
            result = client.check_connection()
            self.send_json(200, {
                "success": True,
                "api_key": "설정됨",
                "status": "connected",
                "message": "GLM API에 연결되었습니다.",
                "model": client.model,
            })
        except GLMConfigurationError as exc:
            self.send_json(200, {
                "success": False,
                "api_key": "설정됨",
                "status": "failed",
                "message": str(exc),
                "model": client.model,
            })
        except Exception as exc:
            self.send_json(200, {
                "success": False,
                "api_key": "설정됨",
                "status": "failed",
                "message": f"API 연결 확인 중 오류가 발생했습니다: {exc}",
                "model": client.model,
            })

    def handle_samples(self):
        csv_path = os.path.join(ROOT, "data", "research_samples.csv")
        samples = []
        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    samples.append({
                        "sample_id": row.get("sample_id", ""),
                        "category": row.get("category", ""),
                        "title": row.get("title", ""),
                        "source": row.get("source", ""),
                        "original_text": row.get("original_text", ""),
                    })
            self.send_json(200, {"success": True, "samples": samples})
        except Exception:
            self.send_json(500, {"success": False, "error": "샘플 자료를 읽지 못했습니다."})

    def handle_convert(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                self.send_json(400, {"success": False, "error": "요청 본문이 없습니다."})
                return
            if content_length > 2_000_000:
                self.send_json(413, {"success": False, "error": "요청 본문이 너무 큽니다."})
                return
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            self.send_json(400, {"success": False, "error": "올바른 JSON 형식으로 요청해 주세요."})
            return

        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            self.send_json(400, {"success": False, "error": "변환할 원문을 입력해 주세요."})
            return
        text = text.strip()
        if len(text) > MAX_TEXT_LENGTH:
            self.send_json(413, {"success": False, "error": f"원문은 최대 {MAX_TEXT_LENGTH:,}자까지 입력할 수 있습니다."})
            return

        client = GLMClient()
        if not client.is_configured:
            self.send_json(503, {
                "success": False,
                "error": "GLM API 키가 설정되지 않았습니다. 서버의 GLM_API_KEY 환경변수를 설정한 뒤 다시 시도해 주세요.",
            })
            return

        try:
            converted = client.convert(text)
            if not converted or not converted.strip():
                self.send_json(502, {"success": False, "error": "AI가 빈 변환 결과를 반환했습니다."})
                return
            original_analysis = analyze_text(text)
            converted_analysis = analyze_text(converted)
            preservation = compare_information(text, converted)
            self.send_json(200, {
                "success": True,
                "original": text,
                "converted": converted,
                "original_analysis": original_analysis,
                "converted_analysis": converted_analysis,
                "preservation": preservation,
            })
        except GLMConfigurationError as exc:
            self.send_json(401, {"success": False, "error": str(exc)})
        except TimeoutError:
            self.send_json(504, {"success": False, "error": "AI 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."})
        except Exception as exc:
            message = str(exc)
            if len(message) > 300:
                message = "AI 서버 요청 중 오류가 발생했습니다."
            self.send_json(502, {"success": False, "error": message})


def run():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))
    server = ThreadingHTTPServer((host, port), RequestHandler)
    print(f"Easy Public Info AI server: http://0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
