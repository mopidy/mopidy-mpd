# Killing MPD is denied

Mopidy-MPD denies `kill`; upstream MPD may instead shut down the daemon.

```mpd
kill
```
```expected
ACK [4@0] {kill} you don't have permission for "kill"
```
