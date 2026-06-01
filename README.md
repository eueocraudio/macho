# Cráudio Macho 🎙️

> Criado por [Cráudio](https://www.youtube.com/@eueocraudio)

Você gravou um vídeo, mas sua voz ficou fininha demais? Esse script resolve isso.

Ele pega todos os vídeos de uma pasta, aplica um efeito de voz masculina (mais grave, mais encorpada), corta automaticamente os trechos que você marcou durante a gravação, gera a transcrição automática em SRT, prepara um arquivo de texto com título, descrição e palavras-chave prontos para colar no YouTube, e ainda gera um relatório de palavras que você queira monitorar.

---

## O que ele faz, exatamente?

Para cada vídeo encontrado na pasta de entrada:

1. Aplica o efeito de **Pitch Male** na voz (usando ffmpeg com rubberband)
2. Salva o vídeo novo em uma pasta separada
3. Pergunta se você quer gerar legendas, YOUTUBE.txt e report.txt — se não, pula direto para o passo 10
4. Detecta automaticamente o idioma do vídeo
5. Gera um arquivo de **legendas `.srt`** (usando Whisper) — se já existir para esse idioma, pula
6. Remove automaticamente **sons não-verbais** detectados pelo Whisper (ex: `[tosse]`, `[ruído]`) e **trechos marcados por voz** durante a gravação ("início do corte" / "fim do corte") — regera a legenda com os tempos corretos
7. Pergunta se você quer usar a **API da Anthropic** para gerar o título e a descrição — se não, usa análise de texto local (spaCy + NLTK)
8. Gera um arquivo **`YOUTUBE.txt`** com título, descrição, palavras-chave e principais conceitos
9. Gera um arquivo **`report.txt`** com os cortes realizados e as ocorrências das palavras monitoradas
10. Move o vídeo original para uma pasta de "já processados"

---

## Instalação

Você vai precisar rodar o script de instalação como **root**:

```bash
/home/user/projetos/macho/install.sh
```

Ele vai:
- Instalar o `ffmpeg`, `librubberband-dev` e o `python3` via apt
- Instalar todas as bibliotecas Python necessárias
- Baixar os modelos de linguagem (spaCy em português e inglês) e os dados do NLTK
- Criar as pastas de vídeo se ainda não existirem

---

## Configuração

Antes de rodar, dá uma olhada no arquivo `.env` na raiz do projeto. Ele está todo comentado em português e explica o que cada coisa faz.

Os pontos principais que você pode querer ajustar:

**Pitch muito grave ou muito fino?**
Mude o `PITCH_FATOR`. Quanto menor o número, mais grave fica:

```
PITCH_FATOR=0.9800   # padrão (levemente mais grave)
PITCH_FATOR=0.9439   # -1 semitom
PITCH_FATOR=0.8909   # -2 semitons
PITCH_FATOR=0.8409   # -3 semitons (grave)
PITCH_FATOR=0.7937   # -4 semitons (muito grave)
```

**Transcrição lenta demais?**
Troque o modelo do Whisper por um menor:

```
WHISPER_MODEL=tiny    # mais rápido, menos preciso
WHISPER_MODEL=base    # bom equilíbrio para textos simples
WHISPER_MODEL=small   # mais leve
WHISPER_MODEL=medium  # padrão
WHISPER_MODEL=large   # máxima precisão, mais lento
```

**Quer monitorar palavras específicas?**
Coloque-as em `PALAVRAS_FILTRO` separadas por vírgula. Elas vão aparecer no `report.txt` com o tempo exato em que foram ditas:

```
PALAVRAS_FILTRO=corta,bosta,coleguinha
```

**Quer banir palavras do YOUTUBE.txt?**
Use `PALAVRAS_EXCLUIR`. Essas palavras não vão aparecer em nenhuma parte do título, descrição, palavras-chave ou conceitos:

```
PALAVRAS_EXCLUIR=merda,corta,coleguinha,eu
```

**Quer desativar o corte automático por marcadores de voz?**
Por padrão o script detecta "início do corte" e "fim do corte" na legenda e remove esses trechos. Para desativar:

```
CORTE_AUTOMATICO=0
```

Para mudar as frases de marcação:

```
MARCADOR_INICIO_CORTE=começa o corte
MARCADOR_FIM_CORTE=termina o corte
```

A comparação ignora acentos e maiúsculas, e basta a frase aparecer dentro do segmento (não precisa ser exata).

**Quer desativar a remoção de sons não-verbais (tosse, ruídos)?**
Por padrão o script remove automaticamente os segmentos que o Whisper anota como sons não-verbais (`[tosse]`, `[ruído]`, `[espirro]`, etc.). Para desativar:

```
REMOVER_SONS_NAO_VERBAIS=0
```

**Quer usar a IA da Anthropic para gerar título e descrição?**
Configure sua chave de API no `.env`:

```
ANTHROPIC_API_KEY=<sua-chave>
```

Com a chave configurada, o script vai perguntar a cada execução se você quer usá-la — exceto no modo vídeo único, onde a API é usada automaticamente. Sem a chave, o título e a descrição são gerados localmente com spaCy + NLTK.

---

## Como usar

### Modo lote — vários vídeos de uma vez

Coloque os vídeos na pasta de entrada e rode:

```bash
/home/user/projetos/macho/run.sh
```

O script vai perguntar se você quer gerar legendas e se quer usar a API da Anthropic, e depois processa todos os vídeos encontrados em `/home/user/Videos/gravado/`.

### Modo vídeo único — sem perguntas

Passe o caminho do vídeo como argumento:

```bash
python3 /home/user/projetos/macho/src/main.py /caminho/para/video.mp4
```

Nesse modo o script **não faz nenhuma pergunta**: legenda, cortes e API da Anthropic são ativados automaticamente. Ideal para rodar de forma rápida ou em scripts.

---

### Onde ficam os resultados

```
/home/user/Videos/final/
    nome-do-video/
        nome-do-video.mp4       ← vídeo com a voz alterada (e cortes aplicados)
        LEGENDAS_pt.srt         ← transcrição em português (ou outro idioma detectado)
        YOUTUBE.txt             ← título, descrição e palavras-chave para o YouTube
        report.txt              ← tabela de cortes e ocorrências das palavras monitoradas
```

Os originais são movidos para:

```
/home/user/Videos/processado/
```

---

## Tutorial passo a passo

### 1. Grave o vídeo

Durante a gravação, se quiser marcar trechos para cortar — erros, tosse, hesitações longas — é só falar as frases de marcação:

> *"início do corte"* ... *"fim do corte"*

O script detecta essas falas na transcrição e remove o trecho do vídeo automaticamente. Tosses e ruídos isolados também são removidos automaticamente pelo Whisper, sem precisar falar nada.

---

### 2. Configure o .env (uma vez só)

Abra o arquivo `.env` na raiz do projeto e ajuste o que precisar. O mínimo para usar a API da Anthropic:

```
ANTHROPIC_API_KEY=<sua-chave>
```

Para o pitch, o padrão `PITCH_FATOR=0.9800` já deixa a voz levemente mais grave. Experimente valores menores se quiser mais efeito.

---

### 3. Processe o vídeo

**Opção A — vídeo único (recomendado para uso diário):**

```bash
python3 /home/user/projetos/macho/src/main.py /home/user/Videos/gravado/aula01.mp4
```

Sem perguntas. O script aplica pitch, transcreve, corta, gera legenda, YOUTUBE.txt e report.txt.

**Opção B — lote (vários vídeos de uma vez):**

```bash
/home/user/projetos/macho/run.sh
```

O script pergunta suas preferências e processa todos os vídeos da pasta `/home/user/Videos/gravado/`.

---

### 4. Pegue os resultados

Depois de processar, tudo fica em:

```
/home/user/Videos/final/aula01/
    aula01.mp4        ← vídeo final com voz ajustada e cortes aplicados
    LEGENDAS_pt.srt   ← legenda para subir junto com o vídeo
    YOUTUBE.txt       ← copie e cole direto no YouTube
    report.txt        ← lista de cortes e palavras monitoradas (se configurado)
```

O arquivo original (`aula01.mp4`) é movido para `/home/user/Videos/processado/` — fica lá como backup.

---

### 5. Suba para o YouTube

1. Faça o upload de `aula01.mp4`
2. Cole o conteúdo de `YOUTUBE.txt` nos campos de título, descrição e tags
3. Adicione `LEGENDAS_pt.srt` como legenda na aba de acessibilidade

---

## O arquivo YOUTUBE.txt

Esse arquivo é gerado automaticamente a partir da transcrição do vídeo. Ele contém:

- **TÍTULO** — frase curta com as palavras mais relevantes do vídeo
- **DESCRIÇÃO** — resumo com as partes mais importantes, em ordem cronológica
- **PALAVRAS-CHAVE** — os termos mais frequentes para ajudar no SEO
- **PRINCIPAIS CONCEITOS** — pessoas, lugares, organizações e tópicos mencionados

Por padrão tudo é gerado localmente com spaCy + NLTK, sem depender de API externa. Se quiser título e descrição gerados por IA, configure `ANTHROPIC_API_KEY` no `.env` — o script vai perguntar a cada execução se você quer usar. Funciona em português e inglês — o idioma é detectado automaticamente pelo Whisper.

---

## O arquivo report.txt

Pode ter até duas seções, dependendo do que aconteceu no processamento.

**Cortes aplicados** — aparece quando o script removeu trechos do vídeo, com o tempo de início, fim e duração de cada corte:

```
CORTES APLICADOS

+---+---------------+---------------+---------------+
| # | INÍCIO        | FIM           | DURAÇÃO       |
+---+---------------+---------------+---------------+
| 1 | 00:01:05.320  | 00:01:48.910  | 00:00:43.590  |
+---+---------------+---------------+---------------+
```

**Palavras monitoradas** — aparece quando você configurou `PALAVRAS_FILTRO`, com o tempo exato de cada ocorrência:

```
PALAVRAS MONITORADAS

+-----------+--------------+
| PALAVRA   | TEMPO        |
+-----------+--------------+
| corta     | 00:00:42.000 |
| bosta     | 00:01:23.000 |
+-----------+--------------+
```

Se nenhuma das palavras aparecer no vídeo, a tabela informa que não houve ocorrências. Se não houver nem cortes nem palavras monitoradas, o `report.txt` não é gerado.

---

## Formatos de vídeo suportados

`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.ts`

---

## Algo deu errado?

Se um vídeo falhar no processamento ou na transcrição, o script **não move o original** — ele fica na pasta `gravado/` esperando você tentar de novo. O erro aparece no terminal ao final da execução.

Se o `YOUTUBE.txt` ou o `report.txt` não puderem ser gerados, o script exibe um aviso mas continua normalmente — o vídeo e a legenda ainda são salvos.
