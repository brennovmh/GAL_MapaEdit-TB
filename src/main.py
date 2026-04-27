from __future__ import annotations

import argparse
import logging
from pathlib import Path

from converter import convert_pdf_by_patient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Converte o mapa de trabalho do GAL em arquivos editáveis por paciente.")
    parser.add_argument("--input", required=True, help="Caminho do PDF de entrada.")
    parser.add_argument(
        "--output-dir",
        help="Pasta de saída. Se omitida, usa a pasta do caminho informado em --output ou a pasta output/.",
    )
    parser.add_argument(
        "--output",
        help="Compatibilidade com versões anteriores: usa apenas a pasta deste caminho como saída.",
    )
    parser.add_argument(
        "--html-output",
        help="Compatibilidade com versões anteriores: usa apenas a pasta deste caminho como saída.",
    )
    parser.add_argument("--docx-only", action="store_true", help="Gera apenas arquivos DOCX.")
    parser.add_argument("--html-only", action="store_true", help="Gera apenas arquivos HTML.")
    parser.add_argument("--log-level", default="INFO", help="Nível de log. Ex.: INFO, DEBUG.")
    return parser


def resolve_output_dir(args: argparse.Namespace) -> Path:
    if args.output_dir:
        return Path(args.output_dir)
    if args.output:
        return Path(args.output).parent
    if args.html_output:
        return Path(args.html_output).parent
    return Path("output")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    input_path = Path(args.input)
    output_dir = resolve_output_dir(args)
    generate_docx = not args.html_only
    generate_html = not args.docx_only
    if args.docx_only and args.html_only:
        parser.error("Use apenas uma opção entre --docx-only e --html-only.")

    logging.info("Lendo PDF de entrada: %s", input_path)
    logging.info("Gerando saídas por paciente em: %s", output_dir)
    outputs = convert_pdf_by_patient(
        input_path,
        output_dir,
        generate_docx=generate_docx,
        generate_html=generate_html,
    )
    for output in outputs:
        generated_paths = [str(path) for path in (output.docx_path, output.html_path) if path]
        logging.info("Paciente %s: %s", output.patient_name, ", ".join(generated_paths))
    logging.info("Processamento concluído com %s paciente(s)/página(s).", len(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
