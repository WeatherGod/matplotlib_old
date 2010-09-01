"""
The remap module provides a mechanism to alter the behavior of colormaps
without modifying the underlying Colormap object. Contained in this module
are several useful colormap ReMappers that can be combined to achieve
a desired effect.
"""


import numpy as np
from matplotlib.colors import Colormap
import matplotlib.cm as cm
from cbook import ThinWrap


class ReMap(ThinWrap) :
    """
    Base class for classes that modify the replies from calls to
    a normal colormap. These calls modify the rgba values returned
    by a call to a Colormap.
    """
    def __init__(self, cmap=None) :
        """
        Create a new ReMap wrapper around the colormap.

        cmap can be a string indicating a registered
        colormap, or a colormap object, or None to obtain
        the default colormap.
        """
        cmap = cm.get_cmap(cmap)
        ThinWrap.__init__(self, cmap)

    def __call__(self, *args, **kwargs) :
        """
        Generic overload of the __call__ method.
        This method will modify the returned rgba values using
        the _remap method defined by subclasses of ThinWrap.
        """
        return self._remap(self.__dict__['_origobj'](*args, **kwargs))

    def _remap(self, rgba) :
        raise NotImplemented("The base ReMap class does not define _remap()")




class ToGrayscale(ReMap) :
    """
    A ReMapper that will convert any color from a colormap
    into a gray color according to the ITU-R 601-2 luma transform.
    """
    def _remap(self, rgba) :
        if rgba is not None :
            rgba = np.atleast_2d(rgba)
            l = np.sum(rgba[:, :3] * np.array([0.299, 0.587, 0.114]), axis=1)
            return np.squeeze(np.dstack([l, l, l, rgba[:, 3]]))
        else :
            # If we get a None, then return it in kind.
            return None


