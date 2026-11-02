# Raw file browsing is recognized but unavailable

The 0.19 `listfiles` command has a handler but Mopidy's library provider
does not expose arbitrary unrecognized files.

The existing `library.browse` API yields recognized references, not raw file
entries and attributes. Full `listfiles` support needs another source for
unrecognized files rather than reformatting the current browse results.

```mpd
listfiles
```
```expected
ACK [0@0] {listfiles} Not implemented
```
