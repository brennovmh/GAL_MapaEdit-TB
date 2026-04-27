from __future__ import annotations

from html import escape
from pathlib import Path

from extract import FIELD_LABELS, SamplePage


HTML_STYLE = """
@page { size: A4; margin: 10mm; }
body {
  font-family: Arial, sans-serif;
  background: #f2f2f2;
  color: #111;
  margin: 0;
  padding: 12px;
}
.sheet {
  width: 190mm;
  min-height: 277mm;
  margin: 0 auto 12px auto;
  background: #fff;
  box-sizing: border-box;
  padding: 8mm;
  page-break-after: always;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}
.title {
  text-align: center;
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 8px;
}
table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  margin-bottom: 6px;
}
td {
  border: 1px solid #777;
  vertical-align: top;
  padding: 4px;
  font-size: 11px;
}
.label {
  display: block;
  font-weight: 700;
  font-size: 10px;
  margin-bottom: 3px;
}
.value {
  min-height: 18px;
  white-space: pre-wrap;
  outline: none;
}
.value.editable {
  border-bottom: 1px dashed #999;
}
.textarea .value {
  min-height: 72px;
}
.options {
  font-size: 11px;
  line-height: 1.4;
}
@media print {
  body {
    background: #fff;
    padding: 0;
  }
  .sheet {
    box-shadow: none;
    margin: 0;
  }
}
"""


def field_cell(label: str, value: str) -> str:
    safe_label = escape(label)
    safe_value = escape(value or "")
    editable_class = " editable" if not value else ""
    return (
        f"<td><span class='label'>{safe_label}</span>"
        f"<div class='value{editable_class}' contenteditable='true'>{safe_value}</div></td>"
    )


def render_table(items: list[tuple[str, str]]) -> str:
    cells = "".join(field_cell(label, value) for label, value in items)
    return f"<table><tr>{cells}</tr></table>"


def render_options(title: str, options: list[str]) -> str:
    content = " ".join(escape(option) for option in options)
    return (
        "<table><tr><td class='options'>"
        f"<span class='label'>{escape(title)}</span>"
        f"<div class='value' contenteditable='true'>{content}</div>"
        "</td></tr></table>"
    )


def render_textarea(label: str) -> str:
    return (
        "<table class='textarea'><tr><td>"
        f"<span class='label'>{escape(label)}</span>"
        "<div class='value editable' contenteditable='true'></div>"
        "</td></tr></table>"
    )


def render_sample(sample: SamplePage) -> str:
    sections = [
        f"<div class='title'>{escape(sample.get('exame_solicitado') or 'Mapa de Trabalho GAL')}</div>",
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["requisicao", "origem", "data_cadastro", "data_primeiros_sintomas", "codigo"]]),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["paciente", "idade", "sexo", "idade_gestacional"]]),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["requisitante", "municipio", "profissional_saude"]]),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["vacinacao", "data_ultima_dose", "qual_vacina"]]),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["amostra", "material", "localizacao_amostra", "material_clinico", "data_coleta", "hora_coleta"]]),
        render_table(
            [(FIELD_LABELS[key], sample.get(key)) for key in ["data_recebimento", "usou_medicamento", "qual_medicamento", "data_inicio_medicamento", "restrito", "motivo_restricao"]]
        ),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["ri", "kit_lote", "reteste"]]),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["exame_realizado", "nao_conformidade"]]),
        render_table([(FIELD_LABELS[key], sample.get(key)) for key in ["exame_nao_realizado", "exame_cancelado"]]),
        render_options("DNA para Mycobacterium tuberculosis", sample.option_groups["dna_mt"]),
        render_options("Rifampicina", sample.option_groups["rifampicina"]),
        render_options("Complemento", sample.option_groups["complemento"]),
        render_options("Aspecto da Amostra de Escarro", sample.option_groups["aspecto_amostra"]),
        render_textarea("Valor de Referência"),
        render_textarea("Observações"),
    ]
    return f"<section class='sheet'>{''.join(sections)}</section>"


def render_html(samples: list[SamplePage], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(render_sample(sample) for sample in samples)
    html = (
        "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Mapa de Trabalho GAL Editável</title>"
        f"<style>{HTML_STYLE}</style></head><body>{body}</body></html>"
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path
