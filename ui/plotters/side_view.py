import logging
from contextlib import suppress
from dataclasses import dataclass, field
from math import ceil
from typing import List, Tuple, Dict, Type

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.QtGui import QPen, QBrush, QPainterPath, QFont

import settings
from structures.points import NEMid, Nucleoside
from structures.points.point import Point, PointStyles
from structures.profiles import NucleicAcidProfile
from ui.plotters.plotter import Plotter
from ui.plotters.utils import custom_symbol, chaikins_corner_cutting

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PlotModifiers:
    """
    Various modifiers for the scale of various plot aspects.

    Attributes:
        nick_mod: The multiplier for the size of nick points.
        nucleoside_mod: The multiplier for the size of nucleoside points.
        NEMid_mod: The multiplier for the size of NEMid points.
        point_outline_mod: The multiplier for the width of point outlines, with the
            exception of junctable NEMids.
        stroke_mod: The multiplier for the width of strand strokes.
        gridline_mod: The multiplier for the width of grid lines.
    """

    nick_mod: float = 1.0
    nucleoside_mod: float = 1.0
    NEMid_mod: float = 1.0
    point_outline_mod: float = 1.0
    stroke_mod: float = 1.0
    gridline_mod: float = 1.0


@dataclass(slots=True)
class PlotData:
    """
    Currently plotted data.

    Attributes:
        strands: The currently plotted strands.
        domains: The currently plotted domains.
        point_types: The currently plotted point types.
        modifiers: Various modifiers for the scale of various plot aspects.
        points: A mapping of positions of plotted_points to point objects.
        plotted_points: The points.
        plotted_nicks: The nicks.
        plotted_linkages: The linkages.
        plotted_labels: All plotted text labels.
        plotted_strokes: The strand pen line.
        plotted_gridlines: All the grid lines.
    """

    strands: "Strands" = None
    domains: "Domains" = None
    point_types: Tuple[Type, ...] = field(default_factory=tuple)
    modifiers: PlotModifiers = field(default_factory=PlotModifiers)
    points: Dict[Tuple[float, float], "Point"] = field(default_factory=dict)
    plotted_points: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_nicks: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_linkages: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_labels: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_strokes: List[pg.PlotDataItem] = field(default_factory=list)
    plotted_gridlines: List[pg.PlotDataItem] = field(default_factory=list)


