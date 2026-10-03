"""Small Linux filesystem guards used only by opt-in setup commands."""
import contextlib,fcntl,os,pathlib,signal,stat,threading

def regular(path,required=True):
    path=pathlib.Path(path)
    if not os.path.lexists(path):
        if required:raise ValueError('Required file missing: '+str(path))
        return
    if not stat.S_ISREG(path.lstat().st_mode):raise ValueError('Only regular files accepted: '+str(path))

def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def sync_tree(path):
    path=pathlib.Path(path)
    for file in path.rglob('*'):
        if file.is_file() and not file.is_symlink():
            with file.open('rb') as f:os.fsync(f.fileno())
    directories=[x for x in path.rglob('*') if x.is_dir() and not x.is_symlink()]
    for directory in sorted(directories,key=lambda x:len(x.parts),reverse=True):sync_dir(directory)
    sync_dir(path)

@contextlib.contextmanager
def operation_lock(path,commit):
    """Keep the inode: unlinking a lock file permits two different locks."""
    path=pathlib.Path(path);fd=None;previous=None
    try:
        if not commit and not os.path.lexists(path):
            yield;return
        flags=os.O_NOFOLLOW|os.O_CLOEXEC|(os.O_RDWR|os.O_CREAT if commit else os.O_RDONLY)
        fd=os.open(path,flags,0o600);s=os.fstat(fd)
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_nlink!=1:
            raise ValueError('Unsafe operation lock; preserve it and inspect manually')
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Another Aurora operation is running; try again after it finishes')
        if commit and threading.current_thread() is threading.main_thread():
            previous=signal.getsignal(signal.SIGTERM)
            def interrupted(signum,frame):raise InterruptedError('Operation interrupted; rollback will be attempted')
            signal.signal(signal.SIGTERM,interrupted)
        yield
    finally:
        if previous is not None:signal.signal(signal.SIGTERM,previous)
        if fd is not None:os.close(fd)
