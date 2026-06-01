# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Sobre o projeto

Processa vídeos aplicando efeito de Pitch Male (voz masculina) usando `ffmpeg` com o filtro `rubberband`, gera transcrição em SRT usando `faster-whisper`, cria metadados para YouTube usando `spaCy` e `NLTK`, e gera relatório de palavras monitoradas.

## Comandos

```bash
# Instalar dependências e criar diretórios (rodar como root)
/home/user/projetos/macho/install.sh

# Executar
/home/user/projetos/macho/run.sh

# Executar diretamente durante desenvolvimento
python3 /home/user/projetos/macho/src/main.py
```

## Interface

Este projeto é uma aplicação de terminal (CLI). Nunca usar PySide6 ou qualquer biblioteca gráfica. Para TUI, usar `rich` ou `textual`.

## Diretórios de vídeo

| Diretório | Função |
|---|---|
| `/home/user/Videos/gravado/` | Entrada — vídeos a processar |
| `/home/user/Videos/final/<nome_video>/` | Saída — vídeo + legenda + YOUTUBE.txt + report.txt |
| `/home/user/Videos/processado/` | Arquivo — originais processados com sucesso |

## Fluxo de processamento

1. Lê vídeos de `/home/user/Videos/gravado/`
2. Para cada vídeo, cria `/home/user/Videos/final/<stem>/` e aplica o pitch male
3. Pergunta ao usuário: **"Deseja gerar legendas (SRT), YOUTUBE.txt e report.txt?"** — se não, pula para o passo 10
4. Detecta a língua do vídeo via Whisper (lazy — sem consumir os segmentos ainda)
5. Se já existe `LEGENDAS_{língua}.srt`, pula apenas a transcrição — ainda gera YOUTUBE.txt e report.txt com o SRT existente
6. Remove sons não-verbais detectados pelo Whisper (`[tosse]`, `[ruído]`, etc.) e aplica cortes por marcadores de voz — regera o SRT após os cortes (2ª transcrição)
7. Pergunta ao usuário: **"Deseja usar a API da Anthropic para gerar TÍTULO e DESCRIÇÃO?"** — se sim, usa `claude-opus-4-8` via `ANTHROPIC_API_KEY`; se não, usa spaCy + NLTK
8. Gera `YOUTUBE.txt` com título, descrição, palavras-chave e conceitos
9. Gera `report.txt` com tabela de ocorrências das palavras monitoradas (`PALAVRAS_FILTRO`)
10. Move o original para `/home/user/Videos/processado/`

## Módulos Python

| Arquivo | Responsabilidade |
|---|---|
| `src/main.py` | Orquestração do fluxo completo |
| `src/youtube.py` | Geração do `YOUTUBE.txt` com spaCy + NLTK ou API Anthropic |
| `src/report.py` | Geração do `report.txt` com tabela de palavras monitoradas |

`src/__init__.py` existe mas é vazio — os imports entre módulos funcionam porque Python adiciona o diretório do script ao `sys.path` automaticamente. Nunca executar `python3 main.py` de dentro de `src/` sem garantir que `src/` esteja no path.

## Invariantes não-óbvias

