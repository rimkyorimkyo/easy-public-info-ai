import csv
import os
import re
from datetime import datetime


ROOT = os.path.dirname(os.path.abspath(__file__))
SENTENCE_END = re.compile(r"[.!?。！？]+|(?<=[다요함됨됨임])(?:\s|$)")


def load_terms():
    path = os.path.join(ROOT, "data", "terms.csv")
    terms = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                if row.get("difficult_term", "").strip():
                    terms.append(row)
    except OSError:
        pass
    return terms


def count_sentences(text):
    if not text or not text.strip():
        return 0
    normalized = re.sub(r"\r\n?", "\n", text.strip())
    parts = re.split(r"[.!?。！？\n]+", normalized)
    count = sum(1 for part in parts if part.strip())
    if count:
        return count

    sentences = re.findall(r".*?(?:다|요|함|됨|임)(?=\s|$)", normalized)
    if sentences:
        return len(sentences)
    return 1


def analyze_text(text):
    text = text or ""
    char_count = len(text)
    no_space_count = len(re.sub(r"\s", "", text))
    sentence_count = count_sentences(text)
    average_length = round(no_space_count / sentence_count, 1) if sentence_count else 0.0
    terms = load_terms()
    found_terms = []
    difficult_occurrences = 0
    for term in terms:
        difficult = term["difficult_term"].strip()
        if difficult and difficult in text:
            found_terms.append(difficult)
            difficult_occurrences += len(re.findall(re.escape(difficult), text))
    word_count = len(re.findall(r"[가-힣A-Za-z0-9]+", text))
    difficult_ratio = round(difficult_occurrences / word_count * 100, 2) if word_count else 0.0
    difficult_ratio = min(difficult_ratio, 100.0)
    return {
        "character_count": char_count,
        "no_space_count": no_space_count,
        "sentence_count": sentence_count,
        "average_sentence_length": average_length,
        "difficult_term_count": len(found_terms),
        "difficult_term_occurrences": difficult_occurrences,
        "difficult_terms": found_terms,
        "difficult_term_ratio": difficult_ratio,
    }


def normalize_numbers(text):
    normalized = re.sub(r"[,\s]", "", text)
    return normalized


def extract_dates(text):
    patterns = [
        r"\d{4}\s*[년./-]\s*\d{1,2}\s*[월./-]\s*\d{1,2}\s*[일]?",
        r"\d{4}\s*년\s*\d{1,2}\s*월",
        r"\d{1,2}\s*월\s*\d{1,2}\s*일까지?",
        r"\d{1,2}\s*[.~-]\s*\d{1,2}",
    ]
    values = set()
    for pattern in patterns:
        values.update(match.strip() for match in re.findall(pattern, text))
    return sorted(values)


def extract_phones(text):
    return sorted(set(re.findall(r"(?:0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})", text)))


def extract_numbers(text):
    raw = re.findall(r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)", text)
    return sorted(set(normalize_numbers(value) for value in raw))


def compare_items(category, original_items, converted_text):
    confirmed = []
    missing = []
    for item in original_items:
        candidates = [normalize_numbers(item)]
        found = any(normalize_numbers(converted_text).find(candidate) >= 0 for candidate in candidates if candidate)
        (confirmed if found else missing).append(item)
    return {"category": category, "confirmed": confirmed, "missing": missing}


def compare_information(original, converted):
    categories = []
    dates = extract_dates(original)
    phones = extract_phones(original)
    numbers = extract_numbers(original)
    categories.append(compare_items("날짜 및 기간", dates, converted))
    categories.append(compare_items("금액 및 숫자", numbers, converted))
    categories.append(compare_items("전화번호", phones, converted))

    agency_pattern = re.compile(r"([가-힣A-Za-z0-9]+(?:시|도|구|군|읍|면|동|센터|공단|기관|청|부|원))")
    agencies = sorted(set(agency_pattern.findall(original)))
    agencies = [agency for agency in agencies if len(agency) >= 2]
    categories.append(compare_items("기관명", agencies, converted))

    section_patterns = {
        "신청 대상": r"(신청\s*대상|지원\s*대상|대상자)[^.\n。]{0,80}",
        "자격 조건": r"(자격\s*요건|자격\s*조건|충족해야\s*할\s*조건)[^.\n。]{0,100}",
        "제출 서류": r"(제출\s*서류|구비\s*서류|준비할\s*서류)[^.\n。]{0,100}",
        "신청 방법": r"(신청\s*방법|온라인으로\s*신청|방문\s*신청|우편\s*신청)[^.\n。]{0,100}",
        "장소 및 주소": r"(주소|방문\s*장소|접수\s*장소)[^.\n。]{0,100}",
    }
    for label, pattern in section_patterns.items():
        original_matches = sorted(set(re.findall(pattern, original)))
        if original_matches:
            found = [match for match in original_matches if re.sub(r"\s", "", match) in re.sub(r"\s", "", converted)]
            missing = [match for match in original_matches if match not in found]
            categories.append({"category": label, "confirmed": found, "missing": missing})
        else:
            categories.append({"category": label, "confirmed": [], "missing": []})

    return {
        "categories": categories,
        "limit_notice": "이 검사는 단순 문자열 비교를 사용하는 보조 검증입니다. 확인되지 않은 항목은 누락이 확정된 것이 아니며 사람이 다시 확인해야 합니다.",
    }
