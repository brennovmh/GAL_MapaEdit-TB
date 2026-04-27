from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from extract import SamplePage, extract_samples
from render_docx import render_docx
from render_html import render_html


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


@dataclass(slots=True)
class PatientOutput:
    patient_name: str
    page_number: int
    docx_path: Path | None = None
    html_path: Path | None = None


def sanitize_filename(value: str, fallback: str) -> str:
    name = unicodedata.normalize("NFKC", value or "").strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        name = fallback
    if name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"{name}_paciente"
    return name[:120]


def _unique_stem(base_stem: str, used_stems: set[str]) -> str:
    stem = base_stem
    counter = 2
    while stem.lower() in used_stems:
        stem = f"{base_stem}_{counter}"
        counter += 1
    used_stems.add(stem.lower())
    return stem


def build_patient_outputs(
    samples: list[SamplePage],
    output_dir: str | Path,
    *,
    generate_docx: bool = True,
    generate_html: bool = True,
) -> list[PatientOutput]:
    if not generate_docx and not generate_html:
        raise ValueError("Selecione ao menos um formato de saída.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[PatientOutput] = []
    used_stems: set[str] = set()
    for sample in samples:
        patient_name = sample.get("paciente") or f"Paciente pagina {sample.page_number}"
        base_stem = sanitize_filename(patient_name, fallback=f"paciente_pagina_{sample.page_number:03d}")
        stem = _unique_stem(base_stem, used_stems)

        output = PatientOutput(patient_name=patient_name, page_number=sample.page_number)
        if generate_docx:
            output.docx_path = render_docx([sample], output_dir / f"{stem}.docx")
        if generate_html:
            output.html_path = render_html([sample], output_dir / f"{stem}.html")
        outputs.append(output)
    return outputs


def convert_pdf_by_patient(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    generate_docx: bool = True,
    generate_html: bool = True,
) -> list[PatientOutput]:
    samples = extract_samples(input_path)
    return build_patient_outputs(
        samples,
        output_dir,
        generate_docx=generate_docx,
        generate_html=generate_html,
    )
