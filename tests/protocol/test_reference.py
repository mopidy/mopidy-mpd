"""Replay the 0.19 scenarios with stable framing against pinned upstream MPD."""

import difflib
import hashlib
import json
import os
import socket
import subprocess
import time
from contextlib import closing
from pathlib import Path

import pytest
from mopidy._exts.file.backend import FileBackend

from tests.protocol import BaseTestCase
from tests.protocol.test_markdown import ROOT, matches, steps

MOPIDY_FILE_CASES = {
    "connection/tagtypes.md",
    "current-playlist/add.md",
}
OUTSTANDING = {
    "command-list/batch.md": "commands are buffered until command_list_end",
    "connection/kill.md": "upstream kill may stop the reference daemon",
    "connection/close.md": "close may end the socket without a response",
    "playback/resume.md": "upstream closes the socket intermittently after resume",
    "status/idle.md": "idle does not produce an immediate response",
}
SCENARIO_ROOT = ROOT / "tests/protocol/0.19"
SCENARIOS = tuple(
    path.relative_to(SCENARIO_ROOT).as_posix()
    for path in sorted(SCENARIO_ROOT.rglob("*.md"))
    if path.relative_to(SCENARIO_ROOT).as_posix() not in OUTSTANDING
)
assert OUTSTANDING.keys() <= {
    path.relative_to(SCENARIO_ROOT).as_posix() for path in SCENARIO_ROOT.rglob("*.md")
}
MEDIA = ROOT / "tests/protocol/media"
TRACKS = {f"dummy:/{name}": MEDIA / f"{name}.flac" for name in "ab"}
RECORDS = ROOT / "tests/protocol/reference/records"


class FileTestCase(BaseTestCase):
    def get_config(self):
        config = super().get_config()
        config["file"] = {
            "media_dirs": [f"{MEDIA}|Fixtures"],
            "show_dotfiles": False,
            "excluded_file_extensions": [],
            "follow_symlinks": False,
            "metadata_timeout": 5000,
        }
        return config

    def create_backend(self):
        return FileBackend.start(config=self.get_config(), audio=self.audio).proxy()


def mapped_command(command, *, mopidy):
    for uri, path in TRACKS.items():
        command = command.replace(uri, path.as_uri() if mopidy else path.name)
    return command


def comparable_response(response):
    aliases = {
        f"file: {value}": f"file: {uri}"
        for uri, path in TRACKS.items()
        for value in (path.as_uri(), path.name)
    }
    return [aliases.get(line, line) for line in response]


def recorded_response(response):
    """Replace environment-specific values; leave behavior differences visible."""
    result = []
    for line in response:
        if line.startswith("audio: "):
            # The decoder's format may not be known immediately after a skip.
            continue
        if line.startswith("Last-Modified: "):
            result.append("Last-Modified: <fixture mtime>")
        elif line.startswith("playlist: "):
            result.append("playlist: <revision>")
        elif line.startswith("uptime: "):
            result.append("uptime: <seconds>")
        elif line.startswith("db_update: "):
            result.append("db_update: <timestamp>")
        elif line.startswith("elapsed: "):
            result.append("elapsed: <seconds>")
        elif line.startswith("bitrate: "):
            result.append("bitrate: <kbps>")
        elif line.startswith("time: "):
            result.append("time: <elapsed>:" + line.rsplit(":", 1)[-1])
        else:
            result.append(line)
    return result


def exchange(stream, command):
    stream.write(f"{command}\n".encode())
    stream.flush()
    response = []
    while True:
        line = stream.readline()
        if not line:
            raise AssertionError(f"MPD closed connection during {command!r}")
        text = line.decode().rstrip("\n")
        response.append(text)
        if text == "OK" or text.startswith("ACK "):
            return response


