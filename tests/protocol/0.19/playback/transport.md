# Playback transport uses the current queue

The test track has a 40-second length. `currentsong` reports its queue entry
during playback, and stopping leaves the queue intact.

```mpd
add "dummy:/a"
```
```expected
OK
```

```mpd
play 0
```
```expected
OK
```

```mpd
currentsong
```
```expected
file: dummy:/a
Pos: 0
Id: 1
OK
```

```mpd
stop
status
```
```expected
state: stop
playlistlength: 1
OK
```
