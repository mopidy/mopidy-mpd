# An incorrect password is rejected

Mopidy-MPD has no password configured in this fixture. A password command
with the wrong value returns an authentication error.

```mpd
password wrong
```
```expected
ACK [3@0] {password} incorrect password
```
