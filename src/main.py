import subprocess;
import shutil;
import sys;
import os;
import re;
import unicodedata;
from pathlib import Path;
from dotenv import load_dotenv;
from faster_whisper import WhisperModel;
from youtube import gerar_youtube_txt;
from report import gerar_report_txt;
from rich.console import Console;
from rich.panel import Panel;
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn;
from rich.prompt import Confirm;
from rich.table import Table;

load_dotenv(Path.home() / ".env");
load_dotenv(Path(__file__).parent.parent / ".env");

DIR_ENTRADA = Path(os.getenv("DIR_ENTRADA", "/home/user/Videos/gravado"));
DIR_SAIDA   = Path(os.getenv("DIR_SAIDA",   "/home/user/Videos/final"));
DIR_BACKUP  = Path(os.getenv("DIR_BACKUP",  "/home/user/Videos/processado"));

PITCH_FATOR    = float(os.getenv("PITCH_FATOR",    "0.9800"));
EQ_GRAVES_FREQ = int(os.getenv("EQ_GRAVES_FREQ",   "180"));
EQ_GRAVES_WIDTH= int(os.getenv("EQ_GRAVES_WIDTH",  "100"));
EQ_GRAVES_GAIN = int(os.getenv("EQ_GRAVES_GAIN",   "2"));
EQ_METAL_FREQ  = int(os.getenv("EQ_METAL_FREQ",    "3500"));
EQ_METAL_WIDTH = int(os.getenv("EQ_METAL_WIDTH",   "1000"));
EQ_METAL_GAIN  = int(os.getenv("EQ_METAL_GAIN",    "-3"));
WHISPER_MODEL       = os.getenv("WHISPER_MODEL", "small");
PALAVRAS_FILTRO     = [p.strip() for p in os.getenv("PALAVRAS_FILTRO",  "").split(",") if p.strip()];
PALAVRAS_EXCLUIR    = [p.strip() for p in os.getenv("PALAVRAS_EXCLUIR", "").split(",") if p.strip()];
CORTE_AUTOMATICO        = os.getenv("CORTE_AUTOMATICO",        "1") == "1";
REMOVER_SONS_NAO_VERBAIS = os.getenv("REMOVER_SONS_NAO_VERBAIS", "1") == "1";
MARCADOR_INICIO_CORTE   = os.getenv("MARCADOR_INICIO_CORTE", "início do corte");
MARCADOR_FIM_CORTE      = os.getenv("MARCADOR_FIM_CORTE",    "fim do corte");

EXTENSOES_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts"};

console = Console();


def _normalizar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto.lower().strip());
    return "".join(c for c in nfkd if not unicodedata.combining(c));


def _srt_para_segundos(timestamp: str) -> float:
    h, m, resto = timestamp.split(":");
    s, ms = resto.split(",");
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000;


def detectar_cortes(arquivo_srt: Path, marcador_inicio: str, marcador_fim: str) -> list[tuple[float, float]]:
    norm_inicio = _normalizar(marcador_inicio);
    norm_fim    = _normalizar(marcador_fim);
    texto = arquivo_srt.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n");
    blocos = re.split(r"\n\n+", texto.strip());
    cortes = [];
    inicio_pendente = None;
    for bloco in blocos:
        linhas = bloco.strip().splitlines();
        if len(linhas) < 3:
            continue;
        m = re.match(r"(\S+)\s+-->\s+(\S+)", linhas[1]);
        if not m:
            continue;
        t_inicio = _srt_para_segundos(m.group(1));
        t_fim    = _srt_para_segundos(m.group(2));
        conteudo = _normalizar(" ".join(linhas[2:]));
        if norm_inicio in conteudo:
            inicio_pendente = t_inicio;
        elif norm_fim in conteudo and inicio_pendente is not None:
            cortes.append((inicio_pendente, t_fim));
            inicio_pendente = None;
    return cortes;


def detectar_sons_nao_verbais(arquivo_srt: Path) -> list[tuple[float, float]]:
    texto = arquivo_srt.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n");
    blocos = re.split(r"\n\n+", texto.strip());
    intervalos = [];
    for bloco in blocos:
        linhas = bloco.strip().splitlines();
        if len(linhas) < 3:
            continue;
        m = re.match(r"(\S+)\s+-->\s+(\S+)", linhas[1]);
        if not m:
            continue;
        conteudo = " ".join(linhas[2:]).strip();
        if re.fullmatch(r"\[.*?\]", conteudo):
            intervalos.append((_srt_para_segundos(m.group(1)), _srt_para_segundos(m.group(2))));
    return intervalos;


