# mopidy-mpd

[![Latest PyPI version](https://img.shields.io/pypi/v/mopidy-mpd)](https://pypi.org/p/mopidy-mpd)
[![CI build status](https://img.shields.io/github/actions/workflow/status/mopidy/mopidy-mpd/ci.yml)](https://github.com/mopidy/mopidy-mpd/actions/workflows/ci.yml)
[![Test coverage](https://img.shields.io/codecov/c/gh/mopidy/mopidy-mpd)](https://codecov.io/gh/mopidy/mopidy-mpd)

[Mopidy](https://mopidy.com/) extension for controlling Mopidy from MPD
clients.

MPD stands for Music Player Daemon, which is also the name of the
[original MPD server project](https://www.musicpd.org/). Mopidy does not
depend on the original MPD server, but implements the MPD protocol
itself, and is thus compatible with most clients built for the original
MPD server.

## Maintainer wanted

Mopidy-MPD is currently kept on life support by the Mopidy core
developers. It is in need of a more dedicated maintainer.

If you want to be the maintainer of Mopidy-MPD, please:

1.  Make 2-3 good pull requests improving any part of the project.

2.  Read and get familiar with all of the project's open issues.

3.  Send a pull request removing this section and adding yourself as the
    "Current maintainer" in the "Credits" section below. In the pull
    request description, please refer to the previous pull requests and
    state that you've familiarized yourself with the open issues.

    As a maintainer, you'll be given push access to the repo and the
    authority to make releases to PyPI when you see fit.

## Installation

Install by running:

```sh
python3 -m pip install mopidy-mpd
```

See https://mopidy.com/ext/mpd/ for alternative installation methods.

## Configuration

Before starting Mopidy, you must add configuration for
mopidy-mpd to your Mopidy configuration file:

```ini
[mpd]
hostname = ::
```

> [!WARNING]
> As a simple security measure, the MPD server is by default only available from
> localhost. To make it available from other computers, change the
> `mpd/hostname` config value.
>
> Before you do so, note that the MPD server does not support any form of
> encryption and only a single clear text password (see `mpd/password`) for weak
> authentication. Anyone able to access the MPD server can control music
> playback on your computer. Thus, you probably only want to make the MPD server
> available from your local network. You have been warned.

The following configuration values are available:

- `mpd/enabled`: If the MPD extension should be enabled or not.
- `mpd/hostname`: Which address the MPD server should bind to. This
  can be a network address or the path toa Unix socket:
  - `127.0.0.1`: Listens only on the IPv4 loopback interface
    (default).
  - `::1`: Listens only on the IPv6 loopback interface.
  - `0.0.0.0`: Listens on all IPv4 interfaces.
  - `::`: Listens on all interfaces, both IPv4 and IPv6.
  - `unix:/path/to/unix/socket.sock`: Listen on the Unix socket at
    the specified path. Must be prefixed with `unix:`.
- `mpd/port`: Which TCP port the MPD server should listen to. Default: 6600.
- `mpd/password`: The password required for connecting to the MPD
  server. If blank, no password is required. Default: blank.
- `mpd/max_connections`: The maximum number of concurrent connections
  the MPD server will accept. Default: 20.
- `mpd/connection_timeout`: Number of seconds an MPD client can stay
  inactive before the connection is closed by the server. Default: 60.
- `mpd/zeroconf`: Name of the MPD service when published through
  Zeroconf. The variables `$hostname` and `$port` can be used in the
  name. Set to an empty string to disable Zeroconf for MPD. Default:
  `Mopidy MPD server on $hostname`
- `mpd/command_blacklist`: List of MPD commands which are disabled by
  the server. By default this blacklists `listall` and `listallinfo`.
  These commands don't fit well with many of Mopidy's backends and
  are better left disabled unless you know what you are doing.
- `mpd/default_playlist_scheme`: The URI scheme used if the server
  cannot find a backend appropriate for creating a playlist from the
  given tracks. Default: `m3u`

## Limitations

This is a non-exhaustive list of MPD features that Mopidy doesn't
support.

- Only a single password is supported. It gives all-or-nothing access.
- Toggling of audio outputs is not supported.
- Channels for client-to-client communication are not supported.
- Stickers are not supported.
- Crossfade is not supported.
- Replay gain is not supported.
- `stats` does not provide any statistics.
- `decoders` does not provide information about available decoders.
- Live update of the music database is not supported.

## Clients

Over the years, a huge number of MPD clients have been built for every
thinkable platform. As always, the quality and state of maintenance
varies between clients, so you might have to try a couple before you
find one you like for your purpose. In general, they should all work
with Mopidy-MPD.

The [Wikipedia article on
MPD](https://en.wikipedia.org/wiki/Music_Player_Daemon#Clients) has a
short list of well-known clients. In the MPD wiki there is a [more
complete list](https://mpd.fandom.com/wiki/Clients) of the available MPD
clients. Both lists are grouped by user interface, e.g. terminal,
graphical, or web-based

## Project resources

- [Source code](https://github.com/mopidy/mopidy-mpd)
- [Issues](https://github.com/mopidy/mopidy-mpd/issues)
- [Releases](https://github.com/mopidy/mopidy-mpd/releases)

## Development

### Set up development environment

Clone the repo using, e.g. using [gh](https://cli.github.com/):

```sh
gh repo clone mopidy/mopidy-mpd
```

Enter the directory, and install dependencies using [uv](https://docs.astral.sh/uv/):

```sh
cd mopidy-mpd/
uv sync
```

### Running tests

To run all tests and linters in isolated environments, use
[tox](https://tox.wiki/):

```sh
tox
```

To only run tests, use [pytest](https://pytest.org/):

```sh
pytest
```

To format the code, use [ruff](https://docs.astral.sh/ruff/):

```sh
ruff format .
```

To check for lints with ruff, run:

```sh
ruff check .
```

To check for type errors, use [pyright](https://microsoft.github.io/pyright/):

```sh
pyright .
```

### Making a release

To make a release to PyPI, go to the project's [GitHub releases
page](https://github.com/mopidy/mopidy-mpd/releases)
and click the "Draft a new release" button.

In the "choose a tag" dropdown, select the tag you want to release or create a
new tag, e.g. `v0.1.0`. Add a title, e.g. `v0.1.0`, and a description of the changes.

Decide if the release is a pre-release (alpha, beta, or release candidate) or
should be marked as the latest release, and click "Publish release".

Once the release is created, the `release.yml` GitHub Action will automatically
build and publish the release to
[PyPI](https://pypi.org/project/mopidy-mpd/).

## Credits

- Original author: [Stein Magnus Jodal](https://github.com/jodal) and
  [Thomas Adamcik](https://github.com/adamcik) for the Mopidy-MPD
  extension in Mopidy core.
- Current maintainer: None. Maintainer wanted, see section above.
- [Contributors](https://github.com/mopidy/mopidy-mpd/graphs/contributors)