def start_reference(tmp_path, mpd_binary):
    with closing(socket.socket()) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    playlists = tmp_path / "playlists"
    playlists.mkdir()
    config = tmp_path / "mpd.conf"
    config.write_text(
        f'music_directory "{MEDIA}"\n'
        f'playlist_directory "{playlists}"\n'
        f'db_file "{tmp_path / "db"}"\n'
        f'log_file "{tmp_path / "mpd.log"}"\n'
        'bind_to_address "127.0.0.1"\n'
        f'port "{port}"\n'
        'audio_output {\n  type "null"\n  name "Reference null"\n}\n',
        encoding="utf-8",
    )
    process = subprocess.Popen(  # noqa: S603
        [mpd_binary, "--no-daemon", str(config)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        connection, stream = connect_reference(process, port)
    except BaseException:
        process.terminate()
        process.wait(timeout=5)
        raise
    else:
        return process, connection, stream


def connect_reference(process, port):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError(f"MPD exited: {process.stderr.read().decode()}")
        try:
            connection = socket.create_connection(("127.0.0.1", port), timeout=1)
        except OSError:
            time.sleep(0.05)
            continue
        connection.settimeout(10)
        stream = connection.makefile("rwb")
        greeting = stream.readline().decode().strip()
        if not greeting:
            stream.close()
            connection.close()
            time.sleep(0.05)
            continue
        assert greeting == "OK MPD 0.19.0", greeting
        return connection, stream
    raise AssertionError("MPD did not start within 10 seconds")


def ready_library(stream):
    exchange(stream, "update")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = exchange(stream, "status")
        if not any(line.startswith("updating_db:") for line in status):
            files = exchange(stream, "listall")
            if "file: a.flac" in files and "file: b.flac" in files:
                return
        time.sleep(0.05)
    raise AssertionError("MPD did not index both reference tracks")


def replay_step(stream, client, name, number, *, commands, expected):
    actual_mopidy = []
    actual_mpd = []
    reference_commands = []
    for command in commands:
        if client:
            actual_mopidy.extend(
                client.send_request(mapped_command(command, mopidy=True))
            )
        reference_command = mapped_command(command, mopidy=False)
        reference_commands.append(reference_command)
        actual_mpd.extend(exchange(stream, reference_command))

    if client:
        assertions = expected
        if name == "current-playlist/add.md" and number == 2:
            # Both scanners must read these tags from the same FLAC file.
            assertions = [
                *expected,
                "Artist: Example",
                "Album: Protocol fixture",
                "Track: 1",
                "Time: 40",
            ]
        actual = comparable_response(actual_mopidy)
        assert all(matches(line, actual) for line in assertions), (
            f"{name} step {number} on Mopidy: {commands!r}\n"
            f"expected: {assertions!r}\nactual: {actual!r}\n"
            f"raw MPD: {actual_mpd!r}"
        )

    return {
        "step": number,
        "commands": reference_commands,
        "mpd": recorded_response(actual_mpd),
    }


def save_or_check_record(name, record):
    record_dir = os.environ.get("MPD_REFERENCE_RECORD_DIR")
    path = (Path(record_dir) if record_dir else RECORDS) / name.replace(".md", ".json")
    if record_dir:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return

    saved = path.read_text(encoding="utf-8")
    observed = json.dumps(record, indent=2) + "\n"
    assert record == json.loads(saved), (
        f"MPD reference changed for {name}; run the manual record workflow "
        "to review an updated record\n"
        + "".join(
            difflib.unified_diff(
                saved.splitlines(keepends=True),
                observed.splitlines(keepends=True),
                fromfile=str(path),
                tofile="live MPD",
            )
        )
    )


@pytest.mark.parametrize(
    "name", SCENARIOS, ids=lambda name: f"tests/protocol/0.19/{name}"
)
def test_live_reference(name, tmp_path):
    binary = os.environ.get("MPD_REFERENCE_BIN")
    if not binary:
        pytest.skip("MPD_REFERENCE_BIN not set")
    version = subprocess.check_output([binary, "--version"], text=True)  # noqa: S603
    assert "Music Player Daemon 0.19.21" in version

    client = FileTestCase() if name in MOPIDY_FILE_CASES else None
    if client:
        client.setUp()
    process = connection = stream = None
    try:
        process, connection, stream = start_reference(tmp_path, binary)
        ready_library(stream)
        transcript = [
            replay_step(
                stream, client, name, number, commands=commands, expected=expected
            )
            for number, (commands, expected) in enumerate(
                steps(SCENARIO_ROOT / name), start=1
            )
        ]
    finally:
        if stream:
            stream.close()
        if connection:
            connection.close()
        if process:
            process.terminate()
            process.wait(timeout=5)
        if client:
            client.tearDown()

    record = {
        "scenario": f"tests/protocol/0.19/{name}",
        "daemon": version.splitlines()[0],
        "greeting": "OK MPD 0.19.0",
        "media_sha256": {
            file.name: hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(MEDIA.glob("*.flac"))
        },
        "steps": transcript,
    }
    save_or_check_record(name, record)
