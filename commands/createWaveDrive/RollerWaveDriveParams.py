import math


class RollerWaveDriveParams:
    RESOLUTION = 8
    ECCENTRICITY = 0.2

    def __init__(self, roller_diameter: float, rollers_number: int, use_balls: bool, roller_height: float,
                 use_minimal_diameter: bool, cycloid_diameter: float, shaft_diameter: float, roller_tolerance: float):
        self.roller_diameter = roller_diameter
        self.roller_number = rollers_number
        self.use_balls = use_balls
        self._roller_height = roller_height
        self.use_minimal_diameter = use_minimal_diameter
        self.cycloid_diameter = cycloid_diameter
        self.shaft_diameter = shaft_diameter
        self.roller_tolerance = roller_tolerance

    @property
    def roller_height(self) -> float:
        return self.roller_diameter if self.use_balls else self._roller_height

    @property
    def min_cycloid_radius(self) -> float:
        num_dimples = self.roller_number + 1
        return (1.03 * self.roller_diameter) / math.sin(math.pi / num_dimples)

    @property
    def eccentricity(self) -> float:
        return self.ECCENTRICITY * self.roller_diameter

    @property
    def internal_radius(self) -> float:
        return self.cycloid_diameter - 2 * self.eccentricity

    @property
    def cam_radius(self) -> float:
        return self.internal_radius + self.eccentricity - self.roller_diameter

    @property
    def separator_thickness(self) -> float:
        return 2.2 * self.eccentricity

    @property
    def separator_middle_radius(self) -> float:
        return self.cam_radius + self.roller_diameter / 2

    @property
    def separator_inner_radius(self) -> float:
        return self.separator_middle_radius - self.separator_thickness / 2

    @property
    def separator_outer_radius(self) -> float:
        return self.separator_middle_radius + self.separator_thickness / 2

    @property
    def resolution(self) -> int:
        return self.RESOLUTION * (self.roller_number + 1)
