import pickle
import logging
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget
from resources import fetch_icon
from dataclasses import dataclass
from contextlib import suppress
import references


filename = "config/saves/nucleic_acid.nano"
current = None  # current profile
previously_loaded_name = None
profiles = None  # all profiles
logger = logging.getLogger(__name__)
last_state_name = "Restored Settings"


@dataclass
class profile:
    """
    A settings profile.

    Attributes:
        D (float): Diameter of a domain.
        H (float): Height of a turn.
        T (float): There are T turns every B bases.
        B (float): There are B bases every T turns.
        Z_c (float): Characteristic height.
        Z_s (float): Switch height.
        Z_b (float): Base height.
        theta_b (float): Base angle.
        theta_c (float): Characteristic angle.
        theta_s (float): Switch angle.
    """

    D: float = 0
    H: float = 0.0
    T: int = 0
    B: int = 0
    Z_c: float = 0.0
    Z_s: float = 0.0
    theta_b: float = 0.0
    theta_c: float = 0.0
    theta_s: float = 0.0

    def __post_init__(self) -> None:
        # compute Z_b based on T, H, and B
        self.Z_b = (self.T * self.H) / self.B
        self.Z_b = round(self.Z_b, 4)

    def __eq__(self, other: object) -> bool:
        """Returns true if identical profile is returned"""
        return vars(self) == vars(other)


def load() -> None:
    global current
    global profiles

    try:
        logger.debug("Settings file found. Loading setting profiles...")
        # attempt to open the settings file, or create a new settings file with
        # DNA-B settings (as a default/example)
        with open(filename, "rb") as settings_file:
            current, profiles = pickle.load(settings_file)

    except FileNotFoundError:
        logger.debug("Settings file not found. Restoring defaults...")
        current = profile(
            D=2.2,
            H=3.549,
            T=2,
            B=21,
            Z_c=0.17,
            Z_s=1.26,
            theta_b=34.29,
            theta_c=17.1428,
            theta_s=2.3,
        )
        profiles = {"B-DNA": current}

    logger.debug("Loaded profiles.")
    logger.debug(profiles)


def dump() -> None:
    """Dump persisting attributes of this module to a file"""
    # dump settings to file in format current-profile, all-profiles
    with open(filename, "wb") as settings_file:
        pickle.dump((current, profiles), settings_file)


