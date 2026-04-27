from __future__ import annotations

import logging
import re
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pdfplumber
from PIL import Image

try:
    import zxingcpp
except ImportError:  # pragma: no cover - optional fallback
    zxingcpp = None


LOGGER = logging.getLogger(__name__)


FIELD_LABELS = {
    "requisicao": "Requisição",
    "origem": "Origem",
    "data_cadastro": "Data de cadastro",
    "data_primeiros_sintomas": "Data dos Primeiros Sintomas",
    "codigo": "Código",
    "paciente": "Paciente",
    "idade": "Idade",
    "sexo": "Sexo",
    "idade_gestacional": "Idade Gestacional",
    "requisitante": "Requisitante",
    "municipio": "Município",
    "profissional_saude": "Profissional de Saúde",
    "vacinacao": "O Paciente tomou Vacina?",
    "data_ultima_dose": "Data da última dose",
    "qual_vacina": "Qual Vacina?",
    "exame_solicitado": "Exame solicitado",
    "amostra": "Amostra",
    "material": "Material",
    "localizacao_amostra": "Localização da amostra",
    "material_clinico": "Material clínico",
    "data_coleta": "Data de coleta",
    "hora_coleta": "Hora da coleta",
    "data_recebimento": "Data de recebimento",
    "usou_medicamento": "Uso de medicamento",
    "qual_medicamento": "Qual medicamento?",
    "data_inicio_medicamento": "Data que iniciou o uso",
    "restrito": "Restrito",
    "motivo_restricao": "Motivo da restrição",
    "ri": "R.I.",
    "kit_lote": "Kit/lote",
    "reteste": "Reteste",
    "exame_realizado": "Exame realizado",
    "exame_nao_realizado": "Exame não realizado",
    "exame_cancelado": "Exame cancelado",
    "nao_conformidade": "Não conformidade",
    "valor_referencia": "Valor de Referência",
    "observacoes": "Observações",
}


DEFAULT_OPTION_GROUPS = {
    "dna_mt": [
        "( 1 ) Detectável",
        "( 2 ) Não Detectável",
        "( 3 ) Inconclusivo",
        "( 4 ) Abaixo do limite de detecção",
        "( 5 ) Acima do limite de detecção",
        "( 6 ) Quantificado",
    ],
    "rifampicina": [
        "( 1 ) Sensível",
        "( 2 ) Resistente",
        "( 3 ) Inconclusivo",
    ],
    "complemento": [
        "( 1 ) Amostra sanguinolenta",
        "( 2 ) Amostra com resíduos de alimento",
    ],
    "aspecto_amostra": [
        "( 1 ) Saliva",
        "( 2 ) Sanguinolento",
        "( 3 ) Liquefeito",
        "( 4 ) Mucopurulento",
    ],
}


@dataclass(slots=True)
class SamplePage:
    page_number: int
    fields: dict[str, str] = field(default_factory=dict)
    option_groups: dict[str, list[str]] = field(default_factory=lambda: dict(DEFAULT_OPTION_GROUPS))
    source_text: str = ""

    def get(self, key: str) -> str:
        return self.fields.get(key, "").strip()


def normalize_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalize_label_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "", normalized)
    return normalized


KNOWN_LABEL_ALIASES = {
    "usoumedicamento",
    "motivodarestricao",
    "datado receb".replace(" ", ""),
}

KNOWN_LABEL_KEYS = {normalize_label_key(label) for label in FIELD_LABELS.values()} | KNOWN_LABEL_ALIASES


def clean_field_value(value: str) -> str:
    if not value:
        return ""
    if normalize_label_key(value) in KNOWN_LABEL_KEYS:
        return ""
    cleaned_lines: list[str] = []
    for line in value.splitlines():
        compact = normalize_text(line)
        if not compact:
            continue
        normalized = normalize_label_key(compact)
        if normalized in KNOWN_LABEL_KEYS:
            continue
        cleaned_lines.append(compact)
    combined = "\n".join(cleaned_lines).strip()
    if normalize_label_key(combined) in KNOWN_LABEL_KEYS:
        return ""
    return combined


def _looks_like_corrupted_demographic_value(value: str) -> bool:
    normalized = normalize_label_key(value or "")
    compact_value = normalize_text(value or "").upper()
    return (
        "\n" in (value or "")
        or normalized.startswith(("paciente", "idade", "sexo"))
        or compact_value in {"ULINO", "MININO", "MASCU", "FEM"}
    )


