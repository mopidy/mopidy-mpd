# Stickers are recognized but unavailable

The sticker subcommands share one handler. Sticker storage is not provided,
and `sticker` does not appear in the ordinary `commands` listing.

A Mopidy-MPD-owned persistent sticker store could provide these operations
without requiring Mopidy's library backends to store stickers. It would need
consistent URI handling and cleanup rules across connections.

```mpd
sticker list song dummy:/a
```
```expected
ACK [0@0] {sticker} Not implemented
```
