# Tag types are per connection

The client can restrict which metadata tags it asks for. Clearing and restoring
the selection affects subsequent `tagtypes` responses on this connection.

Upstream MPD 0.19.21 rejects `tagtypes clear` and `tagtypes enable` as invalid
arguments. Mopidy-MPD accepts them despite advertising protocol 0.19.0. The
[live MPD record](../../reference/records/connection/tagtypes.json) preserves
the actual errors; the expectations below describe Mopidy-MPD.

```mpd
ping
tagtypes clear
tagtypes
```
```expected
OK
```

```mpd
tagtypes enable Artist
tagtypes
```
```expected
tagtype: Artist
OK
```
