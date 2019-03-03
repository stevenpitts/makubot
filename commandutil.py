import traceback


async def send_formatted_message(recipient, msg):
    for i in range(0, len(msg), 1500):
        await recipient.send(r"```"+msg[i:i+1500]+r"```")


def get_formatted_traceback(e):
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))


known_ids = {"aagshit": 322509699159162883,
             "aagshit_lawgs": 541742610604359720,
             "lilybots": [287343736046878730]}
