from typing import Tuple

from constants.directions import *
from structures.points.point import x_coord_from_angle
from structures.profiles import NucleicAcidProfile
from structures.strands import Strand


class GenerationCount:
    """
    A class for storing the number of NEMids to generate for a domain.

    Attributes:
        bottom_count: The number of NEMids to generate for the bottom strand.
        body_count: The number of NEMids to generate for the body strand.
        top_count: The number of NEMids to generate for the top strand.

    Method:
        direction: The direction that this is the generation count for.
    """

    def __init__(self, count: Tuple[int, int, int], direction=None):
        """
        Initialize a GenerationCount object.

        Args:
            count: The number of NEMids to generate for the bottom, body, and top
                strands.
        """
        self.bottom_count = count[0]
        self.body_count = count[1]
        self.top_count = count[2]

        self.direction = direction

    def __len__(self) -> int:
        """
        Get the number of NEMids to generate for the bottom, body, and top strands.

        Returns:
            The number of NEMids to generate for the bottom, body, and top strands.
        """
        return 3

    def __getitem__(self, index: int) -> int:
        """
        Get the number of NEMids to generate for the bottom, body, and top strands.

        Args:
            index: The index of the number of NEMids to generate for the bottom, body,
                and top strands.

        Returns:
            The number of NEMids to generate for the bottom, body, and top strands.
        """
        if index == 0:
            return self.bottom_count
        elif index == 1:
            return self.body_count
        elif index == 2:
            return self.top_count
        else:
            raise IndexError("Index out of range.")

    def __setitem__(self, index: int, value: int):
        """
        Set the number of NEMids to generate for the bottom, body, and top strands.

        Args:
            index: The index of the number of NEMids to generate for the bottom, body,
                and top strands.
            value: The number of NEMids to generate for the bottom, body, and top
                strands.
        """
        if index == 0:
            self.bottom_count = value
        elif index == 1:
            self.body_count = value
        elif index == 2:
            self.top_count = value
        else:
            raise IndexError("Index out of range.")


