# Pausing retains the current song

The track remains current after playback is paused.

```mpd
add dummy:/a
play
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
