# Replay gain cannot be changed

The setter is recognized but unimplemented. The reported mode stays off.

To make a different mode effective, the audio path would need to apply track
or album gain; this handler cannot provide that behavior on its own.

```mpd
replay_gain_mode track
```
```expected
ACK [0@0] {replay_gain_mode} Not implemented
```

```mpd
replay_gain_status
```
```expected
replay_gain_mode: off
OK
```