class Domain:
    """
    A singular domain object.

    Attributes:
        parent: The strands workers container object. If this is None then index becomes
            None too.
        index: The index of this domain in its strands.
        up_strand (Strand): The up strand of the domain. This is an unparented strand
            object.
        down_strand (Strand): The down strand of the domain. This is an unparented
            strand object.
        theta_m_multiple: Angle between this and the next workers' line of tangency.
            Multiple of theta_c. This is the angle between i,i+1's line of tangency
            and i+1,i+2's line of tangency where i is the index of this domain. This
            is the theta_m_multiple times the characteristic angle.
        theta_m: Angle between this and the next workers' line of tangency. In degrees.
            This is the angle between i,i+1's line of tangency and i+1,i+2's line of
            tangency where i is the index of this domain. This is the theta_m_multiple
            times the characteristic angle.
        theta_s_multiple: The switch from upness to downness (or lack thereof) of the
            helix joints.
            (-1) for up to down switch; (0) for both up/down switch; (1) for down to up
            switch
        nucleic_acid_profile: the nucleic acid configuration for the domain.
        left_helix_joint: The left helix joint's upwardness or downwardness.
            "Left" indicates that the left side of this domain will be lined up to
            the right helix joint of the previous domain. Uses the constant 0 for up and
            1 for down.
        right_helix_joint: The right helix joint's upwardness or downwardness.
            "right" indicates that the right side of this domain will be lined up to
            the left helix joint of the next domain. Uses the constant 0 for up and 1
            for down.
        left_helix_count: Number of initial NEMids/strand to generate for the left
            helix joint direction helix. This is a list of bottom-count, body-count,
            and top-count. The number of NEMids in the domains' is determined by
            count[1], and then count[0] NEMids are added to the bottom strand and
            count[2] NEMids are added to the top of the strand.
        other_helix_count: Number of initial NEMids/strand and excess NEMids/strand to
            generate for the other helix.
    """

    def __init__(
        self,
        nucleic_acid_profile: NucleicAcidProfile,
        theta_m_multiple: int,
        left_helix_joint: int,
        right_helix_joint: int,
        left_helix_count: Tuple[int, int, int],
        other_helix_count: Tuple[int, int, int],
        parent: "Domains" = None,
        index: int = None,
    ):
        """
        Initialize a Domain object.

        Args:
            nucleic_acid_profile: The nucleic acid settings nucleic_acid_profile
            theta_m_multiple: Angle between this and the next workers' lines of
                tangency. Multiple of theta c.
            left_helix_joint: The left helix joint's upwardness or downwardness.
                "Left" indicates that the left side of this domain will be lined up to
                the right helix joint of the previous domain. Uses the constant 0 for
                up and 1 for down.
            right_helix_joint: The right helix joint's upwardness or downwardness.
                "right" indicates that the right side of this domain will be lined up to
                the left helix joint of the next domain. Uses the constant 0 for up and
                1 for down.
            left_helix_count: Number of initial NEMids/strand to generate. This is a
                list of bottom-count, body-count, and top-count. The number of NEMids
                in the domains' is determined by count[1], and then count[0] NEMids are
                added to the bottom strand and count[2] NEMids are added to the top of
                the strand.
            other_helix_count: Number of initial NEMids/strand to generate for the
            non-left helix. This is a list of
                bottom-count, body-count, and top-count. The number of NEMids in the
                domains' is determined by count[1], and then count[0] NEMids are
                added to the bottom strand and count[2] NEMids are added to the top
                of the strand.
            parent (Subunit): The strands subunit. Defaults to None.
            index (int): The index of this domain in its strands. Defaults to None.
        """
        # store the strands subunit
        self.parent = parent

        # store the nucleic acid settings
        self.nucleic_acid_profile = nucleic_acid_profile

        # multiple of the characteristic angle (theta_c) for the interior angle
        self.theta_m_multiple: int = theta_m_multiple

        # the helical joints
        self.left_helix_joint = left_helix_joint
        self.right_helix_joint = right_helix_joint
        assert self.left_helix_joint in [0, 1]
        assert self.right_helix_joint in [0, 1]

        # the number of NEMids to generate for the left and right helices
        self.left_helix_count = GenerationCount(
            left_helix_count, direction=lambda: self.left_helix_joint
        )
        self.other_helix_count = GenerationCount(
            other_helix_count, direction=lambda: self.right_helix_joint
        )
        assert len(self.left_helix_count) == 3
        assert len(self.other_helix_count) == 3

        # set the index of the domain
        self.index = index

    def angles(self, start=0):
        """
        Obtain the angles of the NEMids of the Domain.

        Yields:
            The angle of each NEMid in the domain.
        """
        angle = start
        while True:
            angle += self.nucleic_acid_profile.theta_b
            yield angle

    def x_coords(self):
        """
        Obtain the x coords of the NEMids of the Domain.

        Yields:
            The x coords of each NEMid in the domain.
        """
        for angle in self.angles():
            yield x_coord_from_angle(angle, self)

    def z_coords(self, start=0):
        """
        Obtain the z coords of the NEMids of the Domain.

        Yields:
            The z coords of each NEMid in the domain.
        """
        z_coord = start
        while True:
            z_coord += self.nucleic_acid_profile.Z_b
            yield z_coord

    @property
    def left_strand(self) -> Strand | None:
        """
        The left strand of the domain.

        The grandparent's .points() method is used to obtain the strand. Note that
        the grandparent of a Domain object is the strands of the strands. The strands of
        a Domains object is a Subunit object, and the strands of a Subunit object is a
        Domains object. It is the Domains object that has a .points() method.

        Returns:
            The left strand of the domain or None if the domain doesn't have a strands.
        """
        if self.parent is None or self.parent.strands:
            return None
        else:
            return Strand(self.parent.strands.points()[self.index][RIGHT])

    @property
    def right_strand(self) -> Strand | None:
        """
        The right strand of the domain.

        The grandparent's .points() method is used to obtain the strand. Note that
        the grandparent of a Domain object is the strands of the strands. The strands of
        a Domains object is a Subunit object, and the strands of a Subunit object is a
        Domains object. It is the Domains object that has a .points() method.

        Returns:
            The right strand of the domain or None if the domain doesn't have a strands.
        """
        if self.parent is None:
            return None
        else:
            return Strand(self.parent.strands.points()[self.index][RIGHT])

    @property
    def theta_s_multiple(self) -> int:
        """
        Obtain the theta switch multiple. This is either -1, 0, or 1.
        Based on the left and right helical joints, this outputs:
        (-1) for up to down; (0) for both up/down; (1) for down to up

        This is very computationally inexpensive, so it is a property.
        (self.theta_s_multiple)
        """
        helix_joints = (self.left_helix_joint, self.right_helix_joint)
        if helix_joints == (UP, DOWN):
            return -1
        elif helix_joints == (UP, UP):
            return 0
        elif helix_joints == (DOWN, DOWN):
            return 0
        elif helix_joints == (DOWN, UP):
            return 1
        else:
            raise ValueError("Invalid helical joint integer", helix_joints)

    @property
    def theta_s(self) -> float:
        """
        Obtain the theta switch angle.

        This is equivalent to self.theta_s_multiple * self.theta_s.
        Updated Bill 2/11/23
        """
        return self.theta_s_multiple * self.nucleic_acid_profile.theta_s

    @property
    def theta_m(self) -> float:
        """
        Obtain the theta interior angle.

        This is equivalent to self.theta_m_multiple * self.theta_c.
        """
        return self.theta_m_multiple * self.nucleic_acid_profile.theta_c

    def __repr__(self):
        """Return a string representation of the Domain object."""
        return (
            f"Domain("
            f"m={self.theta_m_multiple}, "
            f"left_joint={self.left_helix_joint}, "
            f"right_joint={self.right_helix_joint}, "
            f"left_count={self.left_helix_count}, "
            f"other_count={self.other_helix_count}, "
            f"index={self.index}"
            f")"
        )