- **Generator lazy do Whisper**: `model.transcribe()` retorna `(segments, info)` onde `segments` é um generator consumível apenas uma vez, dentro de `escrever_srt()`. A língua é lida de `info.language` antes do consumo. Iterar `segments` uma segunda vez retornará vazio.
- **Transcrição usa o arquivo processado**: o Whisper roda sobre o vídeo com pitch já aplicado (`arquivo_saida`), não sobre o original.
- **ffmpeg usa `-y`**: sobrescreve arquivos de saída sem confirmação — relevante ao re-processar vídeos que já têm output em `DIR_SAIDA`.
- **ffmpeg copia vídeo sem re-codificação**: `-c:v copy` copia o stream de vídeo intacto na etapa de pitch. Os cortes (`aplicar_cortes`) usam `filter_complex` com `trim`+`concat`, o que re-codifica o vídeo — não usar `-c:v copy` em conjunto com esse filtro.
- **Cortes exigem par de marcadores**: `MARCADOR_INICIO_CORTE` sem `MARCADOR_FIM_CORTE` correspondente é ignorado silenciosamente. Marcadores são buscados por substring no conteúdo do bloco SRT (não igualdade exata), após normalização de caixa e acentos via `unicodedata`.
- **Sons não-verbais**: `detectar_sons_nao_verbais` usa `re.fullmatch(r"\[.*?\]", conteudo)` — só corta blocos SRT cujo texto inteiro seja uma anotação Whisper (ex: `[tosse]`). Blocos mistos (fala + anotação) não são cortados. Os intervalos são mesclados com os cortes de marcador antes de `aplicar_cortes`.
- **Intervalos sobrepostos em `aplicar_cortes`**: usa `pos = max(pos, fim)` para avançar o ponteiro — evita regressão quando um corte está contido dentro de outro (ex: marcador (1,5) + som (2,3)).
- **report.txt gerado antes da retranscrição**: `gerar_report_txt` é chamado com o SRT original (pré-corte) para garantir que as seções CORTES e PALAVRAS usem a mesma timeline. `gerar_youtube_txt` usa o SRT pós-retranscrição (timeline do vídeo final).
- **YOUTUBE.txt não gerado se retranscrição falhar após cortes**: flag `srt_confiavel` evita passar SRT contaminado com marcadores ("início do corte") para a geração de metadados YouTube.
- **SRT existente não bloqueia metadados**: quando `LEGENDAS_{língua}.srt` já existe, a transcrição é pulada mas YOUTUBE.txt e report.txt são gerados normalmente com o SRT em disco.
- **CRLF em SRT**: `detectar_cortes`, `detectar_sons_nao_verbais`, `_parsear_srt` e `_texto_do_srt` normalizam `\r\n` → `\n` antes de processar — SRTs gerados no Windows são aceitos sem erro silencioso.
- **Parser de texto SRT por blocos**: `_texto_do_srt` (youtube.py) e `_parsear_srt` (report.py) filtram o número de sequência por posição (`linhas[0]`), não por `isdigit()` — evita descartar texto numérico legítimo (anos, códigos, etc.).
- **Vídeos com mesmo stem**: aviso exibido antes do loop quando dois arquivos compartilham o mesmo nome base — o segundo pode sobrescrever SRT e metadados do primeiro.
- **WhisperModel em try/except**: modelo inválido (ex: `WHISPER_MODEL=turbo`) exibe mensagem clara e encerra com `sys.exit(1)` em vez de traceback cru.
- **`tmp.replace(saida)`**: `aplicar_cortes` usa `Path.replace()` em vez de `Path.rename()` — substitui o destino atomicamente mesmo que já exista (cross-platform).
- **Título fallback truncado**: `_titulo` trunca o fallback a 15 palavras quando nenhuma sentença curta com palavra-chave é encontrada.
- **`_secao_palavras` pré-compila regex**: padrões de `PALAVRAS_FILTRO` são compilados uma vez fora do loop duplo.
- **Cortes só acontecem com legenda**: se o usuário recusar gerar legenda, nenhum corte é aplicado (sem SRT, sem detecção de marcadores).
- **Falha parcial**: se pitch succeed mas transcrição falha, o arquivo processado permanece em `DIR_SAIDA` mas o original fica em `DIR_ENTRADA` (não é movido).
- **YOUTUBE.txt e report.txt são não-bloqueantes**: falha exibe aviso mas não interrompe o processamento nem impede a movimentação do original.
- **report.txt não é criado quando vazio**: `gerar_report_txt` retorna `(True, "")` sem criar o arquivo quando `PALAVRAS_FILTRO` está vazio e não há cortes — comportamento silencioso intencional.
- **Modelos spaCy são cacheados**: `_cache_modelos` em `youtube.py` evita recarga entre vídeos do mesmo lote.
- **Parser da API Anthropic**: `_titulo_descricao_via_api` suporta `DESCRIÇÃO:` multi-linha — linhas subsequentes sem prefixo após `DESCRIÇÃO:` são acumuladas.
- **Carregamento do .env**: `main.py` carrega `~/.env` primeiro, depois `.env` do projeto. `~/.env` tem precedência (load_dotenv não sobrescreve por padrão).

## Configuração (.env)

| Variável | Padrão | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Chave da API Anthropic (opcional) |
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
| `CORTE_AUTOMATICO` | `1` | `1` ativa o corte automático por marcadores de voz; `0` desativa |
| `REMOVER_SONS_NAO_VERBAIS` | `1` | `1` remove segmentos anotados pelo Whisper como sons não-verbais (ex: `[tosse]`); `0` desativa |
| `MARCADOR_INICIO_CORTE` | `início do corte` | Frase dita para marcar o início de um trecho a cortar |
| `MARCADOR_FIM_CORTE` | `fim do corte` | Frase dita para marcar o fim de um trecho a cortar |

Referência de `PITCH_FATOR` por semitons:

| Semitons | Fator |
|---|---|
| -1 | 0.9439 |
| -2 | 0.8909 |
| -3 | 0.8409 |
| -4 | 0.7937 |

## Geração de metadados YouTube (`src/youtube.py`)

Usa a transcrição (SRT) como fonte e gera `YOUTUBE.txt` com:
- **Título** — sentença com maior densidade de palavras-chave (máx. 15 palavras), obrigatoriamente contendo ao menos uma palavra-chave
- **Descrição** — top 4 sentenças por frequência de palavras-chave, em ordem original
- **Palavras-chave** — top 15 substantivos/adjetivos lematizados, sem stopwords
- **Principais conceitos** — entidades nomeadas (NER) + noun chunks compostos

Quando o usuário opta pela API Anthropic, título e descrição são gerados pelo modelo `claude-opus-4-8`; palavras-chave e conceitos continuam via spaCy + NLTK. O system prompt usa `cache_control: {"type": "ephemeral"}` para prompt caching.

Palavras em `PALAVRAS_EXCLUIR` são removidas de keywords, conceitos, título e descrição.

Língua detectada pelo Whisper → modelo spaCy:

| Língua | Modelo spaCy |
|---|---|
| `pt` | `pt_core_news_sm` |
| `en` | `en_core_web_sm` |
| outras | `en_core_web_sm` (fallback) |

## Whisper

Roda em CPU com quantização int8 (`device="cpu", compute_type="int8"`) e `beam_size=5`. O modelo é carregado uma única vez antes do loop de vídeos (se `fazer_legenda=True`). Para GPU, mudar `device` e `compute_type`. Modelos menores sacrificam precisão por velocidade.

## Extensões de vídeo aceitas

`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.ts` — definidas em `EXTENSOES_VIDEO` em `main.py`.

## Dependências

- `ffmpeg` + `librubberband-dev` (pitch shifting via filtro `rubberband`)
- `rich` (saída no terminal)
- `python-dotenv` (leitura do `.env`)
- `faster-whisper` (transcrição, CPU com `int8`)
- `spacy` + `pt_core_news_sm` + `en_core_web_sm` (NLP para metadados YouTube)
- `nltk` + dados `stopwords`, `punkt`, `punkt_tab`
- `anthropic` (opcional — geração de título/descrição via `claude-opus-4-8`)
