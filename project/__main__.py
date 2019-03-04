from . import tokens
from . import makubot
import sys

if bool('test' in sys.argv) == bool('real' in sys.argv):
    raise ValueError('You must pass only one of "test" or "real" in args.')
if 'test' in sys.argv and tokens.testToken is None:
    raise ValueError(
        'You must replace testToken in tokens.py with your own test token first.')
elif 'real' in sys.argv and tokens.realToken is NOne:
    raise ValueError(
        'You must replace realToken in tokens.py with your own token first.')
token = tokens.testToken if 'test' in sys.argv else tokens.realToken
makubot.MakuBot().run(token)