def repair_demographic_fields_from_text(fields: dict[str, str], text: str) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    demographic_line = ""
    for index, line in enumerate(lines):
        compact = normalize_label_key(line)
        if "paciente" in compact and "idade" in compact and "sexo" in compact:
            for candidate in lines[index + 1 : index + 5]:
                if normalize_label_key(candidate) in KNOWN_LABEL_KEYS:
                    continue
                demographic_line = candidate
                break
            break

    if not demographic_line:
        return

    match = re.match(
        r"^(?P<paciente>.+?)\s+(?P<idade>\d+\s*(?:Anos?|Meses?|Dias?))\s+(?P<sexo>MASCULINO|FEMININO)\b\s*(?P<idade_gestacional>.*)$",
        demographic_line,
        flags=re.IGNORECASE,
    )
    if not match:
        return

    replacements = {
        "paciente": normalize_text(match.group("paciente")),
        "idade": normalize_text(match.group("idade")),
        "sexo": normalize_text(match.group("sexo")).upper(),
        "idade_gestacional": normalize_text(match.group("idade_gestacional")),
    }
    for key, value in replacements.items():
        if value and (not fields.get(key) or _looks_like_corrupted_demographic_value(fields[key])):
            fields[key] = value


def looks_like_barcode_value(value: str) -> bool:
    compact = re.sub(r"\s+", "", value or "")
    return compact.isdigit() and len(compact) >= 8


def extract_region_text(page: pdfplumber.page.Page, bbox: tuple[float, float, float, float]) -> str:
    text = page.crop(bbox).extract_text(x_tolerance=2, y_tolerance=2, layout=False) or ""
    return clean_field_value(normalize_text(text))


