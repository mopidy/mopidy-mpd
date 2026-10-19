# Mounts and neighbors are recognized but unavailable

These 0.19 commands have handlers, but none can perform its advertised
operation or list configured remote storage.

Mopidy's current library API can browse configured backends but does not
provide the dynamic storage mount and neighbor discovery these commands need.

```mpd
mount music nfs://example/music
```
```expected
ACK [0@0] {mount} Not implemented
```

```mpd
unmount music
```
```expected
ACK [0@0] {unmount} Not implemented
```

```mpd
listmounts
```
```expected
ACK [0@0] {listmounts} Not implemented
```

```mpd
listneighbors
```
```expected
ACK [0@0] {listneighbors} Not implemented
```
