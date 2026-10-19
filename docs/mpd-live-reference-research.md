# A live MPD 0.19 reference daemon

This note records the research and initial design choices. For the current
runner, coverage, outstanding cases, and refresh workflow, use
[`tests/protocol/README.md`](../tests/protocol/README.md). The early WAV and
test-backend proposals below were superseded by tagged FLAC and Mopidy-File.

## Recommendation and scope

Use upstream **MPD v0.19.21** as a separately built, headless, local TCP oracle for a small, explicitly selected set of protocol observations. It is the last 0.19 patch release in the upstream [v0.19.21 `NEWS`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/NEWS) (dated 2016-12-13); upstream's [annotated tag](https://github.com/MusicPlayerDaemon/MPD/releases/tag/v0.19.21) resolves to commit `3bbcda917ce7cb2fa6dcc90d6c38333ca855c941` (tag object `f7a5fe432ac967eb6afd0ee47e3621f09dbc1999`). Pin the **commit and source content hash**, plus the Nixpkgs revision, toolchain/dependency set, configuration and media fixture. Do not equate a `0.19.0` greeting with the daemon's patch release: [`configure.ac` at v0.19.21](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/configure.ac) sets package version `0.19.21` but `PROTOCOL_VERSION` to `0.19.0`; [`ClientNew.cxx`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/client/ClientNew.cxx) constructs `OK MPD 0.19.0\n`. The [protocol overview](https://mpd.readthedocs.io/en/latest/protocol.html#protocol-overview) explicitly says the greeting identifies the protocol, not the executable version. Record `mpd --version` **and** the socket greeting at runtime; assert both independently. This matches this repository's [fixed `VERSION = "0.19.0"`](../src/mopidy_mpd/protocol/__init__.py) without proving identical implementation.

Pinning makes the chosen upstream source and build inputs reproducible; it does **not** guarantee all 0.19 patch releases behaved alike, a complete normative 0.19 specification, equivalent enabled plugins, identical runtime state, or byte-for-byte stability of timestamps and playback progress. `NEWS` even records protocol changes in patch releases (0.19.20 changes `setprio` scheduling; 0.19.4 and 0.19.3 include protocol fixes). Consult [tagged `NEWS`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/NEWS) and [tagged source](https://github.com/MusicPlayerDaemon/MPD/tree/v0.19.21/src) for exact 0.19 behavior rather than interpreting the [current rolling protocol manual](https://mpd.readthedocs.io/en/latest/protocol.html) as a frozen snapshot.

## Build and fixture feasibility

- This is **Autotools/C++11**, not today's Meson MPD: [`INSTALL`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/INSTALL), [`autogen.sh`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/autogen.sh), and [`configure.ac`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/configure.ac) identify GCC >= 4.7, Boost >= 1.46, GLib >= 2.28, pkg-config, and optional codec/output libraries. Source git checkout needs `./autogen.sh` (Autoconf/Automake/libtool and the bundled `m4` macros); a tagged release tarball may already have generated configure files. Nix can package a pinned checkout, but a modern `pkgs.mpd` is not evidence that 2016 source builds on the 2026 toolchain. Disable incidental auto-detected plugins, inotify (`--disable-inotify`) and Zeroconf (`--with-zeroconf=no`) where appropriate; explicitly enable a WAV decoder (`--enable-sndfile` or `--enable-audiofile`) and confirm `mpd --version` lists it. [`SndfileDecoderPlugin.cxx`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/decoder/plugins/SndfileDecoderPlugin.cxx) and [`AudiofileDecoderPlugin.cxx`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/decoder/plugins/AudiofileDecoderPlugin.cxx) register `wav`. If current Boost/ICU/GLib/compiler APIs fail, isolate compatibility patches or pin an older supported Nixpkgs/toolchain and document the patch hash; **a successful build has not been established by this research**. The [Nixpkgs fetcher reference](https://nixos.org/manual/nixpkgs/stable/#fetchgit) describes fixed-output Git fetching; pin the Nixpkgs input itself rather than relying on a moving channel.
- Headless playback requires an explicit [`audio_output { type "null"; name "Reference null"; mixer_type "none"; }`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/doc/mpdconf.example); the historic example documents this block. `null` avoids ALSA/Pulse/hardware but **does not freeze playback time**. If volume assertions are needed, choose and validate a consistent mixer configuration separately. Configure unique `bind_to_address "127.0.0.1"`, `port`, `music_directory`, `db_file` and `playlist_directory` in per-run temporary writable directories, launch in foreground with `--no-daemon` and stderr logging (inspect the tagged [`CommandLine.cxx`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/CommandLine.cxx) for supported flags). No persistent state file, shared DB, user's default config or shared port; reserve the port and wait for the greeting before issuing commands. The historic [example configuration](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/doc/mpdconf.example) documents these paths and says an omitted `db_file` disables the persistent database.
- Supply small *real* valid WAVs under the music directory, e.g. `a.wav` and `b.wav` with known PCM duration, and add their **relative MPD database paths**. Enable a decoder that recognizes them. Request `update`/`rescan`, then wait for the scan to finish and verify `listallinfo`/`stats` can see both before queue/playback comparisons; the [upstream `update` handler](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/command/OtherCommands.cxx) returns a positive job ID or an ACK, and the [protocol manual's `update`/`status` entries](https://mpd.readthedocs.io/en/latest/protocol.html#command-update) describe `updating_db` as asynchronous. Avoid assuming `OK` following `update` means the songs have been indexed. Use bounded readiness checks / `idle update` on a dedicated connection, and record the fixture file bytes and decoder choice. Create playlist directory only for scenarios requiring stored playlists; reserve isolated sticker storage if testing stickers.

## Shared music fixture and reproducible runs

Use valid, short **silent audio**, not zero-byte files. Embed a few stable tags
(title, artist, album, track number) in the files so upstream MPD and Mopidy
can each scan the *same bytes*. Tagged FLAC is a candidate because the pinned
MPD source has a [FLAC decoder option](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/configure.ac);
first confirm that both installed scanners return the intended tags. A raw WAV
fixture is simpler for a decoder smoke test but may not exercise shared tag
extraction. Store the tiny files in the repository, or commit their generator
and validate content hashes; avoid synthesizing different files at test time.

For Mopidy's real-library side, the bundled
[Mopidy-File backend](https://mopidy.com/ext/file/) reads configured directories
without pre-scanning and scans tags when a file is looked up
([library implementation](https://github.com/mopidy/mopidy/blob/main/src/mopidy/_exts/file/library.py)).
That makes it the smallest real-file adapter for queue and metadata tests.
It cannot search: later database comparisons may use
[Mopidy-Local](https://github.com/mopidy/mopidy-local/blob/main/README.md),
which indexes `local/media_dir` in SQLite before tests. Both adapters expose
Mopidy URIs different from MPD's relative paths, so normalize only an
explicitly documented URI mapping and preserve the raw wire responses.

A committed Nix flake can pin MPD's source commit and hash, Nixpkgs, and build
flags; CI builds that exact oracle and runs the same live test command available
to developers with Nix. Keep the ordinary Python baseline runnable without
Nix. If a separate flake lives below `tests/protocol/`, its lock file also
avoids this repository's root `/*.lock` ignore rule. The first pinned local
build now passes; its CI run is the next verification step.

Start with the [standard Nixpkgs cache](https://nix.dev/manual/nix/2.34/command-ref/conf-file.html#conf-substituters)
for common dependencies and let CI build the pinned historical MPD derivation.
Pinning Nixpkgs does **not** put this custom MPD build on `cache.nixos.org`.
If repeated builds prove costly, publish that output from CI to a Mopidy-owned
binary cache, such as [Cachix](https://docs.cachix.org/getting-started.html),
and make it an optional substituter for contributors. FlakeHub also offers a
[binary cache](https://docs.determinate.systems/flakehub/cache/), but flake
*publishing* is a separate concern and is not necessary to share a flake
already committed to this repository. In all cases, CI still starts the
actual pinned daemon and runs the protocol comparison; cached binaries only
skip rebuilding it.

For an upstream pin update, an explicit **record** run can attach the live
response transcripts and environment provenance to a GitHub Actions artifact
or a reviewable pull request. Normal CI should still start the pinned daemon
and run the comparison live; a recorded transcript is evidence for review, not
the oracle and not a replacement for Mopidy-MPD's `expected` blocks. Keep
upstream observations separate from the behavior asserted by each scenario.

## Where a direct comparison misleads

The existing [scenario guide](../tests/protocol/README.md) says these are **Mopidy-MPD's current behavior**, including limitations; the [runner](../tests/protocol/test_markdown.py) seeds Mopidy-only `dummy:/a` and `dummy:/b` tracks with lengths 40/50 seconds, but with an empty search index and browse tree. MPD does not have this dummy backend. [`QueueCommands.cxx`](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/command/QueueCommands.cxx) routes scheme-bearing URIs to its URL/stream loader, whereas database paths use its database selection. `dummy:/a` therefore cannot be assumed to resolve as a 40-second local song in the live daemon. Translating to `a.wav` changes URI text, metadata, durations, and possibly response shape. Use an explicit mapping for comparable local-song cases; skip or classify cases whose semantics depend on dummy lookup, empty browse/search, unavailable backends or expected `Not implemented` replies. Never silently rewrite the existing baseline as upstream assertions.

The Markdown runner [flattens responses for every command in a step and only checks that expected lines occur](../tests/protocol/test_markdown.py); extra lines, duplicated lines, order, `OK`/`list_OK` placement and absence of fields can escape detection. A live client needs to consume **one complete response per command**, ending at `OK` or `ACK`, and command lists need their own framing. The [upstream ACK formatter](https://github.com/MusicPlayerDaemon/MPD/blob/v0.19.21/src/protocol/Result.cxx) emits `ACK [code@index] {command} text`; the [protocol overview](https://mpd.readthedocs.io/en/latest/protocol.html#failure-responses) specifies error code, command-list offset and command. Compare code/offset/command first; message text may vary with path, configuration or implementation. Do not treat a scenario's Mopidy `ACK [0@0] {...} Not implemented` as an upstream requirement. For selected byte-level comparisons, additionally check exact framing, absence, order and multiplicity instead of applying the subset matcher.

Separate deterministic command/queue observations from asynchronous player/database observations. `status` can change between calls (elapsed, bitrate, state, queue revision, `updating_db`), `stats` has uptime/update timestamps, and `idle` depends on events; [`status` and `stats` definitions](https://mpd.readthedocs.io/en/latest/protocol.html#command-status) describe these fields. Compare invariants or bounded transitions at defined synchronization points rather than captured values. Reinitialize queue, options and directories per case, use a fixed order of commands, avoid sleeps as synchronization, and stop playback before asserting stable state. Exact `ACK` wording, tag order, null mixer volume and position just after `play` should be verified experimentally against the pinned binary before promotion to expectations.

## Initial staged design (superseded by the implementation below)

1. **Prove the oracle:** package/build pinned v0.19.21 with explicit plugin list; log source commit/hash, Nixpkgs revision, `mpd --version`, greeting, config and fixture hash. Smoke-check launch, connection, `status`, `update` completion and discovery of `a.wav`.
2. **Compare the stable intersection:** start with no-media reflection, queue operations using `a.wav`/`b.wav`, and simple DB browsing. Explain the reference fixture and any URI translation beside each comparable scenario; run each against fresh isolated state. Report the live upstream response on failure rather than storing a transcript or maintaining a compatibility matrix.
3. **Extend with guards:** add stored playlists, permissions, errors, then playback/status and asynchronous updates only with explicit readiness/transition rules. Publish divergences as evidence of upstream vs Mopidy behavior, or fixture mismatch, not automatic regressions. Consider a distinct strict oracle suite alongside the existing partial-expectation Markdown baseline.

## First implementation result

The pinned derivation in [`tests/protocol/reference/flake.nix`](../tests/protocol/reference/flake.nix)
builds upstream v0.19.21 with FLAC decoding against the committed Nixpkgs
revision. Its default app runs the comparison with
`nix run ./tests/protocol/reference`, both locally and in CI, without entering
a development shell. The reference runner now replays 31 baseline scenarios
against MPD, with five outstanding framing or connection-lifecycle cases
listed in [`tests/protocol/README.md`](../tests/protocol/README.md). Two cases
also run against Mopidy-MPD using the same tagged silent FLAC files. The shared
files live in
[`tests/protocol/media/`](../tests/protocol/media/). Mopidy's bundled
Mopidy-File backend scans them on lookup and upstream MPD scans them during
its database update, so both extract metadata from the same files. This
verifies one developer environment, not every CI runner or Mopidy-Local's
indexed scanner. The manually dispatched GitHub Actions record mode
uploads refreshed MPD-only responses from
[`tests/protocol/reference/records/`](../tests/protocol/reference/records/).
Normal CI runs the pinned daemon live and checks those records for drift;
Mopidy-MPD's own expectations remain in the Markdown scenarios.

## Open validation questions

- Verify the committed Nix build and live comparison on the GitHub Actions runner; only the local x86_64 Linux build has run so far.
- Is the intended comparison **last 0.19 patch behavior** or behavior shared by all 0.19.x releases? The v0.19.21 oracle establishes only the former.
- Which scenarios merit normalizing URI/metadata and time-varying fields, and which would become misleading after translation? Decide per case based on observed live transcripts.
