# Playback transport uses the current queue

The test track has a 40-second length. Status and `currentsong` reflect
playback, pause, and stop, while the queue survives stopping.

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
pause 1
```
```expected
OK
```

```mpd
status
```
```expected
state: pause
song: 0
songid: 1
OK
```

```mpd
pause 0
stop
status
```
```expected
state: stop
playlistlength: 1
OK
```
