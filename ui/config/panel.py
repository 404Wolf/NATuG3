import logging

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from constants.tabs import *
from constants.toolbar import *
from ui.config.tabs import domains, nucleic_acid, sequencing
from ui.resources import fetch_icon

logger = logging.getLogger(__name__)
dialog = None


class Panel(QWidget):
    """
    The main config panel.

    This panel is for (almost) all user inputs.

    Attributes:
        runner: NATuG's runner.
    """

    def __init__(
        self,
        parent,
        runner: "runner.Runner",
    ) -> None:
        super().__init__(parent)
        self.runner = runner
        self.auto_updating_plots = False

        # Create placeholders for tabs
        self.nucleic_acid = None
        self.domains = None

        # Load the panel
        uic.loadUi("ui/config/panel.ui", self)
        self.update_graphs.setIcon(fetch_icon("reload-outline"))

        # Set up tabs and hook signals
        self._tabs()
        self._signals()

    def _tabs(self):
        """Set up all tabs for config panel."""
        # create the tab bodies and store them as attributes
        self.nucleic_acid = nucleic_acid.NucleicAcidPanel(
            self, self.runner, self.runner.managers.nucleic_acid_profile.current
        )
        self.domains = domains.DomainsPanel(self, self.runner)
        self.sequencing = sequencing.SequencingPanel(self, self.runner)

        # set the nucleic acid tab
        self.nucleic_acid_tab.setLayout(QVBoxLayout())
        self.nucleic_acid_tab.layout().addWidget(self.nucleic_acid)

        # set the domains tab
        self.domains_tab.setLayout(QVBoxLayout())
        self.domains_tab.layout().addWidget(self.domains)

        # set the strands tab
        self.sequencing_tab.setLayout(QVBoxLayout())
        self.sequencing_tab.layout().addWidget(self.sequencing)

    def _signals(self):
        """Setup signals."""

        def tab_updated():
            """Worker for when a tab is updated and wants to call a function"""
            self.runner.managers.strands.recompute()
            if self.auto_update_side_view.isChecked():
                self.runner.window.side_view.refresh()
            if self.auto_update_top_view.isChecked():
                self.runner.window.top_view.refresh()

        self.domains.updated.connect(tab_updated)
        self.nucleic_acid.updated.connect(tab_updated)
        self.tab_area.currentChanged.connect(self._on_tab_change)

    def _on_tab_change(self, index: int):
        """
        Update the plotting mode based on the currently opened tab.

        Args:
            index (int): The index of the tab that is currently open (the tab
                that has been changed to).

        Performs the following actions:
            1) Updates the plotting mode and the enabled status of the buttons in
                the toolbar.
        """
        # First set the toolbar and current plotting mode
        if index in (
            NUCLEIC_ACID,
            DOMAINS,
        ):
            # if the plot mode was not already NEMid make it NEMid
            if self.runner.managers.misc.plot_mode != "NEMid":
                self.runner.managers.misc.plot_mode = "NEMid"
                self.runner.window.side_view.refresh()
            self.runner.managers.toolbar.actions.buttons[INFORMER].setEnabled(True)
            self.runner.managers.toolbar.actions.buttons[NICKER].setEnabled(True)
            self.runner.managers.toolbar.actions.buttons[LINKER].setEnabled(True)
            self.runner.managers.toolbar.actions.buttons[JUNCTER].setEnabled(True)
        elif index in (STRANDS,):
            # if the plot mode was not already nucleoside make it nucleoside
            if self.runner.managers.misc.plot_mode != "nucleoside":
                self.runner.managers.misc.plot_mode = "nucleoside"
                self.runner.window.side_view.refresh()
            self.runner.managers.toolbar.current = INFORMER
            self.runner.managers.toolbar.actions.buttons[INFORMER].setEnabled(True)
            self.runner.managers.toolbar.actions.buttons[NICKER].setEnabled(False)
            self.runner.managers.toolbar.actions.buttons[LINKER].setEnabled(False)
            self.runner.managers.toolbar.actions.buttons[JUNCTER].setEnabled(False)


