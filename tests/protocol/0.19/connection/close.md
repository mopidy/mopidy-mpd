# Closing the client connection

Mopidy-MPD acknowledges `close` and ends this connection. The upstream response
is still outstanding because the reference runner expects a response terminator.

```mpd
close
```
```expected
OK
```
