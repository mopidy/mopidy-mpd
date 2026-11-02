# Seeking uses the Mopidy playback position

The test track is 40 seconds long. Position-based, ID-based, and relative
seeking all operate on the current track. Its reported elapsed time is tied
to the dummy audio provider's position.

```mpd
add dummy:/a
play
```
```expected
OK
```

```mpd
seek 0 5
```
```expected
OK
```

```mpd
seekid 1 10
```
```expected
OK
```

```mpd
seekcur +5
status
```
```expected
time: 15:40
OK
```
