"""Portable packages always launch with system setting writes disabled."""
import os


def main():
    os.environ['ANVIL_MONITOR_ONLY'] = '1'
    from .app import main as run
    return run()
