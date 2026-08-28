#!/usr/bin/env python3
import os, signal, sys
# Behave like a normal unix tool when piped into head/less.
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daver.cli import main
try:
    sys.exit(main())
except BrokenPipeError:
    os._exit(0)
except KeyboardInterrupt:
    os._exit(130)
