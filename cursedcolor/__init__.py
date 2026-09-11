import sys

_libs_path = r"C:\KritaPluginLibs"
if _libs_path not in sys.path:
    sys.path.insert(0, _libs_path)

from .cursedcolor_docker import CursedColorDocker
from krita import DockWidgetFactory, DockWidgetFactoryBase

Krita.instance().addDockWidgetFactory(
    DockWidgetFactory("cursedColorDocker",
                       DockWidgetFactoryBase.DockRight,
                       CursedColorDocker)
)
