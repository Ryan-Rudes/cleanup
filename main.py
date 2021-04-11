from rich.traceback import install
from rich.filesize import decimal
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel
from rich.progress import *
from rich.live import Live
from rich import print

from collections import defaultdict
from hashlib import md5
from tqdm import tqdm
import pickle
import os

install()

BLOCKSIZE = 65536
PRINTSIZE = 100

path = Prompt.ask('Enter the filepath of the root directory in which to search for duplicates')

if not os.path.exists(path):
    raise FileNotFoundError('Directory not found')

hashfn = md5()
archive = {}

console = Console()
table = Table()
table.add_column('Original', style = 'green')
table.add_column('Duplicate', style = 'red')
table.add_column('MD5 Hash', style = 'blue')
table.add_column('Size', style = 'cyan')

pbar = [
    SpinnerColumn(),
    "[progress.description]{task.description}",
    BarColumn(),
    "[progress.percentage]{task.percentage:>3.0f}%",
    TimeRemainingColumn()
]

print ('Starting', end = '')
filecount = 0
for i, (root, dirs, files) in enumerate(os.walk(path)):
    filecount += len(files)
    if i % 10000 == 0:
        print('.', end = '')
print ()

with Progress(*pbar) as progress:
    task = progress.add_task('Computing total size', total = filecount)
    total = 0
    for root, dirs, files in os.walk(path):
        for name in files:
            filepath = os.path.join(root, name)
            if os.path.exists(filepath):
                total += os.path.getsize(filepath)
                progress.advance(task)

duplicates = defaultdict(list)
freespace = 0
b = bytearray(BLOCKSIZE)
mv = memoryview(b)

with Progress(*[*pbar, FileSizeColumn(), 'of', TotalFileSizeColumn(), TransferSpeedColumn()]) as progress:
    task = progress.add_task('Hashing files', total = total)

    for root, dirs, files in os.walk(path):
        for name in files:
            filepath = os.path.join(root, name)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                if not size:
                    continue

                hashfn = md5()
                with open(filepath, 'rb', buffering = 0) as f:
                    for n in iter(lambda: f.readinto(mv), 0):
                        hashfn.update(mv[:n])
                        progress.advance(task, n)

                hashed = hashfn.digest()

                if hashed in archive:
                    freespace += size
                    original = archive[hashed]
                    duplicates[original].append(filepath)
                    table.add_row(original, filepath, hashfn.hexdigest(), decimal(size))
                    if len(table.rows) == PRINTSIZE:
                        console.print(table)
                        print(Panel(decimal(freespace), title = 'Freed up space!'))
                        table.rows.clear()
                        for column in table.columns:
                            column._cells.clear()
                else:
                    archive[hashed] = filepath

with open('hashdict.pkl', 'wb') as f:
    pickle.dump(archive, f)

with open('duplicates.pkl', 'wb') as f:
    pickle.dump(duplicates, f)
