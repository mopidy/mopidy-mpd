# Library browsing depends on backend references

The test library can look up individual tracks but has no browse tree, so
`lsinfo` and `listallinfo` return no track entries. `listall` reports a
not-found error for an unknown path. The list of distinct tags is empty.

These commands already use Mopidy's library browse and distinct-tag APIs.
Providing a browse tree and tag index is a backend concern, not a missing
protocol handler.

```mpd
lsinfo
```
```expected
OK
```

```mpd
listallinfo
```
```expected
OK
```

```mpd
listall /unknown
```
```expected
ACK [50@0] {listall} Not found
```

```mpd
list Artist
```
```expected
OK
```
