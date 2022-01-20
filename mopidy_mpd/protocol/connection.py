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
def tagtypes(context, *parameters):
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
    parameters = list(parameters)
    if parameters:
        subcommand = parameters.pop(0).lower()
        if subcommand not in ("all", "clear", "disable", "enable"):
            raise exceptions.MpdArgError("Unknown sub command")
        elif subcommand == "all":
            context.session.tagtypes.update(tagtype_list.TAGTYPE_LIST)
        elif subcommand == "clear":
            context.session.tagtypes.clear()
        elif subcommand == "disable":
            _validate_tagtypes(parameters)
            context.session.tagtypes.difference_update(parameters)
        elif subcommand == "enable":
            _validate_tagtypes(parameters)
            context.session.tagtypes.update(parameters)
        return
    return [("tagtype", tagtype) for tagtype in context.session.tagtypes]


def _validate_tagtypes(parameters):
    param_set = set(parameters)
    if not param_set:
        raise exceptions.MpdArgError("Not enough arguments")
    if not param_set.issubset(tagtype_list.TAGTYPE_LIST):
        raise exceptions.MpdArgError("Unknown tag type")
