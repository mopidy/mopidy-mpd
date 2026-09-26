# Current playlist metadata can be queried by tag

The test library provides named tracks. `playlistfind` supports exact filename,
Title, Genre, Comment, and MUSICBRAINZ_TRACKID matching in the current queue,
including the matching position and ID. Tag names are case-insensitive; values
match exactly. Other metadata tags and `playlistsearch` remain unsupported
despite being recognized. `delete` removes a position from the queue.

```mpd
add dummy:/a
add dummy:/b
```
```expected
OK
```

```mpd
playlist
```
```expected
file: dummy:/a
file: dummy:/b
OK
```

```mpd
playlistfind filename dummy:/a
```
```expected
file: dummy:/a
OK
```

```mpd
playlistfind Title A
```
```expected
file: dummy:/a
Title: A
Pos: 0
Id: 1
OK
```

```mpd
playlistfind TiTle A
```
```expected
file: dummy:/a
Title: A
Pos: 0
Id: 1
OK
```

The dummy tracks have no Genre, Comment, or MusicBrainz track ID. Looking for
these tags returns no queue entries.

```mpd
playlistfind Genre Example
```
```expected
OK
```

```mpd
playlistfind Comment Example
```
```expected
OK
```

```mpd
playlistfind MUSICBRAINZ_TRACKID Example
```
```expected
OK
```

```mpd
playlistsearch Title B
```
```expected
ACK [0@0] {playlistsearch} Not implemented
```

```mpd
delete 0
status
```
```expected
playlistlength: 1
OK
```
