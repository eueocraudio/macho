import re;
from pathlib import Path;


def _parsear_srt(caminho_srt: Path) -> list[tuple[str, str]]:
    """Retorna lista de (tempo_inicio, texto) de cada entrada do SRT."""
    conteudo = caminho_srt.read_text(encoding="utf-8");
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
        texto = " ".join(l for l in linhas if "-->" not in l and not l.isdigit());
        resultado.append((tempo_inicio, texto));
    return resultado;


def gerar_report_txt(caminho_srt: Path, dir_saida: Path, palavras: list[str]) -> tuple[bool, str]:
    if not palavras:
        return True, "";
    try:
        entradas = _parsear_srt(caminho_srt);
        ocorrencias: list[tuple[str, str]] = [];

        for tempo, texto in entradas:
            for palavra in palavras:
                padrao = re.compile(rf"\b{re.escape(palavra)}\b", re.IGNORECASE);
                if padrao.search(texto):
                    ocorrencias.append((palavra.lower(), tempo));

        col_palavra = max(len("PALAVRA"), max((len(p) for p, _ in ocorrencias), default=0));
        col_tempo   = max(len("TEMPO"),   max((len(t) for _, t in ocorrencias), default=0));

        separador = f"+-{'-' * col_palavra}-+-{'-' * col_tempo}-+";
        cabecalho = f"| {'PALAVRA'.ljust(col_palavra)} | {'TEMPO'.ljust(col_tempo)} |";

        linhas = [separador, cabecalho, separador];
        if ocorrencias:
            for palavra, tempo in ocorrencias:
                linhas.append(f"| {palavra.ljust(col_palavra)} | {tempo.ljust(col_tempo)} |");
        else:
            msg = "nenhuma ocorrência encontrada";
            largura = col_palavra + col_tempo + 3;
            linhas.append(f"| {msg.ljust(largura)} |");
        linhas.append(separador);

        (dir_saida / "report.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8");
        return True, "";
    except Exception as e:
        return False, str(e);
