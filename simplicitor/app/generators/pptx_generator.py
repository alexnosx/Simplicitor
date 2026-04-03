# simplicitor/app/generators/pptx_generator.py
# Phase 3: PowerPoint generator
from pathlib import Path

from pptx import Presentation
from pptx.util import Pt


# Standard layout indices for the default Blank template
_LAYOUT_TITLE_SLIDE = 0      # "Title Slide" — title + subtitle placeholders
_LAYOUT_TITLE_CONTENT = 1    # "Title and Content" — title + body placeholder
_LAYOUT_SECTION_HEADER = 2   # "Section Header" — title (+ text) placeholder


class PptxGenerator:
    """Generates .pptx files from parsed LLM output (Phase 3)."""

    def generate(self, parsed: dict, output_path: Path) -> Path:
        """Write a PowerPoint presentation from the parsed LLM response structure.

        Args:
            parsed: Validated dict from parse_pptx_response(). Expected keys:
                    ``title`` (str) and ``slides`` (list of slide dicts).
            output_path: Full file path (including filename) to write.

        Returns:
            output_path as a Path.

        Raises:
            OSError: On disk write failure.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prs = Presentation()

        for slide_data in parsed.get("slides", []):
            slide_type = slide_data.get("type", "content")
            slide_title = slide_data.get("title", "")
            bullets = slide_data.get("bullets", [])

            if slide_type == "title":
                self._add_title_slide(prs, slide_title, bullets)
            elif slide_type == "section":
                self._add_section_slide(prs, slide_title)
            else:
                # Default to content layout
                self._add_content_slide(prs, slide_title, bullets)

        prs.save(str(output_path))
        return output_path

    def _add_title_slide(self, prs: Presentation, title: str, bullets: list[str]) -> None:
        """Add a title-slide (layout 0) with a title and optional subtitle."""
        layout = prs.slide_layouts[_LAYOUT_TITLE_SLIDE]
        slide = prs.slides.add_slide(layout)

        # Placeholder index 0 = title, index 1 = subtitle
        if slide.placeholders:
            title_ph = slide.placeholders[0]
            title_ph.text = title

        subtitle_text = bullets[0] if bullets else ""
        if len(slide.placeholders) > 1:
            subtitle_ph = slide.placeholders[1]
            subtitle_ph.text = subtitle_text

    def _add_section_slide(self, prs: Presentation, title: str) -> None:
        """Add a section-header slide (layout 2) with a title only."""
        layout = prs.slide_layouts[_LAYOUT_SECTION_HEADER]
        slide = prs.slides.add_slide(layout)

        if slide.placeholders:
            title_ph = slide.placeholders[0]
            title_ph.text = title

    def _add_content_slide(
        self, prs: Presentation, title: str, bullets: list[str]
    ) -> None:
        """Add a title-and-content slide (layout 1) with a title and bullet list."""
        layout = prs.slide_layouts[_LAYOUT_TITLE_CONTENT]
        slide = prs.slides.add_slide(layout)

        # Set title (placeholder idx 0)
        title_ph = slide.placeholders[0]
        title_ph.text = title

        # Set bullet content (placeholder idx 1)
        if len(slide.placeholders) > 1:
            body_ph = slide.placeholders[1]
            tf = body_ph.text_frame
            tf.clear()

            for idx, bullet_text in enumerate(bullets):
                if idx == 0:
                    # Use the existing first paragraph
                    para = tf.paragraphs[0]
                else:
                    para = tf.add_paragraph()
                para.level = 0
                run = para.add_run()
                run.text = bullet_text
