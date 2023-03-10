import logging
from dataclasses import dataclass
from typing import List

from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QApplication,
)

from structures.domains import Domain
from structures.profiles import NucleicAcidProfile
from ui.widgets import DirectionalButton, TableIntegerBox
from ui.widgets.triple_spinbox import TripleSpinbox

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TableWidgets:
    """
    A container for storing table data.

    Attributes:
        theta_m_multiple: User settable theta m multiple.
        theta_s_multiple: Automatically computed switch angle multiple.
        left_helix_joint: User settable left helix joint direction.
        right_helix_joint: User settable right helix joint direction.
        left_helix_count: User settable values for the bottom, middle, and top of the
            left helical strand.
        right_helix_count: User settable values for the bottom, middle, and top of the
            right helical strand.
    """

    theta_m_multiple: TableIntegerBox = None
    theta_s_multiple: TableIntegerBox = None
    left_helix_joint: DirectionalButton = None
    right_helix_joint: DirectionalButton = None
    left_helix_count: TripleSpinbox = None
    other_helix_count: TripleSpinbox = None

    def to_domain(self, nucleic_acid_profile: NucleicAcidProfile):
        """Obtain a domain object from the data in the TableWidgets."""
        return Domain(
            nucleic_acid_profile=nucleic_acid_profile,
            theta_m_multiple=self.theta_m_multiple.value(),
            left_helix_joint=self.left_helix_joint.state,
            right_helix_joint=self.right_helix_joint.state,
            left_helix_count=self.left_helix_count.values(),
            other_helix_count=self.other_helix_count.values(),
        )


