import logging
import os
from functools import partial

from PyQt6 import uic
from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QSizePolicy,
    QFileDialog,
    QApplication,
)

import settings
import utils
from structures.domains import Domains
from ui.config.tabs.domains.table import Table
from ui.resources import fetch_icon

logger = logging.getLogger(__name__)


class DomainsPanel(QWidget):
    """
    Nucleic Acid Config Tab.

    Signals:
        updated: Emitted when the panel is updated. Emits a function which would do the
            proper updating. No updating is actually done in this class, rather it is
            someone else's job to call that function.
    """

    updated = pyqtSignal(object)

    def __init__(self, parent, runner: "runner.Runner") -> None:
        self.runner = runner
        super().__init__(parent)
        uic.loadUi("ui/config/tabs/domains/panel.ui", self)

        # create domains editor table and append it to the bottom of the domains panel
        self.table = Table(self, self.runner.managers.nucleic_acid_profile.current)
        self.layout().addWidget(self.table)

        # set initial values
        self._setup()

        # run setup functions
        self._signals()
        self._prettify()

        # run an initial refresh
        self.table_refresh()
        self.settings_refresh()

        logger.info("Loaded domains tab of config panel.")

    def _setup(self):
        """Fill boxes and table with the current values."""
        self.subunit_count.setValue(self.runner.managers.domains.current.subunit.count)
        self.symmetry.setValue(self.runner.managers.domains.current.symmetry)
        self.total_count.setValue(self.runner.managers.domains.current.count)
        self.table.dump_domains(self.runner.managers.domains.current)

    def _signals(self):
        """Set up panel signals."""

        def update_total_domain_box():
            """Update the total domain count box."""
            self.total_count.setValue(
                self.symmetry.value() * self.subunit_count.value()
            )

        # when domain panel settings are updated call the above worker
        self.symmetry.valueChanged.connect(update_total_domain_box)
        self.subunit_count.valueChanged.connect(update_total_domain_box)

        # when helix joint buttons are clicked refresh the table
        # so that the switch values (-1, 0, 1) get updated
        self.table.helix_joint_updated.connect(
            partial(self.updated.emit, self.table_refresh)
        )

        # dump the initial domains
        self.table.dump_domains(self.runner.managers.domains.current)

        # table update event hooking
        # when the force table update button is clicked
        def updated_worker():
            self.table_refresh()
            self.settings_refresh()

        self.update_table_button.clicked.connect(
            partial(self.updated.emit, updated_worker)
        )

        def updated_table_item():
            self.settings_refresh()
            self.table_refresh()
            self.settings_refresh()

        # when the table itself is updated
        self.table.cell_widget_updated.connect(
            partial(self.updated.emit, updated_table_item)
        )

        # reset the checked button when a helix joint is updated
        # because the user has opted out
        self.table.helix_joint_updated.connect(
            lambda: self.auto_antiparallel.setChecked(False)
        )
        self.auto_antiparallel.stateChanged.connect(
            partial(self.updated.emit, self.table_refresh)
        )

        def save_domains():
            """Save domains to file."""
            filepath = QFileDialog.getSaveFileName(
                parent=self,
                caption="Domains Save File Location Chooser",
                filter="*.csv",
            )[0]
            if len(filepath) > 0:
                logger.info(
                    f"Saving domains to {filepath}.\nDomains being saved: {self.runner.managers.domains.current}"
                )
                self.runner.managers.domains.current.to_json(filepath=filepath)

        self.save_domains_button.clicked.connect(save_domains)

        def load_domains():
            """Load domains from file."""
            filepath = QFileDialog.getOpenFileName(
                parent=self,
                caption="Domains Import File Location Chooser",
                directory=f"{os.getcwd()}\\saves\\domains\\presets",
                filter="*.csv",
            )[0]
            if len(filepath) > 0:

                def loader():
                    domains = Domains.from_df(
                        filepath=filepath,
                        nucleic_acid_profile=self.runner.managers.nucleic_acid_profile.current,
                    )
                    self.runner.managers.domains.current.update(domains)
                    self._setup()
                    QApplication.processEvents()
                    self.runner.window.config.panel.update_graphs.click()

                self.updated.emit(loader)

        self.load_domains_button.clicked.connect(load_domains)

    def _prettify(self):
        """Set up styles of panel."""
        # set panel widget buttons
        self.update_table_button.setIcon(fetch_icon("checkmark-outline"))
        self.load_domains_button.setIcon(fetch_icon("download-outline"))
        self.save_domains_button.setIcon(fetch_icon("save-outline"))

        # set scaling settings for config and table
        config_size_policy = QSizePolicy()
        config_size_policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
        config_size_policy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
        self.config.setSizePolicy(config_size_policy)

    def settings_refresh(self):
        logger.info("Refreshing domains settings.")

        # set M and target M boxes
        # https://github.com/404Wolf/NATuG3/issues/4
        current_domains = self.runner.managers.domains.current
        M: int = sum([domain.theta_m_multiple for domain in current_domains.domains()])
        N: int = current_domains.count
        B: int = self.runner.managers.nucleic_acid_profile.current.B
        R: int = current_domains.symmetry
        target_M_over_R = (B * (N - 2)) / (2 * R)
        M_over_R = M / R
        self.M.setValue(M)

        # remove trailing zeros if target_M_over_R is an int
        if target_M_over_R == round(target_M_over_R):
            self.target_M_over_R.setDecimals(0)
        else:
            self.target_M_over_R.setDecimals(3)
        self.target_M_over_R.setValue(target_M_over_R)

        # remove trailing zeros if M_over_R is an int
        if M_over_R == round(M_over_R):
            self.M_over_R.setDecimals(0)
        else:
            self.M_over_R.setDecimals(3)
        self.M_over_R.setValue(M_over_R)

        # make M_over_R and target_M_over_R box green if it is the target
        if M_over_R == target_M_over_R:
            style = (
                f"QDoubleSpinBox{{"
                f"background-color: rgb{settings.colors['success']}; "
                f"color: rgb(0, 0, 0)}}"
            )
            self.M_over_R.setStyleSheet(style)
        else:
            style = None
        self.M_over_R.setStyleSheet(style)
        self.target_M_over_R.setStyleSheet(style)

    def table_refresh(self):
        """Refresh panel settings/domain table."""
        logger.info("Refreshing domains table.")

        new_domains: Domains = Domains(
            self.runner.managers.nucleic_acid_profile.current,
            self.table.fetch_domains(),
            self.runner.managers.domains.current.symmetry,
            self.auto_antiparallel.isChecked(),
        )
        # update subunit count and refs.domains.current
        # double-check with user if they want to truncate the domains/subunit count
        # (if that is what they are attempting to do)
        if (
            self.subunit_count.value()
            < self.runner.managers.domains.current.subunit.count
        ):
            # helpers.confirm will return a bool
            confirmation: bool = utils.confirm(
                self.parent(),
                "Subunit Count Reduction",
                f"The prospective subunit count ({self.subunit_count.value()}) is lower than the number of domains in "
                f"the domains table ({self.table.rowCount()}). \n\nAre you sure you want to truncate the "
                f"domains/subunit count to {self.subunit_count.value()}?",
            )
            if confirmation:
                logger.info(
                    "User confirmed that they would like the subunit count reduced."
                )
                new_domains.subunit.count = self.subunit_count.value()
                new_domains.symmetry = self.symmetry.value()
                self.update_table_button.setStyleSheet(
                    f"background-color: rgb{str(settings.colors['success'])}"
                )
                QTimer.singleShot(
                    600,
                    partial(
                        self.update_table_button.setStyleSheet,
                        "background-color: light grey",
                    ),
                )
        else:
            new_domains.subunit.count = self.subunit_count.value()
            new_domains.symmetry = self.symmetry.value()

        # update current domains
        self.runner.managers.domains.current.update(new_domains)

        # refresh table
        self.table.dump_domains(self.runner.managers.domains.current)
