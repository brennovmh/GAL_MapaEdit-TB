# GAL Mapa Editável

Automação em Python para converter o PDF de mapa de trabalho do GAL em versões editáveis em `DOCX` e `HTML`, preservando a estrutura operacional por amostra. Cada página/amostra é exportada como arquivos separados, usando o nome do paciente como nome do arquivo.

## Estrutura

```text
gal_mapa_editavel/
  input/
    GAL - Impressão de Mapa de Trabalho.pdf
  output/
  src/
    extract.py
    render_docx.py
    render_html.py
    converter.py
    gui.py
    main.py
  requirements.txt
  README.md
```

No workspace atual, o projeto está na raiz deste diretório e o PDF de validação foi copiado para [input/GAL - Impressão de Mapa de Trabalho.pdf](/mnt/fb9227d1-ba4c-4a6d-b0c1-3b1224e3b4ea/brenno/GAL/input/GAL%20-%20Impress%C3%A3o%20de%20Mapa%20de%20Trabalho.pdf).

## Como instalar

```bash
python3 -m pip install -r requirements.txt
```

## Como executar

```bash
python3 src/main.py \
  --input "input/GAL - Impressão de Mapa de Trabalho.pdf" \
  --output-dir "output"
```

O comando gera um `.docx` e um `.html` para cada paciente. O nome base de cada arquivo é o nome do paciente extraído do PDF.

Também é possível gerar apenas um dos formatos:

```bash
python3 src/main.py \
  --input "input/GAL - Impressão de Mapa de Trabalho.pdf" \
  --output-dir "output" \
  --docx-only
```

## Interface gráfica

Para abrir a interface gráfica:

```bash
python3 src/gui.py
```

No Windows, o mesmo comando pode ser executado com `python`:

```bat
python src\gui.py
```

A tela permite selecionar o PDF de entrada, escolher a pasta de saída e marcar se deseja gerar `DOCX`, `HTML` ou ambos.

## Criar executável para Windows

O executável deve ser criado em uma máquina Windows. Depois disso, a pasta gerada pode ser copiada para um pen drive e executada em outro computador Windows sem instalar Python.

Pré-requisitos na máquina que vai gerar o executável:

- Windows 10 ou superior.
- Python 3.11 ou superior instalado.
- Durante a instalação do Python, marcar a opção `Add python.exe to PATH`.
- Acesso à internet apenas no momento de gerar o executável, para instalar as dependências.

Passos:

1. Copie a pasta inteira deste projeto para a máquina Windows.
2. Dê duplo clique em `build_windows.bat`.
3. Aguarde o processo terminar.
4. Copie para o pen drive a pasta:

```text
dist\GAL_Mapas_Editaveis
```

Para testar em outra máquina, abra essa pasta e execute:

```text
GAL_Mapas_Editaveis.exe
```

Importante: copie a pasta inteira `GAL_Mapas_Editaveis`, não apenas o `.exe`, porque o modo portátil mantém bibliotecas auxiliares ao lado do executável.

Observação: a leitura de códigos de barras é uma etapa auxiliar. Se algum computador bloquear componentes empacotados pelo antivírus ou política local, o programa ainda pode gerar os arquivos, mas alguns campos de código/requisição podem ficar vazios.

## Estratégia adotada

O pipeline evita conversão cega de PDF para Word. Em vez disso:

1. Extrai o texto do PDF por página com `pdfplumber`
2. Usa coordenadas fixas por região para capturar os campos principais, assumindo o layout estável do GAL
3. Usa leitura de barcode para recuperar `Requisição` e `Código` quando esses campos não vêm como texto embutido no PDF
4. Reconstroi cada página em um `DOCX` separado, com tabelas e bordas
5. Gera também uma versão `HTML` separada por amostra, com áreas `contenteditable`
6. Mantém campos operacionais vazios como células editáveis para preenchimento durante a rotina

Há fallback para `pdftotext` quando a extração principal falha, mas a reconstrução mais fiel depende da estratégia por coordenadas.

## Saídas

- `DOCX`: melhor integração com Word e LibreOffice
- `HTML`: tende a ficar mais fiel visualmente em alguns cenários e é útil como alternativa de edição
- Os arquivos são salvos individualmente por paciente. Nomes inválidos no Windows são sanitizados automaticamente

## Limitações esperadas

- A fidelidade visual depende da consistência do PDF de origem. Se o sistema GAL mudar o layout, os recortes por coordenada precisarão de ajuste
- `DOCX` recriado por tabela preserva a organização do formulário, mas não replica 100% da tipografia e microespaçamentos do PDF
- Campos originalmente vazios no PDF permanecem vazios e editáveis no `DOCX` e no `HTML`. Isso é intencional para uso operacional
- O HTML é editável no navegador, mas salvar alterações depende do editor utilizado. Para rotina formal, o `DOCX` tende a ser mais prático
- PDFs digitalizados sem texto embutido exigiriam OCR, o que não faz parte desta primeira versão

## Ajustes futuros...

- Refinar as coordenadas por tipo de exame
- Criar templates específicos por exame
- Adicionar exportação intermediária em JSON para auditoria e teste

