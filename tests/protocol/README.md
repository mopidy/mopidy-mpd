# MPD protocol baseline

The scenarios in `0.19/<area>/<behavior>.md` document Mopidy-MPD's current
MPD 0.19 behavior. Find a command by its protocol area, then read the prose
for limitations and the fenced steps for observable responses. Each file is
one independent scenario; steps within a file share one connection and state.

Use an `mpd` fence for commands, immediately followed by an `expected` fence
for response lines. Text outside those fences explains the behavior and is not
executed. Expected lines need only appear in the response; other lines are
ignored. `key: *` requires a non-empty value for that key. There are no other
matchers. Put dependent commands in successive steps so their effects remain
visible; a block may contain multiple commands when they belong to one step.

The tests use the existing in-process MPD session and dummy Mopidy backend.
The library can look up `dummy:/a` and `dummy:/b`, but its search index and
browse tree are empty. The pytest ID is the scenario's path; a failure shows
the step number, commands, expectations, and actual response.

Run the baseline with `pytest tests/protocol/test_markdown.py` in the project
development environment.

## Live MPD 0.19 reference

The optional reference test starts upstream MPD 0.19.21 from the pinned Nix
flake in `reference/`. It replays 31 of the 36 baseline scenarios (92 of the
99 distinct registered commands), using a fresh MPD database and playlist
directory for each scenario. The binary's release and protocol greeting are
checked separately. `connection/tagtypes.md`
and `current-playlist/add.md` also run against an in-process Mopidy-MPD session.
For the queue test, Mopidy's bundled Mopidy-File backend reads the *same tagged
files on lookup*, without an index or hard-coded metadata model. The baseline's
`dummy:/a` maps explicitly to a `file:` URI on Mopidy and `a.flac` on MPD.
The ordinary baseline still uses its fast dummy backend.

Only the MPD responses are checked in, under `reference/records/` with paths
matching their Markdown scenarios. This makes the reference evidence readable
without Nix. A normal live run checks those records against the pinned daemon;
timestamps, playlist revisions, elapsed time, and bitrate are marked as
environment-dependent. The decoder's `audio` field is omitted because it may
not be available immediately after playback starts or a skip. The records
document MPD, including differences from Mopidy-MPD. The Markdown
`expected` blocks remain the assertions about Mopidy-MPD.

Five scenarios still need reference-specific execution handling:

- `command-list/batch.md`: command lists buffer responses until the end marker.
- `connection/kill.md`: upstream `kill` can end the daemon.
- `connection/close.md`: closing the socket may have no response terminator.
- `playback/resume.md`: this pinned daemon sometimes closes the connection
  during `pause 0`; its playback path needs investigation before recording.
- `status/idle.md`: `idle` waits rather than replying immediately.

These remain executable against Mopidy-MPD in the baseline suite; their missing
MPD records are intentional and listed in `test_reference.py`.

With Nix installed, run the live test directly from the repository root:

```sh
nix run ./tests/protocol/reference
```

To refresh the checked-in records locally, set
`MPD_REFERENCE_RECORD_DIR=tests/protocol/reference/records` before `nix run`.
GitHub Actions also has a manual record-refresh mode that uploads regenerated
files for review and check-in. Ordinary CI runs the daemon live and verifies
that its normalized MPD responses still match the committed records.

The media files contain 40 and 50 seconds of silent, 44.1 kHz mono 16-bit
audio. They were encoded as FLAC 1.5.0 with `TITLE=A`/`TITLE=B`,
`ARTIST=Example`, `ALBUM=Protocol fixture`, and track numbers 1/2.

## Changing protocol behavior

For a Mopidy-MPD fix, start with the relevant Markdown scenario and its MPD
record, when available. The record observes this exact MPD build and fixture;
not proof that every MPD installation behaves that way. In particular, missing
optional plugins can make a command unavailable. Add or strengthen the
scenario's Mopidy expectation, make the smallest implementation change, and
update prose that describes the old shortcoming. Run that scenario and
`nix run ./tests/protocol/reference` before asking for review. A Mopidy-only
fix should not refresh MPD records; those change when the reference pin,
configuration, shared media, or replayed commands change. Git history retains
the earlier baseline behavior.

When targeting a later protocol version, select and pin one exact upstream
patch release. Put new commands and changed semantics in its version directory,
not a copy of the whole 0.19 baseline. Check inherited scenarios for behavior
that the later version supersedes; the current runner discovers only 0.19.
Raise the advertised version only with a separately reviewable support change,
after executable scenarios describe what Mopidy-MPD actually provides.
