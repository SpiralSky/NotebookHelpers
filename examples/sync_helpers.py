"""Editable helper for dev_sync.ipynb; experiment in a disposable copy."""
import math


def double(value):
    return math.floor(value) * 2


def untouched():
    return "Unselected definitions stay in the file."