class widget(QWidget):
    """Nucleic Acid Config Tab"""

    def __init__(self) -> None:
        super().__init__()
        uic.loadUi("config/ui/nucleic_acid.ui", self)

        # prettify buttons
        self.load_profile_button.setIcon(fetch_icon("download-outline"))
        self.save_profile_button.setIcon(fetch_icon("save-outline"))
        self.delete_profile_button.setIcon(fetch_icon("trash-outline"))

        # restore the current settinsg
        self.dump_settings(current)

        # set up the profile manager
        self._profile_manager()

        # hook all input boxes to respective functions
        self._inputs_setup()

    def _profile_manager(self) -> None:
        """Set up the profile manager"""
        # function to obtain list of all items in profile_chooser
        self.profile_list = lambda: [
            self.profile_chooser.itemText(i)
            for i in range(self.profile_chooser.count())
        ]
        # function to obtain index of a given profile
        self.profile_index = lambda name: self.profile_list().index(name)

        # add each profile to the combo box
        for profile_name in profiles:
            self.profile_chooser.addItem(profile_name)

        # scan to see if the last used settings belonged to a profile
        profile_found = False
        for name, profile in profiles.items():
            # if they did then set it to that profile
            if current == profile:
                self.profile_chooser.setCurrentIndex(self.profile_index(name))
                profile_found = True
                break
        if not profile_found:
            # add current profile as the restored profile
            self.profile_chooser.addItem(last_state_name)
            self.profile_chooser.setCurrentIndex(self.profile_index(last_state_name))
        previously_loaded_name = self.profile_chooser.currentText()

        # Worker for the save button
        def save_profile():
            # obtain name of profile to save
            profile_name = self.profile_chooser.currentText()
            # save the profile with the current settings
            profiles[profile_name] = self.fetch_settings()
            if profile_name not in self.profile_list():
                # add the new profile to the profile chooser
                self.profile_chooser.addItem(profile_name)

        self.save_profile_button.clicked.connect(save_profile)

        # Worker for the delete button
        def delete_profile():
            # obtain name of profile to delete
            profile_name = self.profile_chooser.currentText()
            with suppress(KeyError):
                del profiles[profile_name]
                # index of profile in the profile chooser dropdown
                profile_index = self.profile_index(profile_name)
                # remove profile by index from profile chooser
                self.profile_chooser.removeItem(profile_index)

        self.delete_profile_button.clicked.connect(delete_profile)

        def load_profile():
            """Current-profile-changed worker."""
            global previously_loaded_name
            self.load_profile_button.setChecked(True)
            current_profile = self.profile_chooser.currentText()
            previously_loaded_name = current_profile
            if current_profile == last_state_name:
                self.dump_settings(current)
            else:
                self.dump_settings(profiles[current_profile])

        self.load_profile_button.clicked.connect(load_profile)

        # load the restored settings profile
        load_profile()

    def _inputs_setup(self) -> None:
        """Link input boxes to their respective functions."""

        # create list of all input boxes for easier future access
        self.input_widgets = (
            self.D,
            self.H,
            self.T,
            self.B,
            self.Z_c,
            self.Z_s,
            self.theta_b,
            self.theta_c,
            self.theta_s,
        )

        def input_changed(input):
            """Store new settings on input box changed event"""
            global current

            # fetch settings of input boxes
            current = self.fetch_settings()

            # if B or T or H were changed Z_b also will have changed
            self.Z_b.setValue(current.Z_b)

            with suppress(KeyError):
                # if the selected profile is still the previoiusly loaded one
                # and the profile chooser combo box hasn't changed
                if (self.profile_chooser.currentText() == previously_loaded_name) and (
                    (current == profiles[previously_loaded_name])
                    or (self.profile_chooser.currentText() == last_state_name)
                ):
                    # toggle the current profile
                    self.profile_chooser.setCurrentIndex(
                        self.profile_index(previously_loaded_name)
                    )
                    self.load_profile_button.setChecked(True)
                # if the selected profile has changed
                else:
                    self.load_profile_button.setChecked(False)

                # if the current graph's settings are the same as the current settings
                # lock the update graphs button
                if (
                    current
                    == references.windows.constructor.top_view.settings
                    == references.windows.constructor.side_view.settings
                ):
                    references.buttons.update_graphs.setChecked(True)
                else:
                    references.buttons.update_graphs.setChecked(False)

        for input in self.input_widgets:
            # for all input boxes hook them to the input changed function
            input.valueChanged.connect(lambda: input_changed(input))

        # unhighlight the profile chooser if the current profile input is changed
        self.profile_chooser.currentTextChanged.connect(
            lambda: self.load_profile_button.setChecked(False)
        )

        input_changed(None)

    def dump_settings(self, profile: profile) -> None:
        """Saves current settings to profile with name in text edit input box."""
        self.D.setValue(profile.D)
        self.H.setValue(profile.H)
        self.T.setValue(profile.T)
        self.B.setValue(profile.B)
        self.Z_c.setValue(profile.Z_c)
        self.Z_s.setValue(profile.Z_s)
        self.Z_b.setValue(profile.Z_b)
        self.theta_b.setValue(profile.theta_b)
        self.theta_c.setValue(profile.theta_c)
        self.theta_s.setValue(profile.theta_s)

    def fetch_settings(self) -> profile:
        """Fetch a profile object with all current nucleic acid settings from inputs."""
        return profile(
            D=self.D.value(),
            H=self.H.value(),
            T=self.T.value(),
            B=self.B.value(),
            Z_c=self.Z_c.value(),
            Z_s=self.Z_s.value(),
            theta_b=self.theta_b.value(),
            theta_c=self.theta_c.value(),
            theta_s=self.theta_s.value(),
        )
