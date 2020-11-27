# -*- coding: utf-8 -*-


class FlixError(Exception):
    """This fastflix won't fly"""


class MissingFF(FlixError):
    """Required files not found"""


class ConfigError(FlixError):
    pass


class FastFlixError(FlixError):
    """Generic FastFlixError"""


class FastFlixInternalException(FastFlixError):
    """This should always be caught and never seen by user"""