def fallback_extract_pages(pdf_path: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Não foi possível extrair texto do PDF com pdfplumber nem com pdftotext.") from exc
    raw = result.stdout
    pages = [normalize_text(page) for page in raw.split("\f") if normalize_text(page)]
    if not pages:
        raise RuntimeError("O PDF não retornou texto extraível.")
    return pages


def parse_text_page(text: str, page_number: int) -> SamplePage:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fields = {key: "" for key in FIELD_LABELS}
    fields["exame_solicitado"] = next(
        (line for line in lines if "Teste Rápido Molecular" in line),
        "Tuberculose, Teste Rápido Molecular - PCR em Tempo Real",
    )

    def line_after(label: str) -> str:
        for index, line in enumerate(lines):
            if label in line and index + 1 < len(lines):
                return lines[index + 1]
        return ""

    fields["origem"] = line_after("Requisição")
    fields["data_cadastro"] = re.search(r"\b\d{2}/\d{2}/\d{4}\b", fields["origem"] or "") or re.search(
        r"\b\d{2}/\d{2}/\d{4}\b", text
    )
    fields["data_cadastro"] = fields["data_cadastro"].group(0) if fields["data_cadastro"] else ""

    return SamplePage(page_number=page_number, fields=fields, source_text=text)


def _extract_with_pdfplumber(pdf_path: Path) -> list[SamplePage]:
    pages: list[SamplePage] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            raw_text = page.extract_text(layout=True, x_density=2, y_density=2) or ""
            raw_text = normalize_text(raw_text)
            if not raw_text:
                raise RuntimeError(f"Página {page_number} não contém texto extraível.")

            fields = {
                "requisicao": extract_region_text(page, (45, 48, 135, 68)),
                "origem": extract_region_text(page, (138, 48, 275, 68)),
                "data_cadastro": extract_region_text(page, (275, 48, 350, 68)),
                "data_primeiros_sintomas": extract_region_text(page, (350, 48, 450, 68)),
                "codigo": extract_region_text(page, (450, 48, 560, 68)),
                "paciente": extract_region_text(page, (45, 78, 275, 89)),
                "idade": extract_region_text(page, (275, 78, 350, 89)),
                "sexo": extract_region_text(page, (350, 78, 450, 89)),
                "idade_gestacional": extract_region_text(page, (450, 78, 560, 89)),
                "requisitante": extract_region_text(page, (45, 95, 275, 106)),
                "municipio": extract_region_text(page, (275, 95, 450, 106)),
                "profissional_saude": extract_region_text(page, (450, 95, 560, 106)),
                "vacinacao": extract_region_text(page, (45, 112, 275, 123)),
                "data_ultima_dose": extract_region_text(page, (275, 112, 450, 123)),
                "qual_vacina": extract_region_text(page, (450, 112, 560, 123)),
                "exame_solicitado": extract_region_text(page, (45, 135, 560, 152)),
                "amostra": extract_region_text(page, (45, 188, 135, 201)),
                "material": extract_region_text(page, (138, 188, 205, 205)),
                "localizacao_amostra": extract_region_text(page, (205, 188, 303, 205)),
                "material_clinico": extract_region_text(page, (375, 188, 455, 205)),
                "data_coleta": extract_region_text(page, (455, 188, 515, 205)),
                "hora_coleta": extract_region_text(page, (515, 188, 560, 205)),
                "data_recebimento": extract_region_text(page, (45, 219, 128, 232)),
                "usou_medicamento": extract_region_text(page, (128, 203, 190, 219)),
                "qual_medicamento": extract_region_text(page, (190, 203, 275, 219)),
                "data_inicio_medicamento": extract_region_text(page, (275, 203, 385, 219)),
                "restrito": extract_region_text(page, (385, 203, 455, 219)),
                "motivo_restricao": extract_region_text(page, (455, 203, 560, 219)),
                "ri": "",
                "kit_lote": "",
                "reteste": "",
                "exame_realizado": "",
                "exame_nao_realizado": "",
                "exame_cancelado": "",
                "nao_conformidade": "",
                "valor_referencia": "",
                "observacoes": "",
            }
            repair_demographic_fields_from_text(fields, raw_text)
            pages.append(SamplePage(page_number=page_number, fields=fields, source_text=raw_text))
    return pages


def _barcode_center_x(result) -> float:
    left = result.position.top_left.x
    right = result.position.top_right.x
    return (left + right) / 2


def _barcode_center_y(result) -> float:
    top = result.position.top_left.y
    bottom = result.position.bottom_left.y
    return (top + bottom) / 2


def _extract_barcodes_from_page(pdf_path: Path, page_number: int) -> dict[str, str]:
    if zxingcpp is None:
        return {}

    with tempfile.TemporaryDirectory(prefix="gal_barcode_") as temp_dir:
        output_prefix = Path(temp_dir) / f"page_{page_number}"
        subprocess.run(
            [
                "pdftoppm",
                "-r",
                "600",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-singlefile",
                "-png",
                str(pdf_path),
                str(output_prefix),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        image_path = output_prefix.with_suffix(".png")
        image = Image.open(image_path)
        barcodes = zxingcpp.read_barcodes(image)

    if not barcodes:
        return {}

    numeric_barcodes = [barcode for barcode in barcodes if looks_like_barcode_value(barcode.text)]
    top_barcodes = [barcode for barcode in numeric_barcodes if _barcode_center_y(barcode) < image.height * 0.2]
    if not top_barcodes:
        top_barcodes = list(numeric_barcodes)

    top_barcodes.sort(key=_barcode_center_x)
    data: dict[str, str] = {}
    if top_barcodes:
        data["requisicao"] = top_barcodes[0].text
    if len(top_barcodes) > 1:
        data["codigo"] = top_barcodes[-1].text
    return data


def enrich_with_barcodes(samples: list[SamplePage], pdf_path: Path) -> None:
    candidates = [
        sample
        for sample in samples
        if not looks_like_barcode_value(sample.get("requisicao")) or not looks_like_barcode_value(sample.get("codigo"))
    ]
    if not candidates:
        return

    if zxingcpp is None:
        LOGGER.warning("zxing-cpp não está instalado; campos de barcode permanecerão vazios.")
        return

    for sample in candidates:
        try:
            barcode_data = _extract_barcodes_from_page(pdf_path, sample.page_number)
        except Exception as exc:
            LOGGER.warning("Falha ao ler barcode da página %s: %s", sample.page_number, exc)
            continue
        for key, value in barcode_data.items():
            if value and not looks_like_barcode_value(sample.get(key)):
                sample.fields[key] = value


def extract_samples(pdf_path: str | Path) -> list[SamplePage]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")

    try:
        samples = _extract_with_pdfplumber(pdf_path)
    except Exception as exc:
        LOGGER.warning("Falha na extração por coordenadas: %s. Tentando fallback com pdftotext.", exc)
        text_pages = fallback_extract_pages(pdf_path)
        samples = [parse_text_page(text, page_number=i) for i, text in enumerate(text_pages, start=1)]

    non_empty_pages = sum(1 for page in samples if any(value for value in page.fields.values()))
    if non_empty_pages == 0:
        raise RuntimeError("Nenhuma página com dados utilizáveis foi extraída do PDF.")

    enrich_with_barcodes(samples, pdf_path)
    LOGGER.info("Extraídas %s página(s)/amostra(s) de %s.", len(samples), pdf_path.name)
    return samples


def iter_field_items(sample: SamplePage, keys: Iterable[str]) -> list[tuple[str, str]]:
    return [(FIELD_LABELS[key], sample.get(key)) for key in keys]
