# Cráudio Macho 🎙️

> Criado por [Cráudio](https://www.youtube.com/@eueocraudio)

Você gravou um vídeo, mas sua voz ficou fininha demais? Esse script resolve isso.

Ele pega todos os vídeos de uma pasta, aplica um efeito de voz masculina (mais grave, mais encorpada), gera a transcrição automática em SRT, prepara um arquivo de texto com título, descrição e palavras-chave prontos para colar no YouTube, e ainda gera um relatório de palavras que você queira monitorar.

---

## O que ele faz, exatamente?

Para cada vídeo encontrado na pasta de entrada:

1. Aplica o efeito de **Pitch Male** na voz (usando ffmpeg com rubberband)
2. Salva o vídeo novo em uma pasta separada
3. Pergunta se você quer gerar legendas, YOUTUBE.txt e report.txt — se não, pula direto para o passo 7
4. Detecta automaticamente o idioma do vídeo
5. Gera um arquivo de **legendas `.srt`** (usando Whisper) — se já existir para esse idioma, pula
6. Pergunta se você quer usar a **API da Anthropic** para gerar o título e a descrição — se não, usa análise de texto local (spaCy + NLTK)
7. Gera um arquivo **`YOUTUBE.txt`** com título, descrição, palavras-chave e principais conceitos
8. Gera um arquivo **`report.txt`** com a tabela de ocorrências das palavras que você quer monitorar
9. Move o vídeo original para uma pasta de "já processados"

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
PITCH_FATOR=0.9439   # leve (-1 semitom)
PITCH_FATOR=0.8909   # padrão (-2 semitons)
PITCH_FATOR=0.8409   # grave (-3 semitons)
PITCH_FATOR=0.7937   # muito grave (-4 semitons)
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

**Quer usar a IA da Anthropic para gerar título e descrição?**
Configure sua chave de API no `.env`:

```
ANTHROPIC_API_KEY=<sua-chave>
```

Com a chave configurada, o script vai perguntar a cada execução se você quer usá-la. Sem a chave, o título e a descrição são gerados localmente.

---

## Como usar

Coloque seus vídeos na pasta:

```
/home/user/Videos/gravado/
```

Depois é só rodar:

```bash
/home/user/projetos/macho/run.sh
```

O terminal vai mostrar o progresso de cada vídeo. Quando terminar, você encontra os resultados em:

```
/home/user/Videos/final/
    nome-do-video/
        nome-do-video.mp4       ← vídeo com a voz alterada
        LEGENDAS_pt.srt         ← transcrição em português (ou outro idioma detectado)
        YOUTUBE.txt             ← título, descrição e palavras-chave para o YouTube
        report.txt              ← tabela com ocorrências das palavras monitoradas
```

E os originais ficam guardados em:

```
/home/user/Videos/processado/
```

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

Mostra em forma de tabela cada vez que uma palavra monitorada apareceu na transcrição, com o tempo exato:

```
+-----------+--------------+
| PALAVRA   | TEMPO        |
+-----------+--------------+
| corta     | 00:00:42.000 |
| bosta     | 00:01:23.000 |
+-----------+--------------+
```

Se nenhuma das palavras aparecer no vídeo, a tabela informa que não houve ocorrências.

---

## Formatos de vídeo suportados

`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.flv`, `.ts`

---

## Algo deu errado?

Se um vídeo falhar no processamento ou na transcrição, o script **não move o original** — ele fica na pasta `gravado/` esperando você tentar de novo. O erro aparece no terminal ao final da execução.

Se o `YOUTUBE.txt` ou o `report.txt` não puderem ser gerados, o script exibe um aviso mas continua normalmente — o vídeo e a legenda ainda são salvos.
