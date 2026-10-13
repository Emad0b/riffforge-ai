import subprocess
import wave
from pathlib import Path
import imageio_ffmpeg

MAX_BYTES = 20 * 1024 * 1024


def decode(source: Path, target: Path):
    signature = source.read_bytes()[:16]
    if not (
        signature.startswith((b"RIFF", b"fLaC", b"OggS", b"ID3"))
        or signature[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")
        or signature[4:8] == b"ftyp"
    ):
        raise ValueError("Unsupported audio signature. Use WAV, MP3, FLAC, OGG or M4A.")
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-nostdin",
        "-v",
        "error",
        "-y",
        "-protocol_whitelist",
        "file,pipe",
        "-i",
        str(source),
        "-t",
        "31",
        "-vn",
        "-ac",
        "1",
        "-ar",
        "22050",
        "-c:a",
        "pcm_s16le",
        str(target),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=25)
        with wave.open(str(target)) as audio:
            duration = audio.getnframes() / audio.getframerate()
        if not 1 <= duration <= 30:
            raise ValueError("Audio must be between 1 and 30 seconds.")
        return duration
    except (subprocess.SubprocessError, wave.Error) as error:
        target.unlink(missing_ok=True)
        raise ValueError("Audio could not be decoded safely.") from error
