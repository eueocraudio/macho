import re;
from pathlib import Path;


def _parsear_srt(caminho_srt: Path) -> list[tuple[str, str]]:
    conteudo = caminho_srt.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n");
    entradas = re.split(r"\n\s*\n", conteudo.strip());
    resultado = [];
    for entrada in entradas:
        linhas = [l.strip() for l in entrada.splitlines() if l.strip()];
        if len(linhas) < 3:
            continue;
        tempo_linha = next((l for l in linhas if "-->" in l), None);
        if not tempo_linha:
            continue;
        tempo_inicio = tempo_linha.split("-->")[0].strip().replace(",", ".");
        # linhas[0] é o número de sequência — pula por posição, não por isdigit()
        texto = " ".join(l for l in linhas[1:] if "-->" not in l);
        resultado.append((tempo_inicio, texto));
    return resultado;


def _formatar_hms(segundos: float) -> str:
    h  = int(segundos // 3600);
    m  = int((segundos % 3600) // 60);
    s  = int(segundos % 60);
    ms = int((segundos - int(segundos)) * 1000);
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}";


def _secao_cortes(cortes: list[tuple[float, float]]) -> list[str]:
    linhas = ["CORTES APLICADOS", ""];
    rows = [];
    for inicio, fim in cortes:
        duracao = fim - inicio;
        rows.append((_formatar_hms(inicio), _formatar_hms(fim), _formatar_hms(duracao)));

    col_n       = max(1, len(str(len(rows))));
    col_inicio  = max(len("INÍCIO"),   max((len(r[0]) for r in rows), default=0));
    col_fim     = max(len("FIM"),      max((len(r[1]) for r in rows), default=0));
    col_duracao = max(len("DURAÇÃO"),  max((len(r[2]) for r in rows), default=0));

    sep = (f"+-{'-'*col_n}-+-{'-'*col_inicio}-+-{'-'*col_fim}-+-{'-'*col_duracao}-+");
    cab = (f"| {'#'.ljust(col_n)} | {'INÍCIO'.ljust(col_inicio)} "
           f"| {'FIM'.ljust(col_fim)} | {'DURAÇÃO'.ljust(col_duracao)} |");
    linhas += [sep, cab, sep];
    for i, (inicio, fim, dur) in enumerate(rows, 1):
        linhas.append(
            f"| {str(i).ljust(col_n)} | {inicio.ljust(col_inicio)} "
            f"| {fim.ljust(col_fim)} | {dur.ljust(col_duracao)} |"
        );
    linhas.append(sep);
    return linhas;


def _secao_palavras(entradas: list[tuple[str, str]], palavras: list[str]) -> list[str]:
    linhas = ["PALAVRAS MONITORADAS", ""];
    padroes = [re.compile(rf"\b{re.escape(p)}\b", re.IGNORECASE) for p in palavras];
    ocorrencias: list[tuple[str, str]] = [];
    for tempo, texto in entradas:
        for padrao, palavra in zip(padroes, palavras):
            if padrao.search(texto):
                ocorrencias.append((palavra.lower(), tempo));

    col_palavra = max(len("PALAVRA"), max((len(p) for p, _ in ocorrencias), default=0));
    col_tempo   = max(len("TEMPO"),   max((len(t) for _, t in ocorrencias), default=0));

    sep = f"+-{'-'*col_palavra}-+-{'-'*col_tempo}-+";
    cab = f"| {'PALAVRA'.ljust(col_palavra)} | {'TEMPO'.ljust(col_tempo)} |";
    linhas += [sep, cab, sep];
    if ocorrencias:
        for palavra, tempo in ocorrencias:
            linhas.append(f"| {palavra.ljust(col_palavra)} | {tempo.ljust(col_tempo)} |");
    else:
        msg = "nenhuma ocorrência encontrada";
        largura = col_palavra + col_tempo + 3;
        linhas.append(f"| {msg.ljust(largura)} |");
    linhas.append(sep);
    return linhas;


def gerar_report_txt(
    caminho_srt: Path,
    dir_saida: Path,
    palavras: list[str],
    cortes: list[tuple[float, float]] | None = None,
) -> tuple[bool, str]:
    tem_cortes  = bool(cortes);
    tem_palavras = bool(palavras);
    if not tem_cortes and not tem_palavras:
        return True, "";
    try:
        secoes = [];
        if tem_cortes:
            secoes.append(_secao_cortes(cortes));
        if tem_palavras:
            entradas = _parsear_srt(caminho_srt);
            secoes.append(_secao_palavras(entradas, palavras));

        conteudo = ("\n\n\n".join("\n".join(s) for s in secoes)) + "\n";
        (dir_saida / "report.txt").write_text(conteudo, encoding="utf-8");
        return True, "";
    except Exception as e:
        return False, str(e);
