import logging
from functools import partial
from threading import Thread
from typing import List

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout

import ui.dialogs.informers
import ui.plotters
from constants.toolbar import *
from structures.points.point import Point
from structures.strands import Strand
from structures.strands.linkage import Linkage
from ui.dialogs.linkage_config.linkage_config import LinkageConfig
from ui.dialogs.strand_config.strand_config import StrandConfig
from ui.panels.side_view import workers

logger = logging.getLogger(__name__)


class Panel(QGroupBox):
    """
    The side view panel.

    This panel contains a SideViewPlotter with the current strands being plotted and
    contains a useful refresh() method to automatically update the plot with the most
    current strands.
    """

    def __init__(self, parent, runner: "runner.Runner") -> None:
        """
        Initialize the SideView panel.

        Args:
            parent: The strands widget in which the side view panel is contained. Can be None.
            runner: NATuG's runner.
        """
        self.runner = runner
        super().__init__(parent)

        self.setObjectName("Side View")
        self.setLayout(QVBoxLayout())
        self.setTitle("Side View of Helices")
        self.setStatusTip("A plot of the side view of all domains")

        self.plot = ui.plotters.SideViewPlotter(
            self.runner.managers.strands.current,
            self.runner.managers.domains.current,
            self.runner.managers.nucleic_acid_profile.current,
            self.runner.managers.misc.plot_types,
        )
        self.plot.points_clicked.connect(self.points_clicked)
        self.plot.strand_clicked.connect(self.strand_clicked)
        self.plot.linkage_clicked.connect(self.linkage_clicked)
        self.layout().addWidget(self.plot)

    def refresh(self) -> None:
        """
        Update the current plot.

        This will update the current plot with the most recent strands, domains, nucleic acid, and plot mode. Then
        the plot will be refreshed.
        """
        self.plot.strands = self.runner.managers.strands.current
        self.plot.nucleic_acid = self.runner.managers.nucleic_acid_profile.current
        self.plot.point_types = self.runner.managers.misc.plot_types
        self.plot.refresh()

    def linkage_clicked(self, linkage: Linkage) -> None:
        """
        Slot for when a linkage is clicked.

        Opens a linkage dialog for configuring the linkage.

        Args:
            linkage: The linkage that was clicked.
        """
        dialog = LinkageConfig(self.parent(), linkage)
        dialog.updated.connect(self.refresh)
        dialog.show()
        self.refresh()

        logger.info(f"A linkage was clicked.")

    def strand_clicked(self, strand: Strand) -> None:
        """
        Slot for when a strand is clicked.

        Creates a StrandConfig dialog for the strand that was clicked.

        Args:
            strand: The strand that was clicked.
        """
        dialog = StrandConfig(self.parent(), strand=strand)
        dialog.updated.connect(self.refresh)
        dialog.show()
        self.refresh()

        logger.info(f"Strand #{strand.strands.index(strand)} was clicked.")

    def points_clicked(self, points: List[Point]) -> None:
        """
        Slot for when a point in the plot is clicked.

        Utilizes a worker thread to handle the point click.

        Args:
            points: The points that were clicked.
        """
        strands = self.runner.managers.strands.current
        domains = self.runner.managers.domains.current
        parent = self
        refresh = self.runner.window.side_view.plot.refresh

        worker = partial(
            logger.info, "Point was clicked but no worker handled the click"
        )
        if self.runner.managers.toolbar.current == INFORMER:
            worker = partial(
                workers.informer, parent, points, strands, domains, refresh
            )
        elif self.runner.managers.toolbar.current == LINKER:
            worker = partial(workers.linker, points, strands, refresh, self.runner)
        elif self.runner.managers.toolbar.current == JUNCTER:
            worker = partial(workers.juncter, points, strands, refresh, self.runner)
        elif self.runner.managers.toolbar.current == NICKER:
            worker = partial(workers.nicker, points, strands, refresh)
        elif self.runner.managers.toolbar.current == HIGHLIGHTER:
            worker = partial(workers.highlighter, points, refresh)
        thread = Thread(target=worker)
        thread.run()
