# Stored playlist tracks load into the current queue

The test library contains `dummy:/a`. A stored playlist can be created by
adding that URI and then loaded back into the current queue.

```mpd
playlistadd example dummy:/a
```
```expected
OK
```

```mpd
listplaylist example
```
```expected
file: dummy:/a
OK
```

```mpd
load example
```
```expected
OK
```

```mpd
playlistinfo
```
```expected
file: dummy:/a
Pos: 0
OK
```

```mpd
status
```
```expected
playlistlength: 1
OK
```
