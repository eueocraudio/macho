# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Linguagem de programação

Use Python por padrão em todo código novo, scripts e exemplos. Se o usuário nomear outra linguagem explicitamente, use ela. Sempre invocar o interpretador como `python3` e o gerenciador de pacotes como `pip3`. Sempre usar a flag `--break-system-packages` ao executar `pip3`.

## Idioma

- Comentários no código, regras e documentação: em português
- Nomes de classes, arquivos, variáveis e funções: em inglês
- Responder sempre em português

## Estrutura de diretórios

Todo código novo vai em `src/`, a não ser que outro diretório seja indicado explicitamente.

## Execução de scripts

Ao executar arquivos `.sh` com permissão de execução, usar sempre o caminho completo do executável (ex: `/home/user/projetos/macho/run.sh`).

## Regras específicas para Python

Todas as regras abaixo se aplicam exclusivamente a código Python:

### Interface

Este projeto é uma aplicação de terminal (CLI/TUI). Nunca usar PySide6 ou qualquer biblioteca gráfica. Para TUI, usar `rich` ou `textual`.

### Estilo de código
- Terminar todas as linhas de instrução com `;`
- Usar 4 espaços para indentação (nunca TAB)

## Sobre o projeto

Processa vídeos aplicando efeito de Pitch Male (voz masculina) usando `ffmpeg` com o filtro `rubberband`, gera transcrição em SRT usando `faster-whisper`, cria metadados para YouTube usando `spaCy` e `NLTK`, e gera relatório de palavras monitoradas.

### Diretórios de vídeo
| Diretório | Função |
|---|---|
| `/home/user/Videos/gravado/` | Entrada — vídeos a processar |
| `/home/user/Videos/final/<nome_video>/` | Saída — vídeo + legenda + YOUTUBE.txt + report.txt |
| `/home/user/Videos/processado/` | Arquivo — originais processados com sucesso |

### Fluxo
1. Lê vídeos de `/home/user/Videos/gravado/`
2. Para cada vídeo, cria `/home/user/Videos/final/<stem>/` e aplica o pitch male
3. Detecta a língua do vídeo via Whisper (lazy — sem consumir os segmentos ainda)
4. Se já existe `LEGENDAS_{língua}.srt` para essa língua, pula a transcrição
5. Caso contrário, consome os segmentos e salva o SRT
6. Gera `YOUTUBE.txt` com título, descrição, palavras-chave e conceitos via spaCy + NLTK
7. Gera `report.txt` com tabela de ocorrências das palavras monitoradas (`PALAVRAS_FILTRO`)
8. Move o original para `/home/user/Videos/processado/`

> A detecção de língua e a transcrição usam o mesmo `model.transcribe()` — não há chamada dupla ao modelo.
> `YOUTUBE.txt` e `report.txt` são não-bloqueantes: falha exibe aviso mas não interrompe o processamento.

### Configuração (.env)

Todos os parâmetros ajustáveis ficam em `.env` na raiz do projeto:

| Variável | Padrão | Descrição |
|---|---|---|
| `DIR_ENTRADA` | `/home/user/Videos/gravado` | Vídeos a processar |
| `DIR_SAIDA` | `/home/user/Videos/final` | Saída dos vídeos processados |
| `DIR_BACKUP` | `/home/user/Videos/processado` | Destino dos originais |
| `PITCH_FATOR` | `0.8909` | Fator rubberband (-2 semitons) |
| `EQ_GRAVES_FREQ` | `150` | Frequência do boost de graves (Hz) |
| `EQ_GRAVES_WIDTH` | `100` | Largura de banda do boost (Hz) |
| `EQ_GRAVES_GAIN` | `2` | Ganho do boost de graves (dB) |
| `EQ_METAL_FREQ` | `3500` | Frequência do corte anti-metálico (Hz) |
| `EQ_METAL_WIDTH` | `1000` | Largura de banda do corte (Hz) |
| `EQ_METAL_GAIN` | `-3` | Ganho do corte anti-metálico (dB) |
| `WHISPER_MODEL` | `small` | Modelo Whisper: `tiny`, `base`, `small`, `medium`, `large` |
| `PALAVRAS_FILTRO` | — | Palavras monitoradas no `report.txt`, separadas por vírgula |
| `PALAVRAS_EXCLUIR` | — | Palavras banidas do `YOUTUBE.txt`, separadas por vírgula |

Referência de `PITCH_FATOR` por semitons:

| Semitons | Fator |
|---|---|
| -1 | 0.9439 |
| -2 | 0.8909 |
| -3 | 0.8409 |
| -4 | 0.7937 |

### Comandos
```bash
# Instalar dependências e criar diretórios (rodar como root)
/home/user/projetos/macho/install.sh

# Executar
/home/user/projetos/macho/run.sh
```

O `install.sh` também cria os diretórios de vídeo (`gravado/`, `final/`, `processado/`) caso não existam.

### Módulos Python

| Arquivo | Responsabilidade |
|---|---|
| `src/main.py` | Orquestração do fluxo completo |
| `src/youtube.py` | Geração do `YOUTUBE.txt` com spaCy + NLTK |
| `src/report.py` | Geração do `report.txt` com tabela de palavras monitoradas |

### Geração de metadados YouTube (`src/youtube.py`)

Usa a transcrição (SRT) como fonte e gera `YOUTUBE.txt` com:
- **Título** — sentença com maior densidade de palavras-chave (máx. 15 palavras), obrigatoriamente contendo ao menos uma palavra-chave
- **Descrição** — top 4 sentenças por frequência de palavras-chave, em ordem original
- **Palavras-chave** — top 15 substantivos/adjetivos lematizados, sem stopwords
- **Principais conceitos** — entidades nomeadas (NER) + noun chunks compostos

Palavras em `PALAVRAS_EXCLUIR` são removidas de keywords, conceitos, título e descrição.

Língua detectada pelo Whisper → modelo spaCy correspondente:

| Língua | Modelo spaCy |
|---|---|
| `pt` | `pt_core_news_sm` |
| `en` | `en_core_web_sm` |
| outras | `en_core_web_sm` (fallback) |

### Relatório de palavras (`src/report.py`)

Pesquisa as palavras de `PALAVRAS_FILTRO` no SRT usando `\b` (word boundary) e gera `report.txt` com tabela de ocorrências no formato:

```
+-----------+--------------+
| PALAVRA   | TEMPO        |
+-----------+--------------+
| bosta     | 00:01:23.000 |
+-----------+--------------+
```

### Dependências
- `ffmpeg` (com suporte a `librubberband`)
- `rich` (saída no terminal)
- `python-dotenv` (leitura do `.env`)
- `faster-whisper` (transcrição de áudio, roda em CPU com `int8`)
- `spacy` + `pt_core_news_sm` + `en_core_web_sm` (NLP para metadados YouTube)
- `nltk` + dados `stopwords`, `punkt`, `punkt_tab` (stopwords multilíngue)
