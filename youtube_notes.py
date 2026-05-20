#!/usr/bin/env python3
"""YouTube video transcript to detailed notes converter."""

import re
import sys
import tempfile
from pathlib import Path

import click
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def fetch_video_title(video_id: str) -> str:
    import subprocess
    try:
        result = subprocess.run(
            ['yt-dlp', '--print', 'title', '--no-playlist',
             f'https://youtube.com/watch?v={video_id}'],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def fetch_youtube_transcript(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # Prefer manual English captions, then auto-generated, then anything
    try:
        transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
    except Exception:
        try:
            transcript = transcript_list.find_generated_transcript(['en', 'en-US'])
        except Exception:
            # Take whatever is available
            all_transcripts = (
                list(transcript_list._manually_created_transcripts.values()) +
                list(transcript_list._generated_transcripts.values())
            )
            if not all_transcripts:
                raise NoTranscriptFound(video_id, [], {})
            transcript = all_transcripts[0]

    data = transcript.fetch()
    return ' '.join(item.text for item in data)


def transcribe_audio(video_id: str, model_size: str = "base") -> str:
    import subprocess
    import whisper

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_template = Path(tmpdir) / "audio.%(ext)s"
        result = subprocess.run(
            [
                'yt-dlp', '-x', '--audio-format', 'mp3',
                '--no-playlist',
                '-o', str(audio_template),
                f'https://youtube.com/watch?v={video_id}',
            ],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {result.stderr[-500:]}")

        audio_files = list(Path(tmpdir).glob("*.mp3"))
        if not audio_files:
            raise RuntimeError("No audio file produced by yt-dlp")

        model = whisper.load_model(model_size)
        output = model.transcribe(str(audio_files[0]))
        return output['text']


def generate_notes(transcript: str, title: str, api_key: str | None = None) -> str:
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    title_line = f'Video title: "{title}"\n\n' if title else ""

    prompt = f"""{title_line}You are an expert note-taker. Convert the YouTube video transcript below into \
comprehensive, well-structured notes in Markdown.

Include:
1. **Summary** – 2-3 sentence overview
2. **Key Topics** – each as an `##` heading with detailed bullet points underneath
3. **Notable Quotes or Insights** – direct quotes worth remembering (skip if none)
4. **Key Takeaways** – 3-7 concise action points or conclusions

Be thorough but concise. Use plain language.

Transcript:
{transcript}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


@click.command()
@click.argument('url')
@click.option('--output', '-o', type=click.Path(), help='Save notes to a Markdown file')
@click.option(
    '--whisper-model', default='base',
    type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
    show_default=True,
    help='Whisper model for audio fallback transcription',
)
@click.option('--force-audio', is_flag=True, help='Skip YouTube captions; transcribe audio via Whisper')
@click.option('--api-key', envvar='ANTHROPIC_API_KEY', help='Anthropic API key (or set ANTHROPIC_API_KEY)')
def main(url: str, output: str | None, whisper_model: str, force_audio: bool, api_key: str | None):
    """Convert a YouTube video into detailed notes using Claude AI.

    \b
    Accepted URL formats:
      https://www.youtube.com/watch?v=VIDEO_ID
      https://youtu.be/VIDEO_ID
      https://youtube.com/shorts/VIDEO_ID

    \b
    The tool first tries YouTube's built-in captions. If none are available
    (or --force-audio is set) it downloads the audio and transcribes it
    locally with OpenAI Whisper before sending the text to Claude.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:

        try:
            video_id = extract_video_id(url)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            sys.exit(1)

        task = progress.add_task("Fetching video title…", total=None)
        title = fetch_video_title(video_id)
        progress.remove_task(task)

        if title:
            console.print(f"[bold cyan]Video:[/bold cyan] {title}")

        transcript: str | None = None

        if not force_audio:
            task = progress.add_task("Fetching YouTube transcript…", total=None)
            try:
                transcript = fetch_youtube_transcript(video_id)
                progress.remove_task(task)
                console.print("[green]✓[/green] YouTube transcript fetched")
            except Exception as exc:
                progress.remove_task(task)
                console.print(f"[yellow]⚠[/yellow]  No captions found ({exc}); falling back to audio transcription")

        if transcript is None:
            task = progress.add_task(
                f"Downloading audio & transcribing with Whisper [{whisper_model}]…", total=None
            )
            try:
                transcript = transcribe_audio(video_id, whisper_model)
                progress.remove_task(task)
                console.print("[green]✓[/green] Audio transcribed with Whisper")
            except RuntimeError as exc:
                progress.remove_task(task)
                console.print(f"[red]Error:[/red] {exc}")
                sys.exit(1)

        task = progress.add_task("Generating notes with Claude…", total=None)
        try:
            notes = generate_notes(transcript, title, api_key)
            progress.remove_task(task)
            console.print("[green]✓[/green] Notes generated\n")
        except anthropic.AuthenticationError:
            progress.remove_task(task)
            console.print(
                "[red]Error:[/red] Invalid or missing Anthropic API key.\n"
                "Set ANTHROPIC_API_KEY or pass --api-key."
            )
            sys.exit(1)
        except Exception as exc:
            progress.remove_task(task)
            console.print(f"[red]Error:[/red] Claude API call failed: {exc}")
            sys.exit(1)

    console.print(Markdown(notes))

    if output:
        out = Path(output)
        header = f"# Notes: {title}\n\n" if title else ""
        out.write_text(header + notes, encoding="utf-8")
        console.print(f"\n[green]Saved:[/green] {out.resolve()}")


if __name__ == '__main__':
    main()
