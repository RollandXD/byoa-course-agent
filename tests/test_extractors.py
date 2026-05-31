import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent.extractors import extract_docx_text, extract_pptx_text


COURSE_ROOT = ROOT.parent


class ExtractorTests(unittest.TestCase):
    def test_pptx_extraction_finds_experiment_two_requirements(self):
        text = extract_pptx_text(COURSE_ROOT / "Week 13-15.pptx")

        self.assertIn("Experiment 2", text)
        self.assertIn("Bring Your Own Agent", text)
        self.assertIn("2026/06/20", text)
        self.assertIn("function calling", text.lower())

    def test_docx_extraction_finds_previous_report_identity(self):
        text = extract_docx_text(COURSE_ROOT / "综合实践（阶段1）-实验1-于重阳-2024211429.docx")

        self.assertIn("于重阳", text)
        self.assertIn("2024211429", text)
        self.assertIn("https://github.com/RollandXD", text)


if __name__ == "__main__":
    unittest.main()
