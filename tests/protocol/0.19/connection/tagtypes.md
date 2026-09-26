# Tag types are per connection

The client can restrict which metadata tags it asks for. Clearing and restoring
the selection affects subsequent `tagtypes` responses on this connection.

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
