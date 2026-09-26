# Stored playlist edits persist through the dummy backend

The test library supplies two tracks. Their order can be changed and entries
removed without altering the current playback queue.

```mpd
playlistadd example dummy:/a
playlistadd example dummy:/b
```
```expected
OK
```

```mpd
listplaylistinfo example
```
```expected
file: dummy:/a
file: dummy:/b
OK
```

```mpd
playlistmove example 1 0
listplaylist example
```
```expected
file: dummy:/b
OK
```

```mpd
playlistdelete example 1
listplaylist example
```
```expected
file: dummy:/b
OK
```

```mpd
rename example renamed
```
```expected
OK
```

```mpd
playlistclear renamed
listplaylist renamed
```
```expected
OK
```