def aplicar_cortes(entrada: Path, saida: Path, cortes: list[tuple[float, float]]) -> tuple[bool, str]:
    cortes_ord = sorted(cortes);
    manter = [];
    pos = 0.0;
    for inicio, fim in cortes_ord:
        if pos < inicio:
            manter.append((pos, inicio));
        pos = max(pos, fim);
    manter.append((pos, None));

    filtros = [];
    for i, (s, e) in enumerate(manter):
        if e is not None:
            filtros.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]");
            filtros.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]");
        else:
            filtros.append(f"[0:v]trim=start={s},setpts=PTS-STARTPTS[v{i}]");
            filtros.append(f"[0:a]atrim=start={s},asetpts=PTS-STARTPTS[a{i}]");

    n = len(manter);
    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(n));
    filtros.append(f"{concat_inputs}concat=n={n}:v=1:a=1[v][a]");

    tmp = saida.parent / f"_tmp_corte_{saida.stem}{saida.suffix}";
    cmd = [
        "ffmpeg", "-y",
        "-i", str(entrada),
        "-filter_complex", "; ".join(filtros),
        "-map", "[v]",
        "-map", "[a]",
        str(tmp),
    ];
    resultado = subprocess.run(cmd, capture_output=True, text=True);
    if resultado.returncode != 0:
        tmp.unlink(missing_ok=True);
        return False, resultado.stderr[-800:];
    tmp.replace(saida);
    return True, "";


def listar_videos() -> list[Path]:
    return sorted(
        v for v in DIR_ENTRADA.iterdir()
        if v.is_file() and v.suffix.lower() in EXTENSOES_VIDEO
    );


def aplicar_pitch_male(entrada: Path, saida: Path) -> tuple[bool, str]:
    saida.parent.mkdir(parents=True, exist_ok=True);
    filtro = (
        f"rubberband=pitch={PITCH_FATOR}:formant=1:pitchq=quality,"
        f"equalizer=f={EQ_GRAVES_FREQ}:t=o:w={EQ_GRAVES_WIDTH}:g={EQ_GRAVES_GAIN},"
        f"equalizer=f={EQ_METAL_FREQ}:t=o:w={EQ_METAL_WIDTH}:g={EQ_METAL_GAIN}"
    );
    cmd = [
        "ffmpeg", "-y",
        "-i", str(entrada),
        "-af", filtro,
        "-c:v", "copy",
        str(saida),
    ];
    resultado = subprocess.run(cmd, capture_output=True, text=True);
    if resultado.returncode != 0:
        return False, resultado.stderr[-800:];
    return True, "";


