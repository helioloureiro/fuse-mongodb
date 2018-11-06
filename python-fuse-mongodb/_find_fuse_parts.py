import sys, os, glob
from os.path import realpath, dirname, join
from traceback import format_exception

PYTHON_MAJOR_MINOR = "%s.%s" % (sys.version_info[0], sys.version_info[1])
PYTHONFUSEDIR = "/home/ehellou/DEVEL/python-fuse/build/lib.linux-x86_64-3.5"

if sys.version_info[0] != 3:
    raise RuntimeError("Use python3.  Your current python version is: %s" % PYTHON_MAJOR_MINOR)

ddd = realpath(join(dirname(sys.argv[0]), '..'))

for d in [ddd, '.']:
    for p in glob.glob(join(d, 'build', 'lib.*%s' % PYTHON_MAJOR_MINOR)):
        sys.path.insert(0, p)

sys.path.insert(0, PYTHONFUSEDIR)

try:
    import fuse
except ImportError:
    print("sys.path=", sys.path)
    raise RuntimeError("""

! Got exception:
""" + "".join([ "> " + x for x in format_exception(*sys.exc_info()) ]) + """
! Have you ran `python setup.py build'?
!
! We've done our best to find the necessary components of the FUSE bindings
! even if it's not installed, we've got no clue what went wrong for you...
""")
