from pathlib import Path;
from collections import Counter;
import re;
import nltk;
import spacy;
try:
    import anthropic as _anthropic;
except ImportError:
    _anthropic = None;

# Mapa língua Whisper → modelo spaCy
_MODELOS_SPACY: dict[str, str] = {
    "pt": "pt_core_news_sm",
    "en": "en_core_web_sm",
};
_MODELO_FALLBACK = "en_core_web_sm";

_cache_modelos: dict[str, spacy.language.Language] = {};


def _carregar_modelo(lingua: str) -> spacy.language.Language:
    nome = _MODELOS_SPACY.get(lingua, _MODELO_FALLBACK);
    if nome not in _cache_modelos:
        _cache_modelos[nome] = spacy.load(nome);
    return _cache_modelos[nome];


def _texto_do_srt(caminho_srt: Path) -> str:
    conteudo = caminho_srt.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n");
    texto = [];
    for bloco in re.split(r"\n\n+", conteudo.strip()):
        linhas = [l.strip() for l in bloco.strip().splitlines() if l.strip()];
        # linhas[0] é número de sequência — pula por posição, não por isdigit()
        texto += [l for l in linhas[1:] if "-->" not in l];
    return " ".join(texto);


def _set_excluir(palavras_excluir: list[str]) -> set[str]:
    return {p.lower() for p in palavras_excluir};


def _sentenca_contem_excluida(texto: str, excluir_set: set[str]) -> bool:
    for palavra in excluir_set:
        if re.search(rf"\b{re.escape(palavra)}\b", texto, re.IGNORECASE):
            return True;
    return False;


def _palavras_chave(doc, lingua: str, excluir_set: set[str], n: int = 15) -> list[str]:
    try:
        stops = set(nltk.corpus.stopwords.words(
            "portuguese" if lingua == "pt" else "english"
        ));
    except Exception:
        stops = set();

    tokens = [
        t.lemma_.lower() for t in doc
        if not t.is_stop
        and not t.is_punct
        and not t.is_space
        and t.pos_ in ("NOUN", "PROPN", "ADJ")
        and len(t.text) > 2
        and t.lemma_.lower() not in stops
        and t.lemma_.lower() not in excluir_set
        and t.text.lower() not in excluir_set
    ];
    freq = Counter(tokens);
    return [p for p, _ in freq.most_common(n)];


def _conceitos(doc, excluir_set: set[str]) -> list[str]:
    vistos: set[str] = set();
    resultado = [];
    for ent in doc.ents:
        texto = ent.text.strip();
        if texto.lower() not in vistos and not _sentenca_contem_excluida(texto, excluir_set):
            vistos.add(texto.lower());
            resultado.append(texto);
    for chunk in doc.noun_chunks:
        texto = chunk.text.strip();
        if (len(texto.split()) >= 2
                and texto.lower() not in vistos
                and not _sentenca_contem_excluida(texto, excluir_set)):
            vistos.add(texto.lower());
            resultado.append(texto);
    # preserva a ordem de relevância (entidades antes de noun chunks); só limita a 15
    return resultado[:15];


def _pontuar_sentencas(doc, chave_set: set[str], excluir_set: set[str]) -> list[tuple[int, int, str]]:
    resultado = [];
    for i, sent in enumerate(doc.sents):
        if _sentenca_contem_excluida(sent.text, excluir_set):
            continue;
        tokens = [t.lemma_.lower() for t in sent if not t.is_stop and not t.is_punct];
        score = sum(1 for t in tokens if t in chave_set);
        resultado.append((score, i, sent.text.strip()));
    return resultado;


def _descricao(doc, palavras_chave: list[str], excluir_set: set[str], n: int = 4) -> str:
    chave_set = set(palavras_chave);
    pontuadas = _pontuar_sentencas(doc, chave_set, excluir_set);
    top_idx = sorted(
        range(len(pontuadas)),
        key=lambda i: pontuadas[i][0],
        reverse=True,
    )[:n];
    top_idx_ordenados = sorted(top_idx);
    return " ".join(pontuadas[i][2] for i in top_idx_ordenados);