class DomainsAnglesTable(QTableWidget):
    """Nucleic Acid Config Tab."""

    helix_joint_updated = pyqtSignal()
    cell_widget_updated = pyqtSignal()

    def __init__(self, parent, nucleic_acid_profile: NucleicAcidProfile) -> None:
        super().__init__(parent)
        # store the nucleic acid nucleic_acid_profile
        self.nucleic_acid_profile = nucleic_acid_profile

        # header storage areas
        self.side_headers = []
        self.top_headers = []

        # all current row data
        # (domain index = row index)
        self.rows = []

        # set up headers
        self._headers()

        # style the widget
        self._prettify()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Intercept a keypress to alter tabbing."""
        if event.key() in (
            Qt.Key.Key_Tab,
            Qt.Key.Key_Backtab,
            Qt.Key.Key_Down,
            Qt.Key.Key_Up,
        ):
            # Determine the row and column to highlight
            row, column = self.currentRow(), self.currentColumn()
            if event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Down):
                row += 1
            else:
                row -= 1
            if row == len(self.rows):
                row = 0

            # Ensure that the previous widget's data is saved
            self.cellWidget(row, column).editingFinished.emit()
            self.cell_widget_updated.emit()

            # Disable signals temporarily
            self.setTabKeyNavigation(False)
            self.blockSignals(True)

            # Obtain the widget
            to_focus = self.cellWidget(row, column)

            # Create a list of key press events to send
            events = []
            if to_focus is not None:
                # Change the table focus
                self.setCurrentCell(row, column)
                to_focus.setFocus()

                # Simulate a control A press
                QApplication.postEvent(
                    to_focus,
                    QKeyEvent(
                        QEvent.Type.KeyPress,
                        Qt.Key.Key_A,
                        Qt.KeyboardModifier.ControlModifier,
                    ),
                )

            # Unblock signals
            self.blockSignals(False)
            self.setTabKeyNavigation(True)
        else:
            # Otherwise use the normal keypress event
            super().keyPressEvent(event)

    def _headers(self):
        """Configure top headers of widget"""
        # store headers (these do not change)
        self.top_headers = (
            "L-Joint",
            "R-Joint",
            "s",
            "m",
            "Left Count",
            "Other Count",
        )
        # create a column for each header
        self.setColumnCount(len(self.top_headers))
        # apply the headers
        self.setHorizontalHeaderLabels(self.top_headers)

    def _prettify(self):
        """Style the domain panel."""
        # set the style worksheet of the panel
        self.setStyleSheet("QTableView::item{padding: 3.25px; text-align: center}")

        # show table grid
        self.setShowGrid(True)

        # enable smooth scrolling
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        # all columns are statically sized
        for column in range(self.columnCount()):
            self.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.Fixed
            )

        # set column widths
        self.setColumnWidth(0, 40)
        self.setColumnWidth(1, 40)
        self.setColumnWidth(2, 40)
        self.setColumnWidth(3, 47)
        self.setColumnWidth(4, 96)
        self.setColumnWidth(5, 96)

    def dump_domains(self, domains: List[Domain]) -> None:
        """
        Dump a list of domain objects.

        Args:
            domains (List(Domain)): A list of all domains to dump.
        """
        # create rows before we input widgets
        self.setRowCount(len(domains))

        # clear out the side headers list
        self.side_headers = []

        # container for current row items
        self.rows.clear()

        # insert all domains
        for index, domain in enumerate(domains):
            # container for currently-being-added widgets
            row = TableWidgets()

            # column 0 - left helical joint
            row.left_helix_joint = DirectionalButton(
                self, domains[index].left_helix_joint
            )
            row.left_helix_joint.clicked.connect(self.helix_joint_updated.emit)
            row.left_helix_joint.clicked.connect(self.cell_widget_updated.emit)
            self.setCellWidget(index, 0, row.left_helix_joint)

            # column 1 - right helical joint
            row.right_helix_joint = DirectionalButton(
                self, domains[index].right_helix_joint
            )
            row.right_helix_joint.clicked.connect(self.helix_joint_updated.emit)
            row.right_helix_joint.clicked.connect(self.cell_widget_updated.emit)
            self.setCellWidget(index, 1, row.right_helix_joint)

            # column 2 - theta switch multiple
            row.theta_s_multiple = TableIntegerBox(domain.theta_s_multiple, minimum=-1)
            row.theta_s_multiple.setEnabled(False)
            self.setCellWidget(index, 2, row.theta_s_multiple)

            # column 3 - theta interior multiple
            row.theta_m_multiple = TableIntegerBox(
                domain.theta_m_multiple,
                show_buttons=True,
                minimum=1,
                maximum=30,
            )
            row.theta_m_multiple.editingFinished.connect(self.cell_widget_updated.emit)
            self.setCellWidget(index, 3, row.theta_m_multiple)

            # column 4 - initial NEMid count for the left helix
            row.left_helix_count = TripleSpinbox(domain.left_helix_count)
            row.left_helix_count.editingFinished.connect(self.cell_widget_updated.emit)
            self.setCellWidget(index, 4, row.left_helix_count)

            # column 5 - initial NEMid count for the other helix
            row.other_helix_count = TripleSpinbox(domain.other_helix_count)
            row.other_helix_count.editingFinished.connect(self.cell_widget_updated.emit)
            self.setCellWidget(index, 5, row.other_helix_count)

            # Add the label
            self.side_headers.append(f"#{index + 1}")

            # append to the row storage container
            self.rows.append(row)

        class smooth_interior_updating:
            """A class that manages smooth theta_m arrow clicks."""

            @classmethod
            def surrounding(cls, i):
                # make sure to wrap around to the beginning/end of the domains list
                # if "i" is the length of the list or is 0
                if i == (len(self.rows) - 1):
                    surrounding = (i - 1, i, 0)
                elif i == 0:
                    surrounding = (len(self.rows) - 1, 0, i + 1)
                else:
                    surrounding = (i - 1, i, i + 1)

                surrounding = [
                    self.rows[surrounding[0]].theta_m_multiple,
                    self.rows[surrounding[1]].theta_m_multiple,
                    self.rows[surrounding[2]].theta_m_multiple,
                ]

                return surrounding

            @classmethod
            def down(cls, i):
                surrounding = cls.surrounding(i)
                surrounding[0].setValue(surrounding[0].value() + 1)
                # it was just ticked down 1, so tick it down 1 more
                surrounding[1].setValue(surrounding[1].value() - 1)
                surrounding[2].setValue(surrounding[2].value() + 1)
                self.cell_widget_updated.emit()

            @classmethod
            def up(cls, i):
                surrounding = cls.surrounding(i)
                surrounding[0].setValue(surrounding[0].value() - 1)
                # it was just ticked up 1, so tick it up 1 more
                surrounding[1].setValue(surrounding[1].value() + 1)
                surrounding[2].setValue(surrounding[2].value() - 1)
                self.cell_widget_updated.emit()

        for index, row in enumerate(self.rows):
            row.theta_m_multiple.down_button_clicked.connect(
                lambda i=index: smooth_interior_updating.down(i)
            )
            row.theta_m_multiple.up_button_clicked.connect(
                lambda i=index: smooth_interior_updating.up(i)
            )

        self.setVerticalHeaderLabels(self.side_headers)

    def fetch_domains(self) -> List[Domain]:
        """
        Obtain a list of the currently chosen domains.

        This returns a list of Domain objects, NOT a Domains object.

        Returns:
            A list of the domains that populate the domains table.
        """
        domains = []  # output list of domains
        for row in self.rows:
            domains.append(row.to_domain(self.nucleic_acid_profile))

        return domains
