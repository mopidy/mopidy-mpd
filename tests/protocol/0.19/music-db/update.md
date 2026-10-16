# Database update requests only return a placeholder job ID

Both update and rescan acknowledge the request with job ID zero; neither
actually refreshes the dummy library or schedules an MPD database job.

Mopidy core already exposes `library.refresh(uri)`. Mopidy-MPD could call it,
but a real MPD update job ID and `status` lifecycle would need tracking here;
whether rescan can inspect unchanged files depends on each library backend.

```mpd
update
```
```expected
updating_db: 0
OK
```

```mpd
rescan
```
```expected
updating_db: 0
OK
```
