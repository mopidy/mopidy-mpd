# The only reported output is a mute switch

Mopidy maps MPD output ID zero to its mixer mute state. The output is named
`Mute`, rather than describing a physical audio device.

```mpd
outputs
```
```expected
outputid: 0
outputname: Mute
outputenabled: 0
OK
```

```mpd
enableoutput 0
outputs
```
```expected
outputenabled: 1
OK
```

```mpd
toggleoutput 0
outputs
```
```expected
outputenabled: 0
OK
```

```mpd
disableoutput 7
```
```expected
ACK [50@0] {disableoutput} No such audio output
```
