# Database searches depend on backend search capabilities

The test library contains two lookup-able tracks but does not index them for
search. An exact count therefore returns zero, and adding search results
leaves the current queue empty. A successful response is not evidence of a
complete MPD music database.

The commands already delegate to Mopidy's library search API. A backend that
indexes tracks can return results without changing Mopidy-MPD; this fixture's
search provider deliberately returns none.

```mpd
count title A
```
```expected
songs: 0
playtime: 0
OK
```

```mpd
find title A
```
```expected
OK
```

```mpd
search title A
```
```expected
OK
```

```mpd
findadd title A
searchadd title A
status
```
```expected
playlistlength: 0
OK
```
