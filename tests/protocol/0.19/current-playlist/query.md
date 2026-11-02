# Current playlist metadata can be queried by tag

The test library provides tagged tracks. `playlistfind` matches values exactly;
`playlistsearch` matches substrings without regard to case. Both query the
current queue by filename, track metadata, or `any` metadata tag and return
every match with its position and ID. Tag names are case-insensitive, and `any`
does not search filenames. Mopidy tracks have no separate MPD `Name` field, so
that tag has no match here. `delete` removes a position from the queue.

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

```mpd
playlistfind file dummy:/a
```
```expected
file: dummy:/a
Pos: 0
Id: 1
OK
```

```mpd
playlistfind Artist Example
```
```expected
file: dummy:/a
Pos: 0
Id: 1
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistfind Album "Protocol fixture"
```
```expected
file: dummy:/a
Pos: 0
Id: 1
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistfind AlbumArtist Example
```
```expected
file: dummy:/a
Pos: 0
Id: 1
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistfind Track 1
```
```expected
file: dummy:/a
Pos: 0
Id: 1
OK
```

```mpd
playlistfind any Example
```
```expected
file: dummy:/a
Pos: 0
Id: 1
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistfind any dummy:/a
```
```expected
OK
```

```mpd
playlistfind Name A
```
```expected
OK
```

```mpd
playlistfind bogus Example
```
```expected
ACK [2@0] {playlistfind} incorrect arguments
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
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistsearch TiTle a
```
```expected
file: dummy:/a
Pos: 0
Id: 1
OK
```

```mpd
playlistsearch filename b
```
```expected
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistsearch Artist AMP
```
```expected
file: dummy:/a
Pos: 0
Id: 1
file: dummy:/b
Pos: 1
Id: 2
OK
```

```mpd
playlistsearch any dummy:/a
```
```expected
OK
```

```mpd
playlistsearch bogus A
```
```expected
ACK [2@0] {playlistsearch} incorrect arguments
```

```mpd
delete 0
status
```
```expected
playlistlength: 1
OK
```

Adding the same track twice creates distinct queue entries. Filename and Title
lookups return each entry with its own position and ID.

```mpd
add dummy:/a
add dummy:/a
```
```expected
OK
```

```mpd
playlistfind Title A
```
```expected
file: dummy:/a
Pos: 1
Id: 3
Pos: 2
Id: 4
OK
```

```mpd
playlistfind filename dummy:/a
```
```expected
file: dummy:/a
Pos: 1
Id: 3
Pos: 2
Id: 4
OK
```

```mpd
playlistsearch Title a
```
```expected
file: dummy:/a
Pos: 1
Id: 3
Pos: 2
Id: 4
OK
```
