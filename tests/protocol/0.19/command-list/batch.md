# Command lists defer execution until the end marker

In `command_list_ok_begin` mode each successful command emits `list_OK`, then
the list ends with `OK`. A normal command list ends with one `OK`.

```mpd
command_list_ok_begin
ping
status
command_list_end
```
```expected
list_OK
state: stop
OK
```

```mpd
command_list_begin
ping
command_list_end
```
```expected
OK
```
