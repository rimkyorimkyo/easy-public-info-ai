import unittest

from analyzer import analyze_text, count_sentences, compare_information


class AnalyzerTest(unittest.TestCase):
    def test_empty_text_is_safe(self):
        result = analyze_text("")
        self.assertEqual(result["character_count"], 0)
        self.assertEqual(result["sentence_count"], 0)
        self.assertEqual(result["average_sentence_length"], 0)
        self.assertEqual(result["difficult_term_ratio"], 0)

    def test_korean_sentence_analysis(self):
        text = "신청기한은 2026년 12월 31일까지입니다. 구비서류를 준비하세요."
        result = analyze_text(text)
        self.assertEqual(count_sentences(text), 2)
        self.assertGreater(result["character_count"], 0)
        self.assertGreater(result["difficult_term_count"], 0)

    def test_information_comparison(self):
        original = "신청 기간은 2026년 12월 31일까지입니다. 문의처는 02-123-4567입니다."
        converted = "신청할 수 있는 마지막 날짜는 2026년 12월 31일까지입니다."
        result = compare_information(original, converted)
        categories = {item["category"]: item for item in result["categories"]}
        self.assertIn("2026년 12월 31일", categories["날짜 및 기간"]["confirmed"])
        self.assertTrue(categories["전화번호"]["missing"])


if __name__ == "__main__":
    unittest.main()
