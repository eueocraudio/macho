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

### Extensões de vídeo aceitas

`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.ts` (definidas em `EXTENSOES_VIDEO` em `main.py`).

### Fluxo
1. Lê vídeos de `/home/user/Videos/gravado/`
2. Para cada vídeo, cria `/home/user/Videos/final/<stem>/` e aplica o pitch male
3. Pergunta ao usuário: **"Deseja gerar legendas (SRT), YOUTUBE.txt e report.txt?"** — se não, pula para o passo 8
4. Detecta a língua do vídeo via Whisper (lazy — sem consumir os segmentos ainda)
5. Se já existe `LEGENDAS_{língua}.srt` para essa língua, pula a transcrição; caso contrário, consome os segmentos e salva o SRT
6. Pergunta ao usuário: **"Deseja usar a API da Anthropic para gerar TÍTULO e DESCRIÇÃO?"** — se sim, usa `claude-opus-4-8` via `ANTHROPIC_API_KEY`; se não, usa spaCy + NLTK
7. Gera `YOUTUBE.txt` com título, descrição, palavras-chave e conceitos
8. Gera `report.txt` com tabela de ocorrências das palavras monitoradas (`PALAVRAS_FILTRO`)
9. Move o original para `/home/user/Videos/processado/`

> `model.transcribe()` retorna `(segments, info)` onde `segments` é um **generator lazy** — só é consumido uma vez, dentro de `escrever_srt()`. A língua é lida de `info.language` antes de consumir o generator. Qualquer tentativa de iterar `segments` uma segunda vez resultará em iterador vazio.
> `YOUTUBE.txt` e `report.txt` são não-bloqueantes: falha exibe aviso mas não interrompe o processamento.
> Os modelos spaCy são cacheados em `_cache_modelos` (módulo `youtube.py`) para evitar recarga entre vídeos do mesmo lote.
> O ffmpeg aplica filtros apenas no stream de áudio; o stream de vídeo é copiado sem re-codificação (`-c:v copy`). Não adicionar filtros de vídeo sem remover esse flag.
> O Whisper roda em CPU com quantização int8 (`device="cpu", compute_type="int8"`) e `beam_size=5`. Para acelerar, aumentar `WHISPER_MODEL` menor sacrifica precisão; hardware com GPU exigiria mudar `device` e `compute_type`.

### Configuração (.env)

Todos os parâmetros ajustáveis ficam em `.env` na raiz do projeto:

| Variável | Padrão | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Chave da API Anthropic (opcional — necessária para gerar título/descrição via IA) |
| `DIR_ENTRADA` | `/home/user/Videos/gravado` | Vídeos a processar |
| `DIR_SAIDA` | `/home/user/Videos/final` | Saída dos vídeos processados |
| `DIR_BACKUP` | `/home/user/Videos/processado` | Destino dos originais |
| `PITCH_FATOR` | `0.9800` | Fator rubberband (ajustável por semitom) |
| `EQ_GRAVES_FREQ` | `180` | Frequência do boost de graves (Hz) |
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

# Executar diretamente durante desenvolvimento (equivalente ao run.sh)
python3 /home/user/projetos/macho/src/main.py
```

O `install.sh` também cria os diretórios de vídeo (`gravado/`, `final/`, `processado/`) caso não existam.

### Carregamento do .env

`main.py` chama `load_dotenv` duas vezes: primeiro `~/.env`, depois `.env` na raiz do projeto. Como `load_dotenv` não sobrescreve variáveis já definidas, `~/.env` tem precedência sobre o `.env` do projeto. Para sobrescrever, deve-se usar `load_dotenv(..., override=True)`.

### Importações e path

`main.py` importa `youtube` e `report` como módulos irmãos (`from youtube import ...`). Isso funciona porque o Python adiciona o diretório do script (`src/`) ao `sys.path` automaticamente ao executar `python3 src/main.py`. Nunca executar `python3 main.py` de dentro de `src/` sem garantir que `src/` esteja no path.

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

Quando o usuário opta pela API Anthropic, título e descrição são gerados pelo modelo `claude-opus-4-8` usando o texto completo do SRT como contexto; palavras-chave e conceitos continuam sendo gerados via spaCy + NLTK. O system prompt já utiliza `cache_control: {"type": "ephemeral"}` para prompt caching.

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
- `ffmpeg` + `librubberband-dev` (processamento de áudio com pitch shifting)
- `rich` (saída no terminal)
- `python-dotenv` (leitura do `.env`)
- `faster-whisper` (transcrição de áudio, roda em CPU com `int8`)
- `spacy` + `pt_core_news_sm` + `en_core_web_sm` (NLP para metadados YouTube)
- `nltk` + dados `stopwords`, `punkt`, `punkt_tab` (stopwords multilíngue)
- `anthropic` (opcional — geração de título/descrição via `claude-opus-4-8`)