def _titulo(doc, palavras_chave: list[str], excluir_set: set[str]) -> str:
    chave_set = set(palavras_chave);
    pontuadas = _pontuar_sentencas(doc, chave_set, excluir_set);
    # prefere sentenças curtas que contenham ao menos uma palavra-chave
    candidatas = [(s, i, t) for s, i, t in pontuadas if len(t.split()) <= 15 and s > 0];
    if candidatas:
        return max(candidatas, key=lambda x: x[0])[2];
    # fallback: qualquer sentença curta sem palavras excluídas
    candidatas_curtas = [(s, i, t) for s, i, t in pontuadas if len(t.split()) <= 15];
    if candidatas_curtas:
        return max(candidatas_curtas, key=lambda x: x[0])[2];
    if not pontuadas:
        return "";
    titulo = pontuadas[0][2];
    palavras_titulo = titulo.split();
    return " ".join(palavras_titulo[:15]) if len(palavras_titulo) > 15 else titulo;


def _titulo_descricao_via_api(
    texto: str,
    lingua: str,
    palavras_excluir: list[str],
) -> tuple[str, str]:
    if _anthropic is None:
        raise RuntimeError("Pacote 'anthropic' não instalado. Execute: pip3 install anthropic --break-system-packages");
    client = _anthropic.Anthropic();
    user_content = f"Transcrição (idioma: {lingua}):\n{texto}";
    if palavras_excluir:
        user_content = f"Palavras proibidas (não use): {', '.join(palavras_excluir)}\n\n" + user_content;
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": (
                "Você recebe a transcrição de um vídeo e deve gerar metadados para o YouTube.\n\n"
                "Regras:\n"
                "- TÍTULO: máximo 15 palavras, direto, sem clickbait, com ao menos uma palavra-chave do vídeo\n"
                "- DESCRIÇÃO: 3-4 frases resumindo o conteúdo principal, em ordem natural\n"
                "- Nunca use palavras listadas como proibidas\n\n"
                "Responda EXATAMENTE neste formato (sem mais nada):\n"
                "TÍTULO: <título aqui>\n"
                "DESCRIÇÃO: <descrição aqui>"
            ),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_content}],
    );
    resposta = next((b.text for b in response.content if b.type == "text"), "");
    titulo = "";
    descricao_linhas: list[str] = [];
    modo = None;
    for linha in resposta.splitlines():
        if linha.startswith("TÍTULO:"):
            titulo = linha[len("TÍTULO:"):].strip();
            modo = "titulo";
        elif linha.startswith("DESCRIÇÃO:"):
            primeira = linha[len("DESCRIÇÃO:"):].strip();
            if primeira:
                descricao_linhas.append(primeira);
            modo = "descricao";
        elif modo == "descricao" and linha.strip():
            descricao_linhas.append(linha.strip());
    descricao = " ".join(descricao_linhas);
    return titulo, descricao;


def gerar_youtube_txt(
    caminho_srt: Path,
    dir_saida: Path,
    lingua: str,
    palavras_excluir: list[str] | None = None,
    usar_api: bool = False,
) -> tuple[bool, str]:
    try:
        texto = _texto_do_srt(caminho_srt);
        if not texto.strip():
            return False, "transcrição vazia";

        excluir_set = _set_excluir(palavras_excluir or []);

        nlp = _carregar_modelo(lingua);
        doc = nlp(texto);

        palavras  = _palavras_chave(doc, lingua, excluir_set);
        conceitos = _conceitos(doc, excluir_set);

        if usar_api:
            titulo, descricao = _titulo_descricao_via_api(texto, lingua, palavras_excluir or []);
        else:
            descricao = _descricao(doc, palavras, excluir_set);
            titulo    = _titulo(doc, palavras, excluir_set);

        linhas_conceitos = "\n".join(f"- {c}" for c in conceitos);
        conteudo = (
            f"TÍTULO\n{titulo}\n\n"
            f"DESCRIÇÃO\n{descricao}\n\n"
            f"PALAVRAS-CHAVE\n{', '.join(palavras)}\n\n"
            f"PRINCIPAIS CONCEITOS\n{linhas_conceitos}\n"
        );

        (dir_saida / "YOUTUBE.txt").write_text(conteudo, encoding="utf-8");
        return True, "";
    except Exception as e:
        return False, str(e);
