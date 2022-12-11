import logging
from contextlib import suppress
from dataclasses import dataclass, field
from math import ceil
from typing import List, Tuple, Dict, Literal

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPen,
)

import settings
from constants.directions import *
from structures.points import NEMid, Nucleoside
from structures.points.point import Point
from structures.profiles import NucleicAcidProfile
from structures.strands import Strands
from structures.strands.strand import Strand
from ui.plotters import utils
from ui.plotters.utils import custom_symbol, chaikins_corner_cutting

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PlotData:
    """
    Currently plotted data.

    Attributes:
        strands: The currently plotted sequencing.
        mode: The plotting toolbar. Either 'nucleoside' or 'NEMid'.
        points: A mapping of positions of plotted_points to point objects.
        plotted_points: The points.
        plotted_labels: All plotted text labels.
        plotted_strokes: The strand pen line.
        plotted_gridlines: All the grid lines.
    """

    strands: Strands = None
    mode: Literal["nucleoside", "NEMid"] = "NEMid"
    points: Dict[Tuple[float, float], Point] = field(default_factory=dict)
    plotted_points: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_labels: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_strokes: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_gridlines: List[pg.PlotDataItem] = field(default_factory=list)


class SideViewPlotter(pg.PlotWidget):
    """
    Side view sequencing plot widget.

    Attributes:
        strands: The sequencing to plot.
        nucleic_acid_profile: The nucleic acid nucleic_acid_profile of the sequencing to plot.
        plot_data: Currently plotted data.
        width: The width of the plot.
        height: The height of the plot.
        mode: The plotting toolbar. Either "nucleoside" or "NEMid".

    Signals:
        points_clicked(tuple of all points clicked): When plotted points are clicked.
        strand_clicked(the strand that was clicked): When a strand is clicked.
    """

    points_clicked = pyqtSignal(tuple, arguments=("Clicked Point NEMids",))
    strand_clicked = pyqtSignal(Strand, arguments=("Clicked Strand",))

    def __init__(
        self,
        strands: Strands,
        nucleic_acid_profile: NucleicAcidProfile,
        mode: Literal["nucleoside", "NEMid"],
    ) -> None:
        """
        Initialize plotter instance.

        Args:
            strands: The sequencing to plot.
            nucleic_acid_profile: The nucleic acid nucleic_acid_profile of the sequencing to plot.
            mode: toolbar: The plotting toolbar. Either "nucleoside" or "NEMid".
        """
        super().__init__()

        # store config data
        self.strands = strands
        self.nucleic_acid_profile = nucleic_acid_profile
        self.mode = mode
        self.plot_data = PlotData()

        # plot initial data
        self.disableAutoRange()
        self._plot()
        self.autoRange()
        self.setXRange(0, self.width)
        self._prettify()

        # set up styling
        self.setWindowTitle("Side View of DNA")  # set the window's title

    @property
    def height(self):
        return self.strands.size[1]

    @property
    def width(self):
        return self.strands.size[0]

    def refresh(self):
        """Replot plot data."""

        def runner():
            self._reset()
            self._plot()

        # allow one screen refresh for the mouse to release
        # so that the plot is cleared after the mouse release event happens
        QTimer.singleShot(0, runner)
        logger.info("Refreshed side view.")

    def _reset(self, plot_data=None):
        """Clear plot_data from plot. Plot_data defaults to self.plot_data."""
        if plot_data is None:
            plot_data = self.plot_data
        for stroke in plot_data.plotted_strokes:
            self.removeItem(stroke)
        for points in plot_data.plotted_points:
            self.removeItem(points)
        for labels in plot_data.plotted_labels:
            self.removeItem(labels)
        for gridline in plot_data.plotted_gridlines:
            self.removeItem(gridline)
        self.clear()

    def _points_clicked(self, event, points):
        """Called when a point on a strand is clicked."""
        position = tuple(points[0].pos())

        # use point mapping to detect the clicked points
        located = [self.plot_data.points[position]]
        # if the located item is a NEMid with a juncmate append the juncmate too
        if isinstance(located[0], NEMid) and (located[0].juncmate is not None):
            located.append(located[0].juncmate)

        self.points_clicked.emit(tuple(located))

    def _prettify(self):
        """Add plotted_gridlines and style the plot."""
        # clear preexisting plotted_gridlines
        self.plot_data.plotted_gridlines = []

        # create pen for custom grid
        grid_pen: QPen = pg.mkPen(color=settings.colors["grid_lines"], width=1.4)

        # domain index grid
        for i in range(ceil(self.strands.size[0]) + 1):
            self.plot_data.plotted_gridlines.append(self.addLine(x=i, pen=grid_pen))

        # for i in <number of helical twists of the tallest domain>...
        with suppress(ZeroDivisionError):
            for i in range(0, ceil(self.height / self.nucleic_acid_profile.H) + 1):
                self.plot_data.plotted_gridlines.append(
                    self.addLine(y=(i * self.nucleic_acid_profile.H), pen=grid_pen)
                )

        # add axis labels
        self.setLabel("bottom", text="x", units="nanometers", unitPrefix="nm")
        self.setLabel("left", text="z", units="nanometers", unitPrefix="nm")

    def _plot(self):
        self.plot_data.strands = self.strands
        self.plot_data.mode = self.mode
        self.plot_data.points.clear()
        self.plot_data.plotted_labels.clear()
        self.plot_data.plotted_points.clear()
        self.plot_data.plotted_strokes.clear()

        for strand_index, strand in enumerate(self.plot_data.strands.strands):
            # create containers for plotting data
            symbols: List[str] = list()
            symbol_sizes: List[int] = list()
            symbol_brushes = list()
            symbol_pens = list()
            x_coords: List[float] = list()
            z_coords: List[float] = list()

            # create various brushes
            point_brush = pg.mkBrush(color=utils.dim_color(strand.color, 0.9))
            bright_brush = pg.mkBrush(color=utils.brighten_color(strand.color, 0.2))
            dim_brush = pg.mkBrush(color=utils.dim_color(strand.color, 0.1))
            highlight_brush = pg.mkBrush(color=settings.colors["highlighted"])

            # create various pens
            black_pen = pg.mkPen(
                color=([0] * 3),
                width=0.5,
            )
            strand_pen = pg.mkPen(color=strand.color, width=strand.thickness)

            # if the strand color is dark
            if sum(strand.color) < (255 * 3) / 2:
                # a light symbol pen
                point_pen = pg.mkPen(
                    color=[200] * 3,
                    width=0.65,
                )
            else:
                # otherwise create a dark one
                point_pen = pg.mkPen(
                    color=[0] * 3,
                    width=0.5,
                )

            # iterate on the proper type based on toolbar
            if self.plot_data.mode == "NEMid":
                to_plot = strand.NEMids()
            elif self.plot_data.mode == "nucleoside":
                to_plot = strand.nucleosides()

            # now create the proper plot data for each point one by one
            for point_index, point in enumerate(to_plot):
                # update the point mappings (this is a dict that allows us to easily traverse between
                # a coord and a Point)
                self.plot_data.points[
                    (
                        point.x_coord,
                        point.z_coord,
                    )
                ] = point

                # assign the coords of the point
                x_coords.append(point.x_coord)
                z_coords.append(point.z_coord)

                # determine the symbol for the point
                if isinstance(point, Nucleoside) and point.base is not None:
                    # if the point is a nucleoside and the nucleoside has a base assigned to it
                    # then make the symbol that base, rotated based on the direction of the nucleoside
                    if point.direction is UP:
                        symbols.append(
                            custom_symbol(point.base, flip=False, rotation=-90)
                        )
                    else:
                        symbols.append(
                            custom_symbol(point.base, flip=False, rotation=90)
                        )
                else:
                    # otherwise we will make the point symbol a simple arrow indicating its direction
                    if point.direction == UP:
                        symbols.append("t1")  # up arrow for an upwards point
                    else:  # point.direction == DOWN
                        symbols.append("t")  # down arrow for a downwards point

                # if the Point is highlighted then make it larger and yellow
                if point.highlighted:
                    symbol_brushes.append(highlight_brush)
                    symbol_pens.append(point_pen)
                    symbol_size = 18
                # if it isn't highlighted then determine the properties of it based off of the type of the point
                else:
                    if isinstance(point, Nucleoside):
                        if point.base is None:
                            # baseless nucleosides are normally colored
                            symbol_brushes.append(point_brush)
                            symbol_pens.append(point_pen)
                            symbol_size = 7
                        else:
                            # based nucleosides are dimly colored
                            symbol_brushes.append(dim_brush)
                            symbol_pens.append(black_pen)
                            symbol_size = 9
                    if isinstance(point, NEMid):
                        if point.junctable:
                            # junctable NEMids are dimmly colored
                            symbol_brushes.append(bright_brush)
                            symbol_pens.append(point_pen)
                            symbol_size = 6
                        else:
                            # non-junctable NEMids are normally colored
                            symbol_brushes.append(point_brush)
                            symbol_pens.append(point_pen)
                            symbol_size = 6
                    else:
                        raise TypeError("Point is not a Nucleoside or NEMid.")

                # if the strand is highlighted boost the size of the symbol brush
                if strand.highlighted:
                    symbol_size += 5
                symbol_sizes.append(symbol_size)

            # graph the points separately
            plotted_points = pg.PlotDataItem(
                x_coords,
                z_coords,
                symbol=symbols,  # type of symbol (in this case up/down arrow)
                symbolSize=symbol_sizes,  # size of arrows in px
                pxMode=True,  # means that symbol size is in px and non-dynamic
                symbolBrush=symbol_brushes,  # set color of points to current color
                symbolPen=symbol_pens,  # for the outlines of points
                pen=None,
            )
            plotted_points.sigPointsClicked.connect(self._points_clicked)
            self.plot_data.plotted_points.append(plotted_points)

            # if this strand contains a junction then
            # round the corners of the outline for aesthetics
            if strand.interdomain:
                coords = zip(x_coords, z_coords)
                coords = chaikins_corner_cutting(coords, offset=0.4, refinements=1)
                coords = list(chaikins_corner_cutting(coords, refinements=1))

                connect = []
                # in case the junction is a left-to-right side of screen junction
                # do not plot the entire connector line going from the left to the
                # right of the screen
                for point_index, (x_coord, z_coord) in enumerate(coords.copy()):
                    # if the distance between this x coord and the next one is large then add a break in the connector.
                    # Note that the "next x coord" to check against is typically the next on in the array, except
                    # when we reach the end of the list, in which case it becomes the first one.
                    if point_index != len(coords) - 1:
                        next_x_coord = coords[point_index + 1][0]
                    else:
                        next_x_coord = coords[0][0]

                    # if the distance between this x coord and the next one is large then don't add a connection.
                    # otherwise add a connection.
                    if abs(x_coord - next_x_coord) > 1:
                        # do not connect
                        connect.append(0)
                    else:
                        # connect
                        connect.append(1)

                # closed strands will have one extra item in the end so that they appear connected
                if strand.closed:
                    connect.append(1)

                connect = np.array(connect)
                x_coords = [coord[0] for coord in coords]
                z_coords = [coord[1] for coord in coords]
            else:
                connect = "all"

            # plot the outline separately
            if strand.closed:
                x_coords.append(x_coords[0])
                z_coords.append(z_coords[0])
            stroke = pg.PlotDataItem(
                x_coords, z_coords, pen=strand_pen, connect=connect
            )
            stroke.setCurveClickable(True)
            stroke.sigClicked.connect(
                lambda plot_data_item, mouse_event, to_emit=strand: self.strand_clicked.emit(
                    to_emit
                )
            )
            self.plot_data.plotted_strokes.append(stroke)

        for stroke, points in zip(
            self.plot_data.plotted_strokes, self.plot_data.plotted_points
        ):
            self.addItem(stroke)
            self.addItem(points)

        for label in self.plot_data.plotted_labels:
            self.addItem(label)

        self._prettify()
