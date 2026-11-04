"""Entry point of the single-file build: the same commands as ``riskid`` (see ``riskid.spec``)."""

import sys

from riskid.cli import main

sys.exit(main())
