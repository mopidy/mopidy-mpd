# Connection control is limited

An unauthenticated server does not require a password. `kill` and `config`
are denied; `close` acknowledges the request and ends this connection.

```mpd
password wrong
```
```expected
ACK [3@0] {password} incorrect password
```

```mpd
kill
```
```expected
ACK [4@0] {kill} you don't have permission for "kill"
```

```mpd
close
```
```expected
OK
```
