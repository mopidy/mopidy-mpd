from mopidy_mpd import exceptions, protocol
from mopidy_mpd.protocol import tagtype_list


@protocol.commands.add("close", auth_required=False)
def close(context):
    """
    *musicpd.org, connection section:*

        ``close``

        Closes the connection to MPD.
    """
    context.session.close()


@protocol.commands.add("kill", list_command=False)
def kill(context):
    """
    *musicpd.org, connection section:*

        ``kill``

        Kills MPD.
    """
    raise exceptions.MpdPermissionError(command="kill")


@protocol.commands.add("password", auth_required=False)
def password(context, password):
    """
    *musicpd.org, connection section:*

        ``password {PASSWORD}``

        This is used for authentication with the server. ``PASSWORD`` is
        simply the plaintext password.
    """
    if password == context.password:
        context.dispatcher.authenticated = True
    else:
        raise exceptions.MpdPasswordError("incorrect password")


@protocol.commands.add("ping", auth_required=False)
def ping(context):
    """
    *musicpd.org, connection section:*

        ``ping``

        Does nothing but return ``OK``.
    """
    pass


@protocol.commands.add("tagtypes")
def tagtypes(context, *args):
    """
    *mpd.readthedocs.io, connection settings section:*

        ``tagtypes``

        Shows a list of available song metadata.

        ``tagtypes disable {NAME...}``

        Remove one or more tags from the list of tag types the client is interested in.

        ``tagtypes enable {NAME...}``

        Re-enable one or more tags from the list of tag types for this client.

        ``tagtypes clear``

        Clear the list of tag types this client is interested in.

        ``tagtypes all``

        Announce that this client is interested in all tag types.
    """
    if not args:
        pass
    elif args[0] == "all":
        context.session.tagtypes = tagtype_list.TAGTYPE_LIST[:]
    elif args[0] == "clear":
        context.session.tagtypes.clear()
    elif args[0] == "disable":
        context.session.tagtypes = [
            value for value in context.session.tagtypes if value not in args[1:]
        ]
    elif args[0] == "enable":
        enabled_types = [
            value for value in args[1:] if value not in context.session.tagtypes
        ]
        context.session.tagtypes.extend(enabled_types)
    else:
        raise exceptions.MpdArgError("Unknown sub command")

    tagtypes = [
        value
        for value in context.session.tagtypes
        if value in tagtype_list.TAGTYPE_LIST
    ]
    return [("tagtype", tagtype) for tagtype in tagtypes]
