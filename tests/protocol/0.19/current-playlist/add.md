# Adding a library track changes the current playlist

The test library provides `dummy:/a` and `dummy:/b`. MPD playlist IDs start at
one on a new connection; `playlistinfo` exposes the track metadata.

```mpd
add "dummy:/a"
```
```expected
OK
```

```mpd
playlistinfo
```
```expected
file: dummy:/a
Title: A
Pos: 0
Id: 1
OK
```

```mpd
status
```
```expected
playlistlength: 1
state: stop
OK
```
