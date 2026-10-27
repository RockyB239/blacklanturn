"""Nonblocking OS-owned update lock. Process death releases either backend."""
import os
try:import fcntl
except ImportError:fcntl=None
try:import msvcrt
except ImportError:msvcrt=None

def acquire(descriptor):
    if fcntl is not None:
        fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
    elif msvcrt is not None:
        if os.fstat(descriptor).st_size==0:os.write(descriptor,b'\0');os.fsync(descriptor)
        os.lseek(descriptor,0,os.SEEK_SET);msvcrt.locking(descriptor,msvcrt.LK_NBLCK,1)
    else:raise OSError('This platform has no supported update-lock backend')

def unlock(descriptor):
    if fcntl is not None:fcntl.flock(descriptor,fcntl.LOCK_UN)
    elif msvcrt is not None:
        os.lseek(descriptor,0,os.SEEK_SET);msvcrt.locking(descriptor,msvcrt.LK_UNLCK,1)
