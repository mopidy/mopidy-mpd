# Reflection advertises commands with differing levels of support

`commands` lists recognized commands, including `crossfade` (which errors)
and `decoders` (which silently returns an empty list). `notcommands` reports
commands denied by the server; the only URI handler here is `dummy`.

The reflection list comes from registered handlers, not their implementation
status. Reporting decoder capabilities accurately would also need a reliable
view of the actual audio pipeline's usable decoders.

```mpd
commands
```
```expected
command: crossfade
command: decoders
command: status
OK
```

```mpd
notcommands
```
```expected
command: config
command: kill
OK
```

```mpd
urlhandlers
```
```expected
handler: dummy
OK
```

```mpd
decoders
```
```expected
OK
```

```mpd
config
```
```expected
ACK [4@0] {config} you don't have permission for "config"
```
