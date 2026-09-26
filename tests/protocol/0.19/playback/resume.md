# Resuming a paused song

Mopidy-MPD accepts `pause 0` to resume playback. The pinned MPD reference
sometimes closes its connection during this transition; that path remains
outside the live-record suite pending investigation.

```mpd
add dummy:/a
play
pause 1
pause 0
```
```expected
OK
```

```mpd
status
```
```expected
state: play
OK
```
