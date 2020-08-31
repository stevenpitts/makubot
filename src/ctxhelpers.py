from functools import lru_cache


@lru_cache
def get_invocation(ctx):
    return f"{ctx.prefix}{ctx.invoked_with}"


@lru_cache
def get_bot_nick(ctx):
    return ctx.me.nick if getattr(ctx.me, "nick", None) else ctx.me.name


@lru_cache
def get_content_without_invocation(ctx):
    return ctx.message.content[len(get_invocation(ctx))+1:]


@lru_cache
def get_has_content(ctx):
    return bool(get_content_without_invocation(ctx).strip())


@lru_cache
def get_invoked_command(ctx):
    return ctx.invoked_with.lower()
