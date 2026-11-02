# Adding a missing track fails without changing the queue

The test library contains `dummy:/a` and `dummy:/b`. A URI that it cannot
resolve produces an MPD error; the empty current playlist remains empty.

```mpd
add "dummy:/missing"
```
```expected
ACK [50@0] {add} directory or file not found
```

```mpd
status
```
```expected
playlistlength: 0
state: stop
OK
```
