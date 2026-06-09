import io
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from byoa_agent import ui


def render_markdown(text: str) -> str:
    out = io.StringIO()
    printer = ui.MarkdownPrinter(color=False, out=out)
    printer.feed(text)
    printer.finish()
    return out.getvalue()


class MarkdownRenderTests(unittest.TestCase):
    def test_headers_get_decorated_and_hashes_stripped(self):
        rendered = render_markdown("# 一级标题\n## 二级标题\n### 三级标题\n")

        self.assertIn("◆ 一级标题", rendered)
        self.assertIn("◇ 二级标题", rendered)
        self.assertIn("三级标题", rendered)
        self.assertNotIn("#", rendered)

    def test_inline_markers_are_stripped(self):
        rendered = render_markdown("**粗体** 与 `代码` 与 *斜体*\n")

        self.assertIn("粗体 与 代码 与 斜体", rendered)
        self.assertNotIn("**", rendered)
        self.assertNotIn("`", rendered)

    def test_links_show_text_and_url(self):
        rendered = render_markdown("[DeepSeek](https://api.deepseek.com)\n")

        self.assertIn("DeepSeek (https://api.deepseek.com)", rendered)

    def test_bullets_become_dots(self):
        rendered = render_markdown("- 第一项\n  - 嵌套项\n1. 编号项\n")

        self.assertIn("• 第一项", rendered)
        self.assertIn("  • 嵌套项", rendered)
        self.assertIn("1. 编号项", rendered)

    def test_code_blocks_get_borders_and_raw_content(self):
        rendered = render_markdown("```python\nx = 1  # **不渲染**\n```\n")
        lines = rendered.splitlines()

        self.assertTrue(lines[0].startswith("  ╭─── python"))
        self.assertIn("  │ x = 1  # **不渲染**", lines[1])
        self.assertTrue(lines[2].startswith("  ╰"))

    def test_table_separator_becomes_rule_and_pipes_restyled(self):
        rendered = render_markdown("| 工具 | 用途 |\n|---|---|\n| read_file | 读文件 |\n")

        self.assertIn("│ 工具 │ 用途 │", rendered)
        self.assertNotIn("|---|", rendered)

    def test_streaming_partial_line_is_held_until_finish(self):
        out = io.StringIO()
        printer = ui.MarkdownPrinter(color=False, out=out)

        printer.feed("流式输出没有换行")
        self.assertEqual(out.getvalue(), "")
        self.assertTrue(printer.midline)

        printer.finish()
        self.assertIn("流式输出没有换行", out.getvalue())
        self.assertFalse(printer.midline)

    def test_flush_emits_partial_line_before_tool_output(self):
        out = io.StringIO()
        printer = ui.MarkdownPrinter(color=False, out=out)
        printer.feed("我先读取")

        printer.flush()

        self.assertIn("我先读取", out.getvalue())


class UiHelperTests(unittest.TestCase):
    def test_display_width_counts_cjk_as_two_cells(self):
        self.assertEqual(ui.display_width("中a"), 3)
        self.assertEqual(ui.display_width("abc"), 3)

    def test_banner_lines_align_for_cjk_content(self):
        text = ui.banner("deepseek-v4-flash", "/tmp/课程目录", 11, color=False)
        lines = text.splitlines()

        widths = {ui.display_width(line) for line in lines}
        self.assertEqual(len(widths), 1, f"banner lines are uneven: {lines}")
        self.assertIn("BYOA Code", text)
        self.assertIn("deepseek-v4-flash", text)

    def test_colorize_diff_keeps_text_without_color(self):
        diff = "+added\n-removed\n@@ -1 +1 @@"

        self.assertEqual(ui.colorize_diff(diff, color=False), diff)

    def test_tool_result_line_marks_command_success(self):
        line = ui.tool_result_line('{"exit_code": 0, "stdout": "", "stderr": ""}', color=False)

        self.assertIn("✓ exit 0", line)

    def test_summarized_arguments_escape_newlines(self):
        summary = ui.summarize_arguments({"content": "第一行\n第二行"})

        self.assertNotIn("\n", summary)
        self.assertIn("⏎", summary)


if __name__ == "__main__":
    unittest.main()
