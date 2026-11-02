# Next and previous navigate the queue

The test library provides two playable tracks. `playid` starts a specific
queue entry, and both skip commands acknowledge playback changes.

```mpd
add dummy:/a
add dummy:/b
playid 1
```
```expected
OK
```

```mpd
next
status
```
```expected
songid: 2
state: play
OK
```

```mpd
previous
status
```
```expected
songid: 1
state: play
OK
```