def formatar_tempo_srt(segundos: float) -> str:
    h  = int(segundos // 3600);
    m  = int((segundos % 3600) // 60);
    s  = int(segundos % 60);
    ms = int((segundos - int(segundos)) * 1000);
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}";


def escrever_srt(segments, lingua: str, dir_saida: Path) -> tuple[bool, str]:
    try:
        linhas = [];
        for i, seg in enumerate(segments, 1):
            inicio = formatar_tempo_srt(seg.start);
            fim    = formatar_tempo_srt(seg.end);
            linhas.append(f"{i}\n{inicio} --> {fim}\n{seg.text.strip()}\n");
        arquivo_srt = dir_saida / f"LEGENDAS_{lingua}.srt";
        arquivo_srt.write_text("\n".join(linhas), encoding="utf-8");
        return True, lingua;
    except Exception as e:
        return False, str(e);


def processar():
    for d in (DIR_ENTRADA, DIR_SAIDA, DIR_BACKUP):
        if not d.exists():
            console.print(f"[red]Diretório não encontrado:[/red] {d}");
            sys.exit(1);

    videos = listar_videos();
    if not videos:
        console.print(Panel("[yellow]Nenhum vídeo encontrado em:[/yellow]\n" + str(DIR_ENTRADA)));
        return;

    tabela = Table(title="Vídeos a processar", show_lines=True);
    tabela.add_column("#", style="dim", width=4);
    tabela.add_column("Arquivo", style="cyan");
    for i, v in enumerate(videos, 1):
        tabela.add_row(str(i), v.name);
    console.print(tabela);

    fazer_legenda = Confirm.ask("\nDeseja gerar legendas (SRT), YOUTUBE.txt e report.txt?", default=True);

    if fazer_legenda:
        usar_api_youtube = Confirm.ask("Deseja usar a API da Anthropic para gerar TÍTULO e DESCRIÇÃO?", default=False);
        console.print(f"\n[dim]Carregando modelo Whisper ({WHISPER_MODEL})...[/dim]");
        try:
            model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8");
        except Exception as e:
            console.print(f"[red]Erro ao carregar modelo Whisper '{WHISPER_MODEL}': {e}[/red]");
            sys.exit(1);
    else:
        usar_api_youtube = False;
        model = None;

    sucesso = [];
    falha   = [];

    stems_vistos: set[str] = set();
    for video in videos:
        if video.stem in stems_vistos:
            console.print(f"[yellow]aviso:[/yellow] dois vídeos com mesmo nome base '{video.stem}' — o segundo pode sobrescrever dados do primeiro");
        stems_vistos.add(video.stem);

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        for video in videos:
            dir_destino  = DIR_SAIDA / video.stem;
            arquivo_saida = dir_destino / video.name;

            task = progress.add_task(f"[cyan]{video.name}[/cyan] — aplicando pitch...", total=None);
            ok, erro = aplicar_pitch_male(video, arquivo_saida);
            if not ok:
                progress.update(task, description=f"[red]✗ pitch[/red] {video.name}");
                falha.append((video.name, erro));
                continue;

            if not fazer_legenda:
                shutil.move(str(video), DIR_BACKUP / video.name);
                progress.update(task, description=f"[green]✓[/green] {video.name} [dim](sem legenda)[/dim]");
                sucesso.append(video.name);
                continue;

            progress.update(task, description=f"[cyan]{video.name}[/cyan] — detectando língua...");
            try:
                segments, info = model.transcribe(str(arquivo_saida), beam_size=5);
                lingua = info.language;
            except Exception as e:
                progress.update(task, description=f"[red]✗ transcrição[/red] {video.name}");
                falha.append((video.name, str(e)));
                continue;

            arquivo_srt = dir_destino / f"LEGENDAS_{lingua}.srt";
            if arquivo_srt.exists():
                lingua_ou_erro = lingua;
            else:
                progress.update(task, description=f"[cyan]{video.name}[/cyan] — transcrevendo ({lingua})...");
                ok_t, lingua_ou_erro = escrever_srt(segments, lingua, dir_destino);
                if not ok_t:
                    progress.update(task, description=f"[red]✗ transcrição[/red] {video.name}");
                    falha.append((video.name, lingua_ou_erro));
                    continue;

            cortes_marcador = detectar_cortes(arquivo_srt, MARCADOR_INICIO_CORTE, MARCADOR_FIM_CORTE) if CORTE_AUTOMATICO else [];
            sons_nao_verbais = detectar_sons_nao_verbais(arquivo_srt) if REMOVER_SONS_NAO_VERBAIS else [];
            cortes = sorted(set(cortes_marcador + sons_nao_verbais));

            # report gerado com SRT original: CORTES e PALAVRAS usam a mesma timeline
            progress.update(task, description=f"[cyan]{video.name}[/cyan] — gerando report...");
            ok_rp, erro_rp = gerar_report_txt(arquivo_srt, dir_destino, PALAVRAS_FILTRO, cortes_marcador if cortes_marcador else None);
            if not ok_rp:
                console.print(f"[yellow]aviso:[/yellow] não foi possível gerar report.txt: {erro_rp}");

            srt_confiavel = True;
            if cortes:
                desc_cortes = [];
                if cortes_marcador:
                    desc_cortes.append(f"{len(cortes_marcador)} marcador(es)");
                if sons_nao_verbais:
                    desc_cortes.append(f"{len(sons_nao_verbais)} som(ns) não-verbal(is)");
                progress.update(task, description=f"[cyan]{video.name}[/cyan] — aplicando cortes ({', '.join(desc_cortes)})...");
                ok_c, erro_c = aplicar_cortes(arquivo_saida, arquivo_saida, cortes);
                if not ok_c:
                    console.print(f"[yellow]aviso:[/yellow] não foi possível aplicar cortes: {erro_c}");
                else:
                    progress.update(task, description=f"[cyan]{video.name}[/cyan] — retranscrevendo após cortes ({lingua_ou_erro})...");
                    try:
                        segments2, _ = model.transcribe(str(arquivo_saida), beam_size=5);
                        ok_t2, _ = escrever_srt(segments2, lingua_ou_erro, dir_destino);
                        if not ok_t2:
                            console.print(f"[yellow]aviso:[/yellow] não foi possível regerar legenda após cortes");
                            srt_confiavel = False;
                    except Exception as e2:
                        console.print(f"[yellow]aviso:[/yellow] erro na retranscrição após cortes: {e2}");
                        srt_confiavel = False;

            progress.update(task, description=f"[cyan]{video.name}[/cyan] — gerando metadados YouTube...");
            if srt_confiavel:
                ok_yt, erro_yt = gerar_youtube_txt(arquivo_srt, dir_destino, lingua_ou_erro, PALAVRAS_EXCLUIR, usar_api_youtube);
                if not ok_yt:
                    console.print(f"[yellow]aviso:[/yellow] não foi possível gerar YOUTUBE.txt: {erro_yt}");
            else:
                console.print(f"[yellow]aviso:[/yellow] YOUTUBE.txt não gerado — SRT contém marcadores de corte (retranscrição falhou)");

            shutil.move(str(video), DIR_BACKUP / video.name);
            progress.update(task, description=f"[green]✓[/green] {video.name} [dim](LEGENDAS_{lingua_ou_erro}.srt)[/dim]");
            sucesso.append(video.name);

    console.print();
    console.print(Panel(
        f"[green]Processados com sucesso:[/green] {len(sucesso)}\n"
        f"[red]Com falha:[/red]              {len(falha)}",
        title="Resumo",
    ));

    if falha:
        console.print("\n[red]Erros:[/red]");
        for nome, err in falha:
            console.print(f"  [bold]{nome}[/bold]\n  {err}\n");


if __name__ == "__main__":
    processar();
