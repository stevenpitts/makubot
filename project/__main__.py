from . import makubot
import sys
import os
from pathlib import Path
try:
    from . import tokens
except ImportError:
    if not os.path.isfile(str(Path(__file__).parent / 'tokens.py')):
        with open(str(Path(__file__).parent / 'tokens.py'), 'w') as f:
            f.write('realToken = None\ntestToken = None\ngoogleAPI = None\n')
    from . import tokens
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
DATA_DIR = PARENT_DIR / 'data'


for data_dir_folder in ['picture_associations',
                        'picture_reactions',
                        'saved_attachments',
                        'working_directory']:
    os.makedirs(str(DATA_DIR / data_dir_folder), exist_ok=True)

default_text = {'reminders.txt': '[]',
                'makubot.log': '',
                'free_reign.txt': '[]',
                'deletion_log.txt': ''}
for filename, to_write in default_text.items():
    if not os.path.isfile(str(DATA_DIR / filename)):
        with open(str(DATA_DIR / filename), 'w') as f:
            f.write(to_write)

if bool('test' in sys.argv) == bool('real' in sys.argv):
    raise ValueError('You must pass only one of "test" or "real" in args.')
if 'test' in sys.argv and tokens.testToken is None:
    raise ValueError(
        'You must replace testToken in tokens.py '
        'with your own test token first.')
elif 'real' in sys.argv and tokens.realToken is None:
    raise ValueError(
        'You must replace realToken in tokens.py '
        'with your own token first.')
token = tokens.testToken if 'test' in sys.argv else tokens.realToken
makubot.MakuBot().run(token)
