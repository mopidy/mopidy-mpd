# Client-to-client channels are recognized but unavailable

All five channel commands are exposed by the dispatcher but have no backing
implementation. Each returns a protocol error.

Channels concern MPD client connections, not the music library. A shared
subscription and message store in the MPD frontend could implement them
without changes to Mopidy core.

```mpd
subscribe news
```
```expected
ACK [0@0] {subscribe} Not implemented
```

```mpd
unsubscribe news
```
```expected
ACK [0@0] {unsubscribe} Not implemented
```

```mpd
channels
```
```expected
ACK [0@0] {channels} Not implemented
```

```mpd
readmessages
```
```expected
ACK [0@0] {readmessages} Not implemented
```

```mpd
sendmessage news hello
```
```expected
ACK [0@0] {sendmessage} Not implemented
```
