import logging
from copy import copy
from functools import partial

import pandas as pd
from PyQt6 import uic
from PyQt6.QtCore import QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QWidget,
    QSizePolicy,
    QFileDialog,
)

import settings
import utils
from structures.domains import Domains
from structures.profiles import NucleicAcidProfile
from ui.config.tabs.domains.table import Table
from ui.dialogs.refresh_confirmer.refresh_confirmer import RefreshConfirmer
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

    updated = pyqtSignal()

    def __init__(self, parent, runner: "runner.Runner") -> None:
        self.runner = runner
        super().__init__(parent)
        uic.loadUi("ui/config/tabs/domains/panel.ui", self)

        # Define internal attributes
        self._pushing_updates = False

        # create domains editor table and append it to the bottom of the domains panel
        self.table = Table(self, self.runner.managers.nucleic_acid_profile.current)
        self.layout().addWidget(self.table)

        # run setup functions
        self._hook_signals()
        self._prettify()

        self.dump_domains(self.runner.managers.domains.current)

        logger.info("Loaded domains tab of config panel.")

    def fetch_domains(self, nucleic_acid_profile: NucleicAcidProfile) -> Domains:
        """
        Fetch the domains from the domains table and settings panel.

        Args:
            nucleic_acid_profile: The nucleic acid profile to use for the domains.

        Returns:
            The domains object.
        """
        return Domains(
            domains=self.table.fetch_domains(),
            symmetry=self.symmetry.value(),
            nucleic_acid_profile=nucleic_acid_profile,
        )

    def dump_domains(self, domains: Domains) -> None:
        """
        Dump a Domains object's domains into the domains table and settings into the
        settings panel of the DomainsPanel.

        Args:
            domains: The Domains object to dump.
        """
        self.table.blockSignals(True)
        self.symmetry.blockSignals(True)

        # dump the current subunit into the subunit table
        self.table.dump_domains(domains.subunit.domains)

        self.subunit_count.setValue(domains.subunit.count)
        self.symmetry.setValue(domains.symmetry)

        # set M and target M boxes
        # https://github.com/404Wolf/NATuG3/issues/4
        M: int = sum([domain.theta_m_multiple for domain in domains.domains()])
        N: int = domains.count
        B: int = self.runner.managers.nucleic_acid_profile.current.B
        R: int = domains.symmetry
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

        self.table.blockSignals(False)
        self.symmetry.blockSignals(False)

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

    def _push_updates(self):
        """
        Warn the user if they are about to overwrite strand data, and if they are
        okay with that, then update the domains. Otherwise, revert to the old domains.
        """
        if self._pushing_updates:
            return
        self._pushing_updates = True
        # Warn the user if they are about to overwrite strand data, and give them the
        # opportunity to save the current state and then update the domains.
        if RefreshConfirmer.run(self.runner):
            self.runner.managers.domains.current.update(
                self.fetch_domains(self.runner.managers.nucleic_acid_profile.current)
            )
            self.dump_domains(self.runner.managers.domains.current)
            self.updated.emit()
            logger.debug("Updated domains.")
        # They rather not update the domains, so revert to the old domains.
        else:
            self.dump_domains(self.runner.managers.domains.current)
            logger.debug("Did not update domains because user chose not to.")
        self._pushing_updates = False

    def _hook_signals(self):
        """
        Hook all signals to their respective slots.

        Hooks the following signals:
            - table.cell_widget_updated
            - table.helix_joint_updated
            - symmetry.valueChanged
            - subunit_count.valueChanged
            - update_table_button.clicked
            - table.helix_joint_updated
            - auto_antiparallel_button.clicked
        """
        self.table.cell_widget_updated.connect(self._push_updates)
        self.table.helix_joint_updated.connect(self._push_updates)

        # Make sure that the total domain count is updated as the summands are changed.
        self.symmetry.valueChanged.connect(self._on_symmetry_setting_change)
        self.subunit_count.valueChanged.connect(self._on_symmetry_setting_change)

        # Read the settings area when the update table button is clicked.
        self.update_table_button.clicked.connect(self._on_table_update_button_clicked)

        # Reset the checked button when a helix joint is updated because the user has
        # opted out of the auto-antiparallel feature by changing the helix joint
        self.table.helix_joint_updated.connect(self._on_helix_joint_updated)
        self.auto_antiparallel.stateChanged.connect(self._push_updates)

        # Set up the save/load buttons slots.
        self.save_domains_button.clicked.connect(self._on_save_button_clicked)
        self.load_domains_button.clicked.connect(self._on_load_button_clicked)

    @pyqtSlot()
    def _on_symmetry_setting_change(self):
        """Update the total domain count box."""
        self.total_count.setValue(self.symmetry.value() * self.subunit_count.value())

    @pyqtSlot()
    def _on_table_update_button_clicked(self):
        new_table_domains = copy(self.runner.managers.domains.current)
        new_table_domains.subunit.count = self.subunit_count.value()
        self.table.dump_domains(new_table_domains.subunit.domains)
        self._push_updates()

    @pyqtSlot()
    def _on_helix_joint_updated(self):
        self.auto_antiparallel.setChecked(False)

    @pyqtSlot()
    def _on_save_button_clicked(self):
        """Save domains to file."""
        filepath = QFileDialog.getSaveFileName(
            parent=self,
            caption="Domains Save File Location Chooser",
            filter="*.csv",
        )[0]
        if len(filepath) > 0:
            logger.info(
                f"Saving domains to {filepath}."
                f"\nDomains being saved: {self.runner.managers.domains.current}"
            )
            domains_df = self.runner.managers.domains.current.to_df()
            domains_df.to_csv(filepath, index=False)

    @pyqtSlot()
    def _on_load_button_clicked(self):
        """Load domains from file."""
        filepath = QFileDialog.getOpenFileName(
            parent=self,
            caption="Domains Import File Location Chooser",
            directory=f"saves/domains/presets",
            filter="*.csv",
        )[0]
        if filepath:
            new_domains = Domains.from_df(
                df=pd.read_csv(filepath),
                nucleic_acid_profile=self.runner.managers.nucleic_acid_profile.current,
            )
            self.dump_domains(new_domains)
            self._push_updates()
            self.updated.emit()

    @pyqtSlot()
    def _on_settings_panel_update(self):
        """Refresh panel settings/domain table."""
        logger.info("Refreshing domains table.")

        old_domains: Domains = self.runner.managers.domains.current
        new_domains: Domains = self.fetch_domains(
            nucleic_acid_profile=self.runner.managers.nucleic_acid_profile.current
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
                f"The prospective subunit count ({self.subunit_count.value()}) is "
                f"lower than the number of domains in the domains table ("
                f"{self.table.rowCount()}). \n\nAre you sure you want to truncate the "
                f"domains/subunit count to {self.subunit_count.value()}?",
            )
            if confirmation:
                logger.info(
                    "User confirmed that they would like the subunit count reduced."
                )
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
                self.dump_domains(new_domains)
        else:
            self.dump_domains(old_domains)

        # update current domains
        self.runner.managers.domains.current.update(
            self.fetch_domains(
                nucleic_acid_profile=self.runner.managers.nucleic_acid_profile.current
            )
        )
