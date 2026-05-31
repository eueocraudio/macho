import subprocess;
import shutil;
import sys;
import os;
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
WHISPER_MODEL    = os.getenv("WHISPER_MODEL", "small");
PALAVRAS_FILTRO  = [p.strip() for p in os.getenv("PALAVRAS_FILTRO",  "").split(",") if p.strip()];
PALAVRAS_EXCLUIR = [p.strip() for p in os.getenv("PALAVRAS_EXCLUIR", "").split(",") if p.strip()];

EXTENSOES_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts"};

console = Console();


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
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8");
    else:
        usar_api_youtube = False;
        model = None;

    sucesso = [];
    falha   = [];

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
                shutil.move(str(video), DIR_BACKUP / video.name);
                progress.update(task, description=f"[green]✓[/green] {video.name} [dim](legenda {lingua} já existe)[/dim]");
                sucesso.append(video.name);
                continue;

            progress.update(task, description=f"[cyan]{video.name}[/cyan] — transcrevendo ({lingua})...");
            ok_t, lingua_ou_erro = escrever_srt(segments, lingua, dir_destino);
            if not ok_t:
                progress.update(task, description=f"[red]✗ transcrição[/red] {video.name}");
                falha.append((video.name, lingua_ou_erro));
                continue;

            progress.update(task, description=f"[cyan]{video.name}[/cyan] — gerando metadados YouTube...");
            ok_yt, erro_yt = gerar_youtube_txt(arquivo_srt, dir_destino, lingua_ou_erro, PALAVRAS_EXCLUIR, usar_api_youtube);
            if not ok_yt:
                console.print(f"[yellow]aviso:[/yellow] não foi possível gerar YOUTUBE.txt: {erro_yt}");

            progress.update(task, description=f"[cyan]{video.name}[/cyan] — gerando report...");
            ok_rp, erro_rp = gerar_report_txt(arquivo_srt, dir_destino, PALAVRAS_FILTRO);
            if not ok_rp:
                console.print(f"[yellow]aviso:[/yellow] não foi possível gerar report.txt: {erro_rp}");

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
