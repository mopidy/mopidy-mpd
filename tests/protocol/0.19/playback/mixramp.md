# MixRamp options are recognized but unavailable

MixRamp overlap and delay cannot be configured through Mopidy-MPD.

Changing only the protocol replies would not overlap audio. Playback would
need to honor MixRamp tags and mix concurrent tracks.

```mpd
mixrampdb -10
```
```expected
ACK [0@0] {mixrampdb} Not implemented
```

```mpd
mixrampdelay 10
```
```expected
ACK [0@0] {mixrampdelay} Not implemented
```
