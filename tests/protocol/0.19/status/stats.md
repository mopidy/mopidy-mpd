# Database statistics are placeholders

Mopidy does not expose MPD's database statistics here. The statistics command
returns zeroes even though the test library contains two tracks. Some clients
may treat these zeroes as a signal that they are connected to Mopidy, so this
placeholder response may have become a compatibility behavior.

Accurate database totals and update times would require aggregating library
backend data that this handler does not currently receive. Replacing the
zeroes also needs care because of the possible client fingerprint above.

```mpd
stats
```
```expected
artists: 0
albums: 0
songs: 0
db_update: 0
OK
```
