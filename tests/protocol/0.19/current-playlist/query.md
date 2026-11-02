# Current playlist metadata can be queried by tag

The test library provides named tracks. Only filename matching is implemented
for `playlistfind`; metadata matching and `playlistsearch` fail despite being
recognized. Both searches could inspect the existing Mopidy tracklist entries
in this extension; they do not need a new core search API. `delete` removes a
position from the queue.

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
ACK [0@0] {playlistfind} Not implemented
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
