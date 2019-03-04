from . import tokens
from . import makubot
import sys

if bool('test' in sys.argv) == bool('real' in sys.argv):
    raise ValueError(
        'You must pass only one of "test" or "real" in args.')
token = (tokens.makumistakeToken if 'test' in sys.argv
         else tokens.makubotToken)
makubot.MakuBot().run(token)
