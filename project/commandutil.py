import traceback

def get_formatted_traceback(e):
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))
