"""Compatibility entry point; use gps_transport_integration.py for the v16 workflow."""
import runpy
from pathlib import Path

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('gps_transport_integration.py')), run_name='__main__')
