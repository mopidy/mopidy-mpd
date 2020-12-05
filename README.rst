**********
Mopidy-MPD
**********

.. image:: https://img.shields.io/pypi/v/Mopidy-MPD
    :target: https://pypi.org/project/Mopidy-MPD/
    :alt: Latest PyPI version

.. image:: https://img.shields.io/circleci/build/gh/mopidy/mopidy-mpd
    :target: https://circleci.com/gh/mopidy/mopidy-mpd
    :alt: CircleCI build status

.. image:: https://img.shields.io/codecov/c/gh/mopidy/mopidy-mpd
    :target: https://codecov.io/gh/mopidy/mopidy-mpd
    :alt: Test coverage

`Mopidy`_ extension for controlling Mopidy from MPD clients.

MPD stands for Music Player Daemon, which is also the name of the `original MPD
server project <https://www.musicpd.org/>`_. Mopidy does not depend on the
original MPD server, but implements the MPD protocol itself, and is thus
compatible with most clients built for the original MPD server

.. _Mopidy: https://mopidy.com/


Maintainer wanted
=================

Mopidy-MPD is currently kept on life support by the Mopidy core
developers. It is in need of a more dedicated maintainer.

If you want to be the maintainer of Mopidy-Local, please:

1. Make 2-3 good pull requests improving any part of the project.

2. Read and get familiar with all of the project's open issues.

3. Send a pull request removing this section and adding yourself as the
   "Current maintainer" in the "Credits" section below. In the pull request
   description, please refer to the previous pull requests and state that
   you've familiarized yourself with the open issues.

   As a maintainer, you'll be given push access to the repo and the authority
   to make releases to PyPI when you see fit.


Installation
============

Install by running::

    sudo python3 -m pip install Mopidy-MPD

See https://mopidy.com/ext/mpd/ for alternative installation methods.


Configuration
=============

Before starting Mopidy, you must add configuration for
Mopidy-MPD to your Mopidy configuration file::

    [mpd]
    hostname = ::

.. warning::

    As a simple security measure, the MPD server is by default only available
    from localhost. To make it available from other computers, change the
    ``mpd/hostname`` config value. Before you do so, note that the MPD
    server does not support any form of encryption and only a single clear
    text password (see ``mpd/password``) for weak authentication. Anyone
    able to access the MPD server can control music playback on your computer.
    Thus, you probably only want to make the MPD server available from your
    local network. You have been warned.

The following configuration values are available:

- ``mpd/enabled``:
  If the MPD extension should be enabled or not.

- ``mpd/hostname``:
  Which address the MPD server should bind to.
  This can be a network address or the path toa Unix socket:

  - ``127.0.0.1``: Listens only on the IPv4 loopback interface (default).
  - ``::1``: Listens only on the IPv6 loopback interface.
  - ``0.0.0.0``: Listens on all IPv4 interfaces.
  - ``::``: Listens on all interfaces, both IPv4 and IPv6.
  - ``unix:/path/to/unix/socket.sock``: Listen on the Unix socket at the
    specified path. Must be prefixed with ``unix:``.

- ``mpd/port``:
  Which TCP port the MPD server should listen to.
  Default: 6600.

- ``mpd/password``:
  The password required for connecting to the MPD server.
  If blank, no password is required.
  Default: blank.

- ``mpd/max_connections``:
  The maximum number of concurrent connections the MPD server will accept.
  Default: 20.

- ``mpd/connection_timeout``:
  Number of seconds an MPD client can stay inactive before the connection is
  closed by the server.
  Default: 60.

- ``mpd/zeroconf``:
  Name of the MPD service when published through Zeroconf. The variables
  ``$hostname`` and ``$port`` can be used in the name.
  Set to an empty string to disable Zeroconf for MPD.
  Default: ``Mopidy MPD server on $hostname``

- ``mpd/command_blacklist``:
  List of MPD commands which are disabled by the server.
  By default this blacklists ``listall`` and ``listallinfo``.
  These commands don't fit well with many of Mopidy's backends and are better
  left disabled unless you know what youare doing.

- ``mpd/default_playlist_scheme``:
  The URI scheme used if the server cannot find a backend appropriate for
  creating a playlist from the given tracks.
  Default: ``m3u``


Limitations
===========

This is a non-exhaustive list of MPD features that Mopidy doesn't support.

- Only a single password is supported. It gives all-or-nothing access.
- Toggling of audio outputs is not supported.
- Channels for client-to-client communication are not supported.
- Stickers are not supported.
- Crossfade is not supported.
- Replay gain is not supported.
- ``stats`` does not provide any statistics.
- ``decoders`` does not provide information about available decoders.
- ``tagtypes`` is not supported.
- Live update of the music database is not supported.


Clients
=======

Over the years, a huge number of MPD clients have been built for every thinkable
platform. As always, the quality and state of maintenance varies between clients,
so you might have to try a couple before you find one you like for your purpose.
In general, they should all work with Mopidy-MPD.

The `Wikipedia article on MPD <https://en.wikipedia.org/wiki/Music_Player_Daemon#Clients>`_
has a short list of well-known clients.
In the MPD wiki there is a
`more complete list <https://mpd.fandom.com/wiki/Clients>`_
of the available MPD clients.
Both lists are grouped by user interface, e.g. terminal, graphical, or web-based.


Project resources
=================

- `Source code <https://github.com/mopidy/mopidy-mpd>`_
- `Issue tracker <https://github.com/mopidy/mopidy-mpd/issues>`_
- `Changelog <https://github.com/mopidy/mopidy-mpd/releases>`_


Credits
=======

- Original authors:
  `Stein Magnus Jodal <https://github.com/mopidy>`__ and
  `Thomas Adamcik <https://github.com/adamcik>`__
  for the Mopidy-MPD extension in Mopidy core.
- Current maintainer: None. Maintainer wanted, see section above.
- `Contributors <https://github.com/mopidy/mopidy-mpd/graphs/contributors>`_
