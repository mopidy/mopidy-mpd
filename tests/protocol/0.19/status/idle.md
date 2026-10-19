# A waiting connection can cancel idle mode

`idle` waits instead of sending an immediate reply. `noidle` releases the
same session and sends the final `OK` when there are no pending events.

```mpd
idle player
noidle
```
```expected
OK
```
