#!/usr/bin/env python
from usingversion import getattr_with_version

__getattr__ = getattr_with_version("mypackage", __file__, __name__)
__name_display__ = __package__ or __name__
