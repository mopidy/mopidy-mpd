# Queue priority and song ranges are unavailable

The 0.19 priority, range, and volatile tag commands are recognized, but no
queue priority or per-song range or tag editing is implemented.

Mopidy's tracklist owns random playback order, so priorities would need
tracklist support or a separate playback-order implementation. Per-song ranges
would need playback to enforce their end points. Volatile tags could live in
Mopidy-MPD, but they would need to follow shared queue entries across client
connections and affect all metadata responses consistently.

```mpd
prio 10 0:1
```
```expected
ACK [0@0] {prio} Not implemented
```

```mpd
prioid 10 1
```
```expected
ACK [0@0] {prioid} Not implemented
```

```mpd
rangeid 1 0:10
```
```expected
ACK [0@0] {rangeid} Not implemented
```

```mpd
addtagid 1 Title new
```
```expected
ACK [0@0] {addtagid} Not implemented
```

```mpd
cleartagid 1 Title
```
```expected
ACK [0@0] {cleartagid} Not implemented
```
