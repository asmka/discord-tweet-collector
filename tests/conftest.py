import pytest


def pytest_addoption(parser):
    parser.addoption("--conf", action="store", help="Config file to run test")
