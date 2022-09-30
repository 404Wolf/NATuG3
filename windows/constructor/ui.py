from types import SimpleNamespace
from PyQt6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QDockWidget,
    QMenuBar,
    QVBoxLayout,
    QGroupBox,
    QWidget,
)
from PyQt6.QtCore import Qt
import references
import config.panel
import top_view.ui, side_view.ui


def unrestrict_scale_upon_float(
    widget: QWidget,
    initial_width: int = 9999,
    unbounded_width: int = 9999,
    initial_height: int = 9999,
    unbounded_height: int = 9999,
):
    """
    Enable scaling beyond a dockable widget's normal maximum when it begins floating.

    Args:
        widget (QWidget): Widget to change size limitations upon floating/not floating of.
        initial_width (int): Maximum widget width when not floating (in pixels).
        unbounded_width (int): Maximum widget width when floating (in pixels).
        initial_height (i)nt: Maximum widget height when not floating (in pixels).
        unbounded_height (int): Maximum widget height when floating (in pixels).
    """
    if widget.isFloating():
        widget.setMaximumWidth(unbounded_width)
        widget.setMaximumHeight(unbounded_height)
    else:
        widget.setMaximumWidth(initial_width)
        widget.setMaximumHeight(initial_height)


class window(QMainWindow):
    """
    The application's main window.

    Attributes:
        docked_widgets (SimpleNamespace): All docked widgets.
        status_bar (QStatusBar): The status bar.
        menu_bar (QMenuBar): The menu bar.
        top_view (QWidget): Top view widget.
        side_view (QWidget): Side view widget.
    """

    def __init__(self):
        # this is an inherented class of QMainWindow
        # so we must initialize the parent qt widget
        super().__init__()

        # store a reference to self in references for cross module use
        references.windows.constructor = self

        # utilize inhereted methods to set up the main window
        self.setWindowTitle("DNA Constructor")

        # initilize status bar
        self._status_bar()

        # initilize menu bar
        self._menu_bar()

        # container to store references to all docked widgets
        self.docked_widgets = SimpleNamespace()

        # add all widgets
        self._config()
        self.load_graphs()

    def _config(self):
        try:  # not first run
            side_view.load()
        except AttributeError:  # first run
            # create a dockable config widget
            self.docked_widgets.config = QDockWidget()
            self.docked_widgets.config.setWindowTitle("Config")
            self.docked_widgets.config.setStatusTip("Settings panel")

            # store the actual link to the widget in self.config
            self.config = config.panel()
            self.docked_widgets.config.setWidget(self.config)

            # set width of config widget while docked to 200px
            self.docked_widgets.config.setMinimumWidth(230)
            self.docked_widgets.config.setMaximumWidth(230)
            # when this widget floats allow it to scale up to 400px wide
            self.docked_widgets.config.topLevelChanged.connect(
                lambda: unrestrict_scale_upon_float(
                    self.docked_widgets.config, initial_width=215, unbounded_width=460
                )
            )
            self.docked_widgets.config.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QDockWidget.DockWidgetFeature.DockWidgetMovable
            )
            # dock the new docakble config widget
            self.addDockWidget(Qt.DockWidgetArea(0x2), self.docked_widgets.config)

    def load_graphs(self):

        self._top_view()
        self._side_view()

    def _top_view(self):
        """Attach top view to main window/replace current top view widget"""
        try:  # not first run
            self.top_view.load()
        except AttributeError:  # first run
            # create dockable widget for top view
            self.docked_widgets.top_view = QDockWidget()
            self.docked_widgets.top_view.setWindowTitle("Top View of Helicies")
            self.docked_widgets.top_view.setStatusTip(
                "A plot of the top view of all domains"
            )

            # store widget in class for easier direct access
            self.top_view = top_view.ui.plot()

            # attach actaul top view widget to docked top view widget
            self.docked_widgets.top_view.setWidget(self.top_view)

            # limit max width of top view widget while docked to 340px
            self.docked_widgets.top_view.setMaximumWidth(340)

            # when this widget floats remove width scaling limitation
            self.docked_widgets.top_view.topLevelChanged.connect(
                lambda: unrestrict_scale_upon_float(
                    self.docked_widgets.top_view, initial_width=340
                )
            )
            self.docked_widgets.top_view.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetFloatable
                | QDockWidget.DockWidgetFeature.DockWidgetMovable
            )

            # dock the new dockable top view widget
            self.addDockWidget(Qt.DockWidgetArea(0x1), self.docked_widgets.top_view)

    def _side_view(self):
        """Attach side view to main window/replace current side view widget"""
        # convert from QWidget to QGroupBox for pretty label and frame
        docked_side_view = self.docked_widgets.side_view = QGroupBox()
        docked_side_view.setLayout(QVBoxLayout())
        docked_side_view.setTitle("Side View of Helicies")
        docked_side_view.setStatusTip("A plot of the side view of all domains")

        # store widget in class for easier future direct widget access
        self.side_view = side_view.ui.plot()
        docked_side_view.layout().addWidget(self.side_view)

        # ensure this widget is always large enough to be useful (300px)
        docked_side_view.setMinimumWidth(300)
        self.setCentralWidget(docked_side_view)

    def _status_bar(self):
        """Create and add status bar."""
        status_bar = self.status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self.statusBar().setStyleSheet("background-color: rgb(210, 210, 210)")

    def _menu_bar(self):
        """Create a menu bar for the main window"""
        # create menu bar
        self.menu_bar = QMenuBar()

        # import all menu bars
        import windows.constructor.menus as menus

        # add all the menus to the filemenu
        self.menu_bar.addMenu(menus.file())
        self.menu_bar.addMenu(menus.view())
        self.menu_bar.addMenu(menus.help())

        # place the menu bar object into the actual menu bar
        self.setMenuBar(self.menu_bar)
