from functools import lru_cache


@lru_cache
def get_invocation(ctx):
    return f"{ctx.prefix}{ctx.invoked_with}"
