"""Revision B dimensions in millimetres; no geometry is generated on import."""
from dataclasses import asdict, dataclass, replace
import math


@dataclass(frozen=True)
class Config:
    revision: str = "B"
    profile: str = "large"
    knife_z: float = 150.0
    edge_y: float = -70.0
    pivot_y: float = 100.0
    blade_thickness: float = 3.0
    stone_width: float = 60.0
    stone_length: float = 180.0
    stone_thickness: float = 30.0
    stone_backing: float = 2.0
    rod_offset: float = 44.0
    rod_length: float = 400.0
    rod_start: float = -110.0
    rod_diameter: float = 8.0
    angle: float = 20.0
    angle_min: float = 15.0
    angle_max: float = 25.0
    # Working yaw is positively locked. Reposition the knife in short sections
    # rather than changing the sharpening-plane orientation along a long edge.
    yaw_limit: float = 0.0
    stroke: float = 25.0
    bushing_length: float = 40.0
    base_width: float = 200.0
    base_depth: float = 240.0
    frame_height: float = 300.0

    @property
    def pivot_distance(self):
        return self.pivot_y - self.edge_y

    def pivot_height(self, angle=None):
        a = math.radians(self.angle if angle is None else angle)
        return self.knife_z + self.pivot_distance * math.tan(a) + self.rod_offset / math.cos(a)

    def guide_u(self, angle=None):
        a = math.radians(self.angle if angle is None else angle)
        return (self.pivot_distance + self.rod_offset * math.sin(a)) / math.cos(a)

    def to_dict(self):
        return asdict(self) | {"pivot_distance": self.pivot_distance}


def get_config(profile="large"):
    cfg = Config()
    if profile == "slim":
        return replace(cfg, profile="slim", stone_width=25.0, stone_length=150.0,
                       stone_thickness=6.0, rod_offset=20.0)
    if profile != "large":
        raise ValueError(f"Unknown stone profile: {profile}")
    return cfg
