"""Replace a file in one step, so a reader never sees half of it.

The new content goes to a temp file in the same directory, then os.replace() swaps it in: a reader
that opens the file mid-write gets the old bytes or the new ones, never a partial zip or a cut row.
Before this, `np.savez` wrote the advise-path caches in place and two whole-file jsonl rewrites
opened their target with "w". What the old `open(path, "wb")` did otherwise is kept: a symlink is
written through (its target is replaced, the link stays), a file we may not write is refused with
PermissionError, and the file keeps its mode and its ACL entries (a temp file inherits only the
directory's default ACL, so named entries on the file itself are copied across).

One exception: a rename by a user who does not own the file hands the file to that user. On a host
where one user's config points at verdict streams in another user's home, that would leave the owner
unable to write its own file (the same failure once hit a shared SQLite store). So a file that belongs
to someone else is rewritten in place, as before, and replace() returns False. The callers today do
not act on that: for them the in-place write is simply the old behaviour.

Covered by tests: atomicity, mode, ACL (mask included), symlink (dangling too), read-only, owner.
Not covered: fsync (durability is not observable without a crash).
"""
import contextlib
import errno
import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

_UMASK = os.umask(0)
os.umask(_UMASK)
_ACL = "system.posix_acl_access"


def _acl(path) -> bytes | None:
    """The file's access ACL, if this OS and filesystem have one (Linux xattr); else None."""
    try:
        return os.getxattr(path, _ACL)
    except AttributeError:          # no xattr API on this OS
        return None
    except OSError as e:
        # no ACL on the file, or none on this filesystem: nothing to copy. Anything else (EACCES, EPERM...)
        # means the swap keeps the mode but may drop ACL entries, and that is said, on stderr (never stdout:
        # this runs inside the MCP path).
        if e.errno not in (getattr(errno, "ENODATA", None), errno.ENOTSUP, errno.EOPNOTSUPP):
            print(f"[atomic] {path}: ACL not read ({e.strerror}); the swap keeps the mode only", file=sys.stderr)
        return None


def replace(path, write: Callable[[BinaryIO], object]) -> bool:
    """Write `path` through write(fh), fh a binary file. True: swapped in atomically. False: the file
    belongs to another user, so it was rewritten in place (its owner kept)."""
    path = Path(os.path.realpath(path))
    st = path.stat() if path.exists() else None
    if st is not None and not os.access(path, os.W_OK):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(path))
    if st is not None and st.st_uid != os.geteuid():
        with open(path, "wb") as fh:
            write(fh)
        return False
    acl = _acl(path) if st is not None else None
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            write(fh)
            fh.flush()
            os.fsync(fh.fileno())
        # mkstemp makes 0600; keep the old mode (and with it the ACL mask), or the umask default
        os.chmod(tmp, (st.st_mode & 0o7777) if st is not None else (0o666 & ~_UMASK))
        if acl is not None:
            os.setxattr(tmp, _ACL, acl)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise
    return True
