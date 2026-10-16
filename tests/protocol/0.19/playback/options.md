# Playback options appear in status

Repeat, random, single, and consume are backed by Mopidy tracklist settings.
An empty playlist remains stopped even when these options change.

```mpd
repeat 1
consume 1
random 1
single 1
status
```
```expected
repeat: 1
consume: 1
random: 1
single: 1
playlist: *
playlistlength: 0
state: stop
OK
```

```mpd
repeat 0
consume 0
random 0
single 0
status
```
```expected
repeat: 0
consume: 0
random: 0
single: 0
OK
```
