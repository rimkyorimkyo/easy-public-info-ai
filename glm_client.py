import json
import os
import urllib.error
import urllib.request


SYSTEM_PROMPT = """너는 공공정보를 누구나 이해하고 활용할 수 있도록 바꾸는 쉬운 글 전문 작성자다.

입력된 공공 안내문을 쉬운 글로 변환하라.

다음 기준을 준수한다.
1. 원문에 있는 사실과 의미를 정확하게 유지한다.
2. 원문에 없는 사실, 제도, 조건, 수치 등을 추가하지 않는다.
3. 신청 대상, 날짜, 기간, 금액, 전화번호, 주소, 기관명, 자격조건, 제출서류, 신청방법을 임의로 변경하지 않는다.
4. 어려운 단어는 쉬운 말로 바꾸거나 짧게 설명한다.
5. 지나치게 긴 문장은 이해하기 쉽게 나눈다.
6. 한 문장에는 가능한 한 하나의 핵심 내용을 담는다.
7. 복잡한 행정 표현을 자연스러운 일상 표현으로 바꾼다.
8. 중요한 정보를 생략하지 않는다.
9. 필요한 경우 제목과 소제목을 새롭게 구성한다.
10. 정보의 순서를 독자가 이해하고 행동하기 쉬운 순서로 조정한다.
11. 신청 절차가 있다면 단계별로 정리한다.
12. 원문의 의미가 모호한 경우 임의로 해석하거나 확정하지 않는다.
13. 원문의 불확실성이나 예외 조건을 그대로 유지한다.
14. 원문의 핵심 정보가 빠지지 않도록 최종적으로 다시 확인한다.

탐색 용이성, 이해 용이성, 활용 가능성을 적용하되, AI의 분석 과정이나 설명은 출력하지 않는다.
실제 변환된 쉬운 글만 제공한다."""


class GLMConfigurationError(RuntimeError):
    pass


class GLMClient:
    def __init__(self):
        self.api_key = os.getenv("GLM_API_KEY", "").strip()
        self.api_base = os.getenv(
            "GLM_API_BASE",
            "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        ).strip()
        self.model = os.getenv("GLM_MODEL", "glm-4-flash").strip()

    @property
    def is_configured(self):
        return bool(self.api_key)

    def _request(self, text, max_tokens, temperature):
        if not self.is_configured:
            raise GLMConfigurationError("GLM_API_KEY가 설정되지 않았습니다.")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        request = urllib.request.Request(
            self.api_base,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8")).get("error", {})
                detail_message = detail.get("message") if isinstance(detail, dict) else str(detail)
            except Exception:
                detail_message = None
            if exc.code in (401, 403):
                if detail_message:
                    raise GLMConfigurationError(
                        f"API 인증에 실패했습니다. GLM_API_KEY를 확인해 주세요. "
                        f"Zhipu 응답: {detail_message}"
                    )
                raise GLMConfigurationError("API 인증에 실패했습니다. GLM_API_KEY를 확인해 주세요.")
            if exc.code == 429:
                raise RuntimeError("API 요청 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.")
            if exc.code >= 500:
                raise RuntimeError("GLM 서버가 일시적으로 응답하지 않습니다. 잠시 후 다시 시도해 주세요.")
            raise RuntimeError(detail_message or "GLM API 요청 형식에 오류가 있습니다.")
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            raise RuntimeError(f"GLM API 서버에 연결할 수 없습니다. ({reason})")

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            raise RuntimeError("GLM API 응답 형식을 확인하지 못했습니다.")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("GLM API가 빈 응답을 반환했습니다.")
        return content.strip()

    def convert(self, text):
        return self._request(text, max_tokens=4000, temperature=0.2)

    def check_connection(self):
        return self._request(
            "한 단어로 연결 상태를 답해 주세요. 연결되었다면 정상이라고 답하세요.",
            max_tokens=16,
            temperature=0
        )