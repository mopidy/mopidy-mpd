# MPD protocol versioning and executable scenarios

For the runnable 0.19 baseline and agent workflow, see
[`tests/protocol/README.md`](../tests/protocol/README.md). Later-version
directories discussed here are a design recommendation, not implemented tests.

## Recommendation

Keep a complete, independently executable **Mopidy-MPD 0.19 baseline** in
`tests/protocol/0.19/`. Add `0.20/`, `0.21/`, etc. for *changes introduced at
that MPD minor version*, rather than copying every inherited scenario into
each directory. This is an organization and test-selection convention, not a
claim that later MPD implementations cease to support older commands. For a
compatibility claim at version N, run the applicable baseline **and all deltas
through N**, and revise or explicitly supersede earlier expectations when a
later version changes them. The upstream release history shows cumulative
changes, including altered existing responses and command arguments, rather
than self-contained protocol specifications per release ([MPD NEWS, 0.19–0.24](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS)).

Prefer the path `0.19/` over `0.19-baseline/`: the first covered version is the
baseline by convention, and version-only directories make command locations
and test IDs predictable. Call it the **0.19 baseline** in the guide instead
of encoding the suite's role into its version identifier. A `0.20/` directory
would then describe only what changes relative to 0.19 (including corrections
to existing commands), not a second full copy of all 0.19 scenarios.

Label directories by **advertised protocol minor version** (`0.19`, `0.20`,
`0.21`, `0.22`, `0.23`, `0.24`). Use the earliest documented introduction of a
behavior as its home; add patch-level directories or explicit patch-version
metadata only if a patch release materially changes an assertion and the suite
actually distinguishes that patch version. For example, MPD's release notes
put `getvol` in 0.23, optional `playlistdelete` ranges in 0.23.3, and
`binarylimit` in 0.22.4. Calling both latter behaviors unconditional 0.23 and
0.22 requirements respectively would overstate support by earlier patch
releases ([NEWS](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS)).

## Evidence and version landmarks

The official protocol describes the initial `OK MPD version` greeting as the
**protocol** version, not the daemon's actual version. The `status` response's
`playlist` field is a *queue revision counter*, not this protocol version
([MPD protocol: overview](https://mpd.readthedocs.io/en/latest/protocol.html#protocol-overview),
[status](https://mpd.readthedocs.io/en/latest/protocol.html#command-status)).
This repository sets `VERSION = "0.19.0"` and uses it in its greeting
([protocol constant](../src/mopidy_mpd/protocol/__init__.py),
[session greeting](../src/mopidy_mpd/session.py)); changing test-directory names
alone cannot make the server advertise a newer protocol.

Representative changes, from the upstream release notes (not an exhaustive
command inventory):

| First release | Protocol-visible examples | Primary evidence |
| --- | --- | --- |
| 0.19 | `addtagid`, `cleartagid`, `listfiles`, mount commands and `rangeid`; grouping for `list`/`count`, `modified-since` filter, fractional `seek*` offsets. | [NEWS 0.19](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS) |
| 0.20 | `find`/`search` gain `window`; song duration gains millisecond precision; `plchanges`/`plchangesposid` gain a range; `sticker find` gains value matching; `commands` depends on playlist-directory configuration. The protocol reference marks `status`'s `duration` field as since 0.20. | [NEWS 0.20](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS); [status](https://mpd.readthedocs.io/en/latest/protocol.html#command-status) |
| 0.21 | New expression filter syntax (replacing the earlier `find TYPE VALUE` form as the documented form), sorting for `find`/`search`, one-shot `single`, `outputset`, configurable `tagtypes`; 0.21.1/0.21.2 refine filter escaping, equality, substring and regex behavior. | [NEWS 0.21–0.21.2](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS); [filters](https://mpd.readthedocs.io/en/latest/protocol.html#filters) |
| 0.22 | `readpicture`, `moveoutput`, `delpartition`, `status` partition field; `findadd`/`searchadd`/`searchaddpl` gain sort and window; 0.22.4 adds `binarylimit`, and 0.22.5 changes malformed-range error handling. | [NEWS 0.22–0.22.5](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS) |
| 0.23 | `getvol`, relative `addid` positions, position parameters for `findadd`/`searchadd`/`load`, playlist audio format; 0.23.1 adds relative `load` positions, 0.23.3 adds position/range arguments to other commands, 0.23.4/0.23.5 extend `searchaddpl`/`searchadd`. | [NEWS 0.23–0.23.5](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS); [getvol](https://mpd.readthedocs.io/en/latest/protocol.html#command-getvol) |
| 0.24 | `searchcount`, `playlistlength`, `searchplaylist`, `protocol` and sticker commands; playlist search sort/window, `save` append/replace, `added-since`, `starts_with`, one-shot `consume`, and extra sticker targets. | [NEWS 0.24](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS); [stored playlists](https://mpd.readthedocs.io/en/latest/protocol.html#stored-playlists) |

These examples show why a delta may modify an old command's argument parsing,
output or errors rather than introduce a new command. The [current official
protocol reference](https://mpd.readthedocs.io/en/latest/protocol.html) mixes
current semantics with selected “since” annotations; it is **not** a frozen
0.19 specification. Use tagged [upstream NEWS](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS)
and, where exact response details matter, corresponding tagged MPD source or
runtime evidence before writing byte-level expectations. NEWS includes
patch-release corrections; a major/minor-only chronology loses those details.

## Implications for this repository

The existing [scenario guide](../tests/protocol/README.md) explicitly describes
`0.19/<area>/<behavior>.md` as the current Mopidy-MPD behavior and says each
file is independent, while steps in a file share a connection and state. The
[runner](../tests/protocol/test_markdown.py) currently discovers **only**
`tests/protocol/0.19/**/*.md`, creates a fresh `BaseTestCase` per file and
checks that each expected line occurs in the response (extra lines are
ignored). New version directories therefore require intentional runner
discovery before their scenarios execute; inheriting them conceptually does
not make them run. Keep each delta file self-contained with its own setup and
observations; a scenario must not rely on another file running first, and
multiple steps in one file may share state. The baseline is the complete
*current documented Mopidy-MPD 0.19 behavior*, including explicit limitations,
not a guarantee of complete upstream MPD 0.19 conformance (see, for example,
[unsupported queue-priority behavior](../tests/protocol/0.19/current-playlist/queue-priority.md)).

Tests should distinguish **upstream expected behavior**, **this server's
observed behavior**, and **desired future support**. Running inherited
scenarios against a newer implementation needs explicit handling of superseded
assertions: for example, a pre-0.20 duration-format assertion may conflict
with millisecond precision in 0.20, and a pre-0.22 malformed-range assertion
may conflict with 0.22.5 error handling ([NEWS](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS)).
The present runner's subset-line matching may overlook extra version-specific
fields, so use focused checks when absence, ordering or exact wire output
matters ([runner](../tests/protocol/test_markdown.py)).

## Open questions

- Which exact upstream patch release is the intended oracle for each minor
  version? NEWS documents material patch changes (e.g. 0.22.4 and 0.23.3), so
  the minor label alone cannot always specify an exact wire contract
  ([NEWS](https://github.com/MusicPlayerDaemon/MPD/blob/v0.24/NEWS)).
- Should future suites assert upstream conformance or document incremental
  Mopidy-MPD behavior? The current [guide](../tests/protocol/README.md) and
  [fixed 0.19.0 greeting](../src/mopidy_mpd/protocol/__init__.py) establish
  only the latter at present.
