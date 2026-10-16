# Crossfade is advertised but unavailable

The command is recognized, but Mopidy core cannot crossfade. It returns an
error and status continues to report zero seconds.

Reporting a nonzero value alone would mislead clients: actual crossfading
would require playback or audio-mixing support below this protocol handler.

```mpd
crossfade 10
```
```expected
ACK [0@0] {crossfade} Not implemented
```

```mpd
status
```
```expected
xfade: 0
playlist: *
OK
```
