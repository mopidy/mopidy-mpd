# Error clearing is advertised but not implemented

The handler exists but cannot clear a playback error.

`status` currently does not track or report an MPD error field. Clearing an
error meaningfully first requires defining and storing that frontend-visible
error state; a bare `OK` would only hide the missing behavior.

```mpd
clearerror
```
```expected
ACK [0@0] {clearerror} Not implemented
```
