from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import configuration.nucleic_acid, configuration.domains, configuration.main
import logging
import computers.side_view.worker
from contextlib import suppress
from constants.directions import *


logger = logging.getLogger(__name__)


class Plot(QWidget):
    """A widget that fetches current settings and generates helices side view."""

    def __init__(self):
        super().__init__()

        self.graph = None
        self.count = None
        self.worker = None
        self.domains = None
        self.settings = None

        # set layout of widget
        self.setLayout(QVBoxLayout())

        # initialize the widget
        self.load()

    def load(self):
        """
        Fetch settings data and actually plot the top view graph.
        Automatically replaces existing plot if this has already been called.
        """

        # attempt to remove existing widget if it is already generated
        # (so that we don't end up with two widgets)
        with suppress(AttributeError):
            self.layout().removeWidget(self.graph)

        # fetch nucleic acid settings and the current domains
        self.settings = configuration.nucleic_acid.storage.current
        self.domains = configuration.domains.storage.current
        self.count = configuration.main.count

        # create instance of dna_nanotube_tools side view generation
        self.worker = computers.side_view.worker.Plot(
            self.domains,
            self.settings.Z_b,
            self.settings.Z_s,
            self.settings.theta_s,
            self.settings.theta_b,
            self.settings.theta_c,
        )
        logger.debug(self.worker)

        self.graph: pg.GraphicsLayoutWidget = (
            pg.GraphicsLayoutWidget()
        )  # create main computers window
        self.graph.setWindowTitle("Side View of DNA")  # set the window's title
        self.graph.setBackground("w")  # make the background white
        main_plot: pg.plot = self.graph.addPlot()

        # we can calculate the range at the end of generation; we don't need to continuously recalculate the range
        main_plot.disableAutoRange()

        # generate the coords
        points = self.worker.compute()

        for index, domain in enumerate(self.domains):
            if index % 2:  # if the domain index is an even integer
                colors: tuple = ((255, 0, 0), (0, 255, 0))  # use red and green colors
            else:  # but if it is an odd integer
                colors: tuple = (
                    (0, 0, 255),
                    (255, 255, 0),
                )  # use blue and yellow colors
            # this way it will be easy to discern between different domains
            # (every other domain will be a different color scheme)

            for strand_direction in (UP, DOWN):
                if strand_direction == UP:  # 0 means up strand
                    symbol: str = "t1"  # up arrow for up strand
                    color: str = colors[
                        0
                    ]  # set the color to be the second option of current color scheme (which is "colors")
                elif strand_direction == DOWN:  # 1 means down strand
                    symbol: str = "t"  # down arrow for down strand
                    color: str = colors[
                        1
                    ]  # set the color to be the first option of current color scheme (which is "colors")

                # domain#i-up or domain#i-down
                title = f"domain#{index}-{str(strand_direction).replace('0','up').replace('1','down')}"

                # obtain an array of x and z coords from the points container
                x_coords = self.worker.x_coords[index][strand_direction]
                z_coords = self.worker.z_coords[index][strand_direction]

                main_plot.plot(  # actually plot the current strand of the current domain
                    x_coords,
                    z_coords,
                    title=title,  # name of what was just plotted
                    symbol=symbol,  # type of symbol (in this case up/down arrow)
                    symbolSize=6,  # size of arrows in px
                    pxMode=True,  # means that symbol size is in px
                    symbolPen=pg.mkPen(
                        color=color
                    ),  # set color of points to current color
                    pen=pg.mkPen(
                        color=(120, 120, 120), width=1.8
                    ),  # set color of pen to current color (but darker)
                )

        main_plot.autoRange()  # reenable autorange so that it isn't zoomed out weirdly
        main_plot.setXRange(0, len(self.domains))

        # add the plot widget to the layout
        self.layout().addWidget(self.graph)
