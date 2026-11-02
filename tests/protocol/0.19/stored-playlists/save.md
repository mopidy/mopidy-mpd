# An empty queue can be saved as a stored playlist

The dummy playlist backend supports saving, listing, and removing a named
playlist. This exercises stored-playlist commands without requiring music files.

```mpd
save "example"
```
```expected
OK
```

```mpd
listplaylists
```
```expected
playlist: example
OK
```

```mpd
rm "example"
```
```expected
OK
```
