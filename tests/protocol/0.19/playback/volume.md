# Volume changes use the Mopidy mixer

`setvol` sets an absolute percentage, while the deprecated `volume` command
adds a relative adjustment. Status reports the effective volume.

```mpd
setvol 40
status
```
```expected
volume: 40
OK
```

```mpd
volume +10
status
```
```expected
volume: 50
OK
```
