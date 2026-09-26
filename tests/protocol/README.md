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
