from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


DRAWING_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
PRESENTATION_NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _normalise_whitespace(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_pptx_text(path: str | Path) -> str:
    """Extract slide text from a PPTX file in presentation order."""
    pptx_path = Path(path)
    with zipfile.ZipFile(pptx_path) as archive:
        presentation = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
        rels = ElementTree.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
        rid_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall(".//rel:Relationship", PRESENTATION_NS)
        }

        sections: list[str] = []
        for index, slide_id in enumerate(presentation.findall(".//p:sldId", PRESENTATION_NS), 1):
            rel_id = slide_id.attrib[f"{{{PRESENTATION_NS['r']}}}id"]
            target = rid_to_target[rel_id]
            slide_path = target if target.startswith("ppt/") else f"ppt/{target}"
            slide = ElementTree.fromstring(archive.read(slide_path))
            text_runs = [
                (node.text or "").strip()
                for node in slide.findall(".//a:t", DRAWING_NS)
                if (node.text or "").strip()
            ]
            if text_runs:
                sections.append(f"[Slide {index}]\n" + "\n".join(text_runs))

    return _normalise_whitespace("\n\n".join(sections))


def extract_docx_text(path: str | Path) -> str:
    """Extract paragraph text from a DOCX file."""
    docx_path = Path(path)
    with zipfile.ZipFile(docx_path) as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))

    paragraphs: list[str] = []
    for paragraph in document.findall(".//w:p", WORD_NS):
        pieces = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)]
        line = "".join(pieces).strip()
        if line:
            paragraphs.append(line)
    return _normalise_whitespace("\n".join(paragraphs))

