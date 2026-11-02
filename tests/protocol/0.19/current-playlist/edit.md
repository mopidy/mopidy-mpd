# Current playlist positions and IDs follow queue edits

Both tracks are available in the test library. `addid` reports an ID, while
`move`, `moveid`, `swap`, `swapid`, and `deleteid` edit the same queue.
`plchanges` and `plchangesposid` report edits since a playlist version.

```mpd
addid "dummy:/a"
```
```expected
Id: 1
OK
```

```mpd
addid "dummy:/b"
```
```expected
Id: 2
OK
```

```mpd
move 1 0
```
```expected
OK
```

```mpd
moveid 2 1
swap 0 1
```
```expected
OK
```

```mpd
playlistinfo 0
```
```expected
file: dummy:/b
Id: 2
OK
```

```mpd
swapid 1 2
```
```expected
OK
```

```mpd
playlistid 1
```
```expected
file: dummy:/a
Id: 1
OK
```

```mpd
plchangesposid 0
```
```expected
cpos: 0
Id: 1
OK
```

```mpd
plchanges 0
```
```expected
file: dummy:/a
OK
```

```mpd
shuffle
```
```expected
OK
```

```mpd
deleteid 2
```
```expected
OK
```

```mpd
clear
```
```expected
OK
```

```mpd
status
```
```expected
playlistlength: 0
OK
```
