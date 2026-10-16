# Search-to-playlist can create an empty stored playlist

The test backend has no search index, even though it can look up the two test
tracks. Searching therefore adds nothing, but `searchaddpl` still creates the
named playlist and returns success.

```mpd
searchaddpl searched title A
```
```expected
OK
```

```mpd
listplaylists
```
```expected
playlist: searched
OK
```

```mpd
listplaylist searched
```
```expected
OK
```
