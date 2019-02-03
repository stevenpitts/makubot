import traceback

async def send_formatted_message(recipient,msg):
    for i in range(0, len(msg), 1500):
        await recipient.send(r"```"+msg[i:i+1500]+r"```")
async def get_formatted_traceback(e):
    return ''.join(traceback.format_exception(type(e), e, e.__traceback__))