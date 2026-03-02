#!/usr/bin/env python3
"""Launch the SF2 to SLI/SLC converter."""

import sys
import os

# Ensure the package directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sf2_converter.__main__ import main

main()