class SideViewPlotter(Plotter):
    """
    Side view strands plot widget.

    Attributes:
        strands: The strands to plot.
        domains: The domains to use for plotting computations, such as determining
            the width of the plot.
        nucleic_acid_profile: The nucleic acid nucleic_acid_profile of the
            strands to plot.
        plot_data: Currently plotted data.
        point_types: The types of points to plot. Options are Nucleoside and
            NEMid. If Point is passed, both Nucleoside and NEMid will be plotted.
        modifiers: Various modifiers for the scale of various plot aspects.
        title: The title of the plot.

    Signals:
        points_clicked(tuple of all points clicked): When plotted points are clicked.
        strand_clicked(the strand that was clicked): When a strand is clicked.
    """

    points_clicked = pyqtSignal(object, arguments=("Clicked Point NEMids",))
    strand_clicked = pyqtSignal(object, arguments=("Clicked Strand",))
    linkage_clicked = pyqtSignal(object, arguments=("Clicked Linkages",))

    def __init__(
        self,
        strands: "Strands",
        domains: "Domains",
        nucleic_acid_profile: NucleicAcidProfile,
        point_types: Tuple[Type, ...] = (Point,),
        modifiers: PlotModifiers = PlotModifiers(),
        title: str = "",
        padding: float = 0.025,
        dot_hidden_points: bool = True,
        initial_plot: bool = True,
    ) -> None:
        """
        Initialize plotter instance.

        Args:
            strands: The strands to plot.
            nucleic_acid_profile: The nucleic acid nucleic_acid_profile of the
                strands to plot.
            point_types: The types of points to plot. Options are Nucleoside and
                NEMid. If Point is passed, both Nucleoside and NEMid will be plotted.
            modifiers: Various modifiers for the scale of various plot aspects.
            title: The title of the plot. Defaults to "".
            padding: The padding to add to the plot when auto-ranging. Defaults to 0.01.
            dot_hidden_points: Whether to show points that are not being plotted as
                small circles. Defaults to True.
            initial_plot: Whether to plot the initial data. Defaults to True.
        """
        super().__init__()
        self.getViewBox().disableAutoRange()

        # store config data
        self.strands = strands
        self.domains = domains
        self.nucleic_acid_profile = nucleic_acid_profile
        self.point_types = point_types
        self.modifiers = modifiers
        self.title = title
        self.dot_hidden_points = dot_hidden_points
        self.padding = padding
        self.plot_data = PlotData()

        # internal variables
        self._set_dimensions()
        self._updating_viewbox = False

        if initial_plot:
            self.plot()
            self._set_range()

        def enableAutoRange(*args, **kwargs):
            if not self._updating_viewbox:
                self._updating_viewbox = True
                self._set_range()
                self._updating_viewbox = False

        self.getViewBox().enableAutoRange = enableAutoRange

    @property
    def height(self):
        return self._height

    @property
    def width(self):
        return self._width

    def _set_dimensions(self):
        self._width = self.domains.count
        self._height = self.strands.size[1]

    def refresh(self):
        """Replot plot data."""

        def runner():
            self._reset()
            self.plot()

        # allow one screen refresh for the mouse to release
        # so that the plot is cleared after the mouse release event happens
        QTimer.singleShot(0, runner)
        logger.info("Refreshed side view.")

    def replot(self):
        """Replot plot data."""
        self._reset()
        self.plot()

    def _reset(self, plot_data=None):
        """Clear plot_data from plot. Plot_data defaults to self.plot_data."""
        if plot_data is None:
            plot_data = self.plot_data
        for stroke in plot_data.plotted_strokes:
            self.removeItem(stroke)
        for points in plot_data.plotted_points:
            self.removeItem(points)
        for nick in plot_data.plotted_nicks:
            self.removeItem(nick)
        for linkage in plot_data.plotted_linkages:
            self.removeItem(linkage)
        for labels in plot_data.plotted_labels:
            self.removeItem(labels)
        for gridline in plot_data.plotted_gridlines:
            self.removeItem(gridline)
        self.clear()

    def _points_clicked(self, event, points):
        """Called when a point on a strand is clicked."""
        position = tuple(points[0].pos())
        self.points_clicked.emit(self.plot_data.points[position])

    def _set_range(self):
        """Configure the range for the plot automatically."""
        self.getViewBox().setXRange(0, self.width, self.padding)
        self.getViewBox().setYRange(0, self.height, self.padding)

    def _prettify(self):
        """Add plotted_gridlines and style the plot."""
        self.setTitle(self.title) if self.title else None

        # Clear preexisting plotted_gridlines
        self.plot_data.plotted_gridlines.clear()

        # Create pen for custom grid
        grid_pen_width = 1.4 * self.modifiers.gridline_mod
        grid_pen: QPen = pg.mkPen(
            color=settings.colors["grid_lines"], width=grid_pen_width
        )

        # For each domain add a grid line
        for i in range(ceil(self.plot_data.strands.size[0]) + 1):
            self.plot_data.plotted_gridlines.append(
                self.addLine(
                    x=i,
                    pen=grid_pen,
                )
            )
            self.plot_data.plotted_gridlines[-1].setZValue(-10)

        # For i in <number of helical twists of the tallest domain> add grid lines.
        with suppress(ZeroDivisionError):
            for i in range(0, ceil(self.height / self.nucleic_acid_profile.H)):
                self.plot_data.plotted_gridlines.append(
                    self.addLine(
                        y=(i * self.nucleic_acid_profile.H),
                        pen=grid_pen,
                    )
                )
                self.plot_data.plotted_gridlines[-1].setZValue(-10)

        # Add axis labels
        self.setLabel("bottom", text="x", units="Helical Diameters")
        self.setLabel("left", text="z", units="Nanometers")

    def plot(self):
        """
        Plot the side view.

        All plotted data gets saved in the current plot_data.

        Raises:
            ValueError: If the mode is not of type "nucleoside" or "NEMid".
        """
        from structures.strands.linkage import Linkage

        self.plot_data.strands = self.strands
        self.plot_data.domains = self.domains
        self.plot_data.point_types = self.point_types
        self.plot_data.modifiers = self.modifiers
        self.plot_data.points.clear()
        self.plot_data.plotted_labels.clear()
        self.plot_data.plotted_points.clear()
        self.plot_data.plotted_nicks.clear()
        self.plot_data.plotted_linkages.clear()
        self.plot_data.plotted_strokes.clear()

        for strand_index, strand in enumerate(self.strands.strands):
            # First plot all the points
            to_plot = strand.items.by_type(Point)

            # create containers for plotting data
            symbols = np.empty(len(to_plot), dtype=object)
            symbol_sizes = np.empty(len(to_plot), dtype=int)
            symbol_brushes = np.empty(len(to_plot), dtype=QBrush)
            symbol_pens = np.empty(len(to_plot), dtype=QPen)
            x_coords = np.empty(len(to_plot), dtype=float)
            z_coords = np.empty(len(to_plot), dtype=float)

            # Now create the proper plot data for each point one by one
            for point_index, point in enumerate(to_plot):
                # For points that are overlapping on the integrer line, they will be
                # plotted slightly differently.
                if point.x_coord % 1 == 0:
                    # If the point is on the right side of its domain (i.e. the
                    # point's domain x coord = index + 1) then we will shift it
                    # slightly to the left so that it is not obscured by the other
                    # point that is on top of it. Otherwise, we will shift it
                    # slightly to the right.
                    if (
                        # Points that are on the very left (x=0) or the very right (
                        # x=the number of domains) will not be shifted.
                        point.x_coord == 0
                        or point.x_coord == self.domains.count
                    ):
                        x_coord = point.x_coord
                    else:
                        if point.domain.index == point.x_coord:
                            x_coord = point.x_coord + 0.04
                        else:
                            x_coord = point.x_coord - 0.04
                else:
                    x_coord = point.x_coord
                z_coord = point.z_coord

                x_coords[point_index] = x_coord
                z_coords[point_index] = z_coord

                # Update the point mappings. This is a dict that allows us to map the
                # location of a given point to the point object itself.
                self.plot_data.points[(x_coord, z_coord)] = point

                # If the point type is NOT the same as the active point type, use the
                # current styles of the point. Otherwise, plot a smaller "o" shaped
                # point to indicate that the point is not the active point type,
                # but still exists.
                if not isinstance(point, self.point_types):
                    if self.dot_hidden_points:
                        symbols[point_index] = "o"
                        symbol_sizes[point_index] = 2
                        symbol_brushes[point_index] = pg.mkBrush(color=(30, 30, 30))
                        symbol_pens[point_index] = None
                else:
                    # if the symbol is a custom symbol, use the custom symbol
                    if point.styles.symbol_is_custom():
                        if point.styles.font is None:
                            symbols[point_index] = custom_symbol(
                                point.styles.symbol,
                                flip=False,
                                rotation=point.styles.rotation,
                            )
                        else:
                            symbols[point_index] = custom_symbol(
                                point.styles.symbol,
                                flip=False,
                                rotation=point.styles.rotation,
                                font=QFont(point.styles.font),
                            )
                        assert isinstance(symbols[point_index], QPainterPath), (
                            "Custom symbol must be of type QPainterPath, but is of type"
                            f" {type(symbols[point_index])}"
                        )
                    else:
                        assert point.styles.symbol in PointStyles.all_symbols, (
                            f'Symbol "{point.styles.symbol} "is not a valid symbol. '
                            "Valid symbols are: "
                            f"{PointStyles.all_symbols}"
                        )
                        symbols[point_index] = point.styles.symbol

                    outline_width = (
                        point.styles.outline[1] * self.modifiers.point_outline_mod
                    )
                    if isinstance(point, NEMid):
                        symbol_sizes[point_index] = (
                            point.styles.size * self.modifiers.NEMid_mod
                        )
                        if point.junctable:
                            outline_width = point.styles.outline[1]
                    elif isinstance(point, Nucleoside):
                        symbol_sizes[point_index] = (
                            point.styles.size * self.modifiers.nucleoside_mod
                        )
                    else:
                        symbol_sizes[point_index] = point.styles.size
                        outline_width = point.styles.outline[1]

                    # Create a brush for the symbol, based on the point's styles.
                    symbol_brushes[point_index] = pg.mkBrush(
                        color=point.styles.fill,
                    )

                    # Create a pen for the symbol, based on the point's styles.
                    symbol_pens[point_index] = (
                        pg.mkPen(
                            color=point.styles.outline[0],
                            width=outline_width,
                        )
                        if outline_width > 0
                        else None
                    )

            # Graph the plot for the points and for the strokes separately. First we
            # will plot the points.
            plotted_points = pg.PlotDataItem(
                x_coords,
                z_coords,
                symbol=symbols,  # type of symbol (in this case up/down arrow)
                symbolSize=symbol_sizes,  # size of arrows in px
                pxMode=True,
                symbolBrush=symbol_brushes,  # set color of points to current color
                symbolPen=symbol_pens,
                pen=None,
                skipFiniteCheck=True,
                name=f"Strand#{strand_index} Points",
            )
            # When a point is clicked, invoke the _points_clicked method.
            plotted_points.sigPointsClicked.connect(self._points_clicked)
            self.plot_data.plotted_points.append(plotted_points)

            strand_with_linkage = strand.has_linkage()

            # A strand consists of items connected by a visual stroke. However,
            # linkages receive a special stroke that has a special color, style,
            # onClick method, and more. So, right now we will split all the strand
            # items into subunits of points, discluding linkages. These subunits can
            # be plotted as connected points with a single stroke each.
            stroke_segments = strand.items.by_type(Point, Linkage).split(Linkage)
            for stroke_segment_index, stroke_segment in enumerate(stroke_segments):
                # The strand will need an extra point to give the appearance of closure
                # if the strand is closed. However, if the strand has at least one linkage
                # and is closed then the linkages should hide the gap.

                # Gather an array of all the x and z coordinates of the points in
                # the stroke segment.
                if (not strand_with_linkage) and strand.closed:
                    stroke_length = len(stroke_segment) + 1
                else:
                    stroke_length = len(stroke_segment)
                x_coords = np.zeros(stroke_length, dtype=float)
                z_coords = np.zeros(stroke_length, dtype=float)

                for point_index, point in enumerate(stroke_segment):
                    x_coords[point_index] = point.x_coord
                    z_coords[point_index] = point.z_coord

                # If the strand is closed, we will be adding a pseudo point to the
                # end of the stroke segment. If the last point and the first point
                # are near in x value, then we will connect the last point to
                # the first point (connect[-1] = True). Otherwise, we will not
                # connect the last point to the first point (connect[-1] = False).
                add_connected_pseudo_point = strand.closed and (
                    abs(stroke_segment[0].domain - stroke_segment[-1].domain)
                    == self.domains.count - 1
                )

                # If the strand is closed, a pseudo point will be added to
                # the end of the stroke segment. Whether this point gets a
                # connection depends on the "add_connected_pseudo_point"
                # variable.
                if strand.closed and not strand_with_linkage:
                    # If the strand is closed, then we need to add a pseudo
                    # point to the end of the stroke segment.
                    splitter_length = len(stroke_segment) + 1
                else:
                    # If the strand is not closed, then we don't need to add a
                    # pseudo point to the end of the stroke segment.
                    splitter_length = len(stroke_segment)

                # Create an array of booleans that indicate where to break apart
                # the coordinates into separate strokes.
                splitter = np.full(splitter_length, False, dtype=bool)

                if interdomain := strand.interdomain():
                    # If the strand is interdomain, it may also be cross-screen (
                    # that is, it breaks off on one side of the screen and
                    # continues on the other). For this reason, we will create an
                    # array of booleans that indicate where to break apart the
                    # coordinates into separate strokes. We will plot multiple
                    # stroke segments separately instead of using pyqtgraph's
                    # "connect" feature, because we will later round the edges of
                    # strokes.

                    for index, point in enumerate(stroke_segment[:-1]):
                        # We will be looking ahead to the next point to determine
                        # whether we have crossed the screen, so we will skip the last
                        # point and worry about it later.
                        if (
                            abs(point.domain - stroke_segment[index + 1].domain)
                            == self.domains.count - 1
                        ):
                            splitter[index + 1] = True
                            strand.cross_screen = True

                    # If the strand is closed then connect the last point to the
                    # first point by creating a pseudo-point at the first point's
                    # location. This will give the appearance of a closed strand.
                    if strand.closed and not strand_with_linkage:
                        splitter[-1] = add_connected_pseudo_point
                        x_coords[-1] = x_coords[0]
                        z_coords[-1] = z_coords[0]
                    else:
                        splitter[-1] = 0

                    # Find the indices of the split array that are nonzero.
                    split_indexes = np.nonzero(splitter)[0]

                    # Use the indices of the split array to split the x and z arrays
                    # into subarrays, which will be connected.
                    x_coords_subarrays = np.split(x_coords, split_indexes)
                    z_coords_subarrays = np.split(z_coords, split_indexes)

                # If we know that a strand is not interdomain (does not contain
                # points within different domains, however, we can skip this
                # check and connect all the points).
                else:
                    x_coords_subarrays = (x_coords,)
                    z_coords_subarrays = (z_coords,)

                def subarray_yielder() -> tuple[bool, np.ndarray, np.ndarray]:
                    """
                    A generator to yield the x and z coord subarrays one at a time.

                    For subarrays that begin on the very left or right side of the screen,
                    an additional subarray will be spit out that indicates that visually.
                    We use a function to yield the subarrays one by one and insert the
                    extra ones where needed because the subarrays are stored in a larger
                    fixed size array and it would be very computationally inefficient to
                    insert items into.

                    Yields:
                        tuple: Whether to smooth the array, x coord subarray, z coord
                            subarray
                    """
                    # Determine the midpoint of the entire plot, and then we will shift
                    # to the left/right of the midpoint in order to place the extra line.
                    midpoint = self.width / 2
                    delta = self.width / 2 + settings.cross_screen_line_length

                    # We will be crawling along the entire split array (which includes
                    # False boolean values for every single index of all the coords in
                    # the x and z subarrays and True boolean values in between them). The
                    # "cumulative_point_index" lets us keep track of the current index to
                    # look at of the split array as we traverse the coord subarrays.
                    cumulative_point_index = 0

                    def make_extension(location: int):
                        """
                        Obtain the actual plottable coordinate set for an
                        extension line to the left/right side of the screen.
                        """
                        if round(x_coords_subarray[location]) == 0:
                            shift_toward = -1
                        elif round(x_coords_subarray[location]) == self.width:
                            shift_toward = 1
                        else:
                            raise ValueError("Must shift either left/right.")

                        return (
                            False,
                            (
                                x_coords_subarray[location],
                                midpoint + shift_toward * delta,
                            ),
                            (
                                z_coords_subarray[location],
                                z_coords_subarray[location],
                            ),
                        )

                    for x_coords_subarray, z_coords_subarray in zip(
                        x_coords_subarrays, z_coords_subarrays
                    ):
                        if strand.cross_screen:
                            if round(x_coords_subarray[0]) in (0, self.domains.count):
                                yield make_extension(0)
                            if round(x_coords_subarray[-1]) in (0, self.domains.count):
                                yield make_extension(-1)
                        yield interdomain, x_coords_subarray, z_coords_subarray

                for smooth, x_coords_subarray, z_coords_subarray in subarray_yielder():
                    if smooth:
                        # Round the subarrays' edges using Chaikin's corner
                        # cutting algorithm.
                        rounded_coords = chaikins_corner_cutting(
                            np.column_stack((x_coords_subarray, z_coords_subarray)),
                            refinements=3,
                            offset=0.3,
                        )
                        x_coords_subarray = rounded_coords[:, 0]
                        z_coords_subarray = rounded_coords[:, 1]

                    stroke_pen = pg.mkPen(
                        color=strand.styles.color.value,
                        width=(strand.styles.thickness.value * self.modifiers.stroke_mod),
                    )

                    # Create the actual plot data item for the stroke segment.
                    plotted_stroke = pg.PlotDataItem(
                        x_coords_subarray,
                        z_coords_subarray,
                        pen=stroke_pen,
                        name=f"Strand#{strand_index} Stroke#"
                        f"{stroke_segment_index}/{len(stroke_segment)}",
                    )
                    # Make it so that the stroke itself can be clicked.
                    plotted_stroke.setCurveClickable(True)
                    # When the stroke is clicked, emit the strand_clicked
                    # signal. This will lead to the creation of a
                    # StrandConfig dialog.
                    plotted_stroke.sigClicked.connect(
                        lambda *args, f=strand: self.strand_clicked.emit(f)
                    )
                    # Store the stroke plotter object, which will be used later.
                    self.plot_data.plotted_strokes.append(plotted_stroke)

                    # Now that we've plotted the stroke, we need to plot the
                    # linkages. We will sort out all the linkages in the strand,
                    # and then plot them one by one.
                    for linkage_index, linkage in enumerate(
                        strand.items.by_type(Linkage)
                    ):
                        # Linkages have a .plot_points attribute that contains three
                        # points: the first point, the midpoint, and the last point.
                        coords = linkage.plot_points
                        # Round out the coordinates using Chaikin's Corner Cutting to
                        # give the appearance of a smooth curve.
                        coords = chaikins_corner_cutting(coords, refinements=3)
                        # Split the coordinates into x and z coordinate arrays for
                        # plotting with pyqtgraph.
                        x_coords = [coord[0] for coord in coords]
                        z_coords = [coord[1] for coord in coords]

                        # Create the plot data item for the linkage.
                        plotted_linkage = pg.PlotDataItem(
                            x_coords,
                            z_coords,
                            pen=pg.mkPen(  # Create a pen for the linkage
                                color=linkage.styles.color,
                                width=linkage.styles.thickness
                                * self.modifiers.stroke_mod,
                            ),
                            name=f"Strand#{strand_index} Linkage#{linkage_index}",
                        )
                        # Make it so that the linkage itself can be clicked.
                        plotted_linkage.setCurveClickable(True)
                        # When the linkage is clicked, emit the linkage_clicked signal.
                        # This will lead to the creation of a LinkageConfig dialog when
                        # invoked.
                        plotted_linkage.sigClicked.connect(
                            lambda *args, to_emit=linkage: self.linkage_clicked.emit(
                                to_emit
                            )
                        )
                        # Store the linkage plotter object, which will be used for
                        # actually plotting the linkage later.
                        self.plot_data.plotted_linkages.append(plotted_linkage)

        nick_brush = pg.mkBrush(color=settings.colors["nicks"])
        for nick_index, nick in enumerate(self.strands.nicks):
            plotted_nick = pg.PlotDataItem(
                (nick.x_coord,),  # Just one point: the nick's x coordinate
                (nick.z_coord,),  # Just one point: the nick's z coordinate
                # The same styles for all nicks...
                symbol="o",
                symbolSize=8 * self.modifiers.nick_mod,
                pxMode=True,  # means that symbol size doesn't change with zoom
                symbolBrush=nick_brush,
                symbolPen=None,  # No outline for the symbol
                pen=None,  # No line connecting the points
                name=f"Nick#{nick_index}",
            )
            # Store the nick plotter object, which will be used for actually
            # plotting the nick later.
            self.plot_data.plotted_nicks.append(plotted_nick)
            # Create a mapping from the nick's coordinates to the nick itself,
            # so that when it is clicked, we can find the nick object.
            self.plot_data.points[(nick.x_coord, nick.z_coord)] = nick
            # Hook up the nick's onClick method to the _points_clicked method.
            plotted_nick.sigPointsClicked.connect(self._points_clicked)

        # Items will be plotted one layer at a time, from bottom to top. The items
        # plotted last go on top, since all items before them are plotted first.
        # Thence, this list is Fin reverse order of the layers in the plot.
        layers = (
            self.plot_data.plotted_strokes,
            self.plot_data.plotted_linkages,
            self.plot_data.plotted_nicks,
            self.plot_data.plotted_points,
        )

        # Add the items to the plot
        for layer in layers:
            for item in layer:
                self.addItem(item)

        self._set_dimensions()

        # Style the plot; automatically adds labels, ticks, etc. Also sets the plot's
        # range.
        self._prettify()
