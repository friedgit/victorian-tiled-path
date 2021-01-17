import math
from panda3d.core import *
from collections import deque
from enum import Enum

import tile_poly as tile

class T_Evt(Enum):
    """
    Directional instructions for laying border tiles when changing direction,
    or, for the _PT ones, creating an internal collision tube to protect the
    tip of a diagonally laid square tile.
    """
    NONE = 0
    # proceeding anti-clockwise
    EAST = 1
    NORTH = 2
    WEST = 3
    SOUTH = 4

    REMOVE = 5
    START = 6

    # TODO these not recognised by intrusion detector
    # Ordinal points of a diagonally laid square tile
    EA_PT = 7
    NO_PT = 8
    WE_PT = 9
    SO_PT = 10


class Tiles:
    """
    Collection of methods for generating different kinds of tiles. Some, such as the
    triangles, aren't used anymore, because they appear by virtue of the border
    occluding parts of the diagonally laid inner tiles.
    """
    # Prisms
    square = [[-1, -1], [1, -1], [1, 1], [-1, 1]]
    triangle = [[-1, -1], [1, -1], [1, 1]]
    rectangle = [[-3, -1], [3, -1], [3, 1], [-3, 1]]
    short_rect = [[-2, -1], [2, -1], [2, 1], [-2, 1]]

    # Ratios
    off = 1 / (1 + math.sqrt(2))
    rad = 2 / (2 + math.sqrt(2))

    tip_rad = 0.1

    @classmethod
    def cnr_tri(cls, pos, tag, phase):
        # return tile.Tile(pos, cls.triangle, "tex/black_front.jpg",
        return tile.Tile(pos, cls.triangle, "tex/white_front.jpg",
                       tip_rad=cls.tip_rad, p_tag=tag,
                       cg=[cls.off,-cls.off], cg_rad=cls.rad,
                       sym_rot=360, phase=phase,
                       scale=1/math.sqrt(2))

    @classmethod
    def edge_tri(cls, pos, tag, phase):
        # return tile.Tile(pos, cls.triangle, "tex/black_front.jpg",
        return tile.Tile(pos, cls.triangle, "tex/white_front.jpg",
                       tip_rad=cls.tip_rad, p_tag=tag,
                       cg=[cls.off,-cls.off], cg_rad=cls.rad,
                       sym_rot=360, phase=phase)

    @classmethod
    def off_edge_diamond(cls, pos, tag, phase):
        # return tile.Tile(pos, cls.square, "tex/white_front.jpg",
        return tile.Tile(pos, cls.square, "tex/black_front.jpg",
                         tip_rad=cls.tip_rad, p_tag=tag,
                         sym_rot=90, phase=phase, hopper=True)

    @classmethod
    def edge_diamond(cls, pos, tag, phase):
        # return tile.Tile(pos, cls.square, "tex/black_front.jpg",
        return tile.Tile(pos, cls.square, "tex/white_front.jpg",
                         tip_rad=cls.tip_rad, p_tag=tag,
                         sym_rot=90, phase=phase, hopper=True)

    @classmethod
    def edge_strip(cls, pos, tag, phase):
        return tile.Tile(pos, cls.rectangle, "tex/black_front.jpg",
                         tip_rad=cls.tip_rad, p_tag=tag,
                         sym_rot=180, phase=phase, scale=1/3)

    @classmethod
    def short_strip(cls, pos, tag, phase):
        return tile.Tile(pos, cls.short_rect, "tex/black_front.jpg",
                         tip_rad=cls.tip_rad, p_tag=tag,
                         sym_rot=180, phase=phase, scale=1/3)

    @classmethod
    def edge_square(cls, pos, tag, phase):
        return tile.Tile(pos, cls.square, "tex/black_front.jpg",
                         tip_rad=cls.tip_rad, p_tag=tag,
                         sym_rot=90, phase=phase, scale=1/3)


class TileDispenser:
    """
    Creates a schedule of tiles to dispense for the border tiles. Also contains all the methods
    for the inner tiles, but they're not invoked here. Instead the inner tile methods are invoked
    in a subclass, TileDispenser2.
    """
    up_lf = [Vec3(0.0, 0.080, -0.080) * 3, Vec3(-0.060, 0.080, -0.080) * 1.5]
    up_hl = [Vec3(0.0, 0.080, -0.080) * 3, Vec3(-0.060, 0.020, -0.080) * 1.5]
    dn_lf = [Vec3(0.0, -0.080, -0.080) * 3, Vec3(-0.060, -0.080, -0.080) * 1.5]
    lf_up = [Vec3(-0.060, 0.0, -0.080) * 3, Vec3(-0.060, 0.080, -0.080) * 1.5]
    lf_dn = [Vec3(-0.060, 0.0, -0.080) * 3, Vec3(-0.060, -0.080, -0.080) * 1.5]
    rt_dn = [Vec3(0.060, 0.0, -0.080) * 3, Vec3(0.060, -0.080, -0.080) * 1.5]
    up_up = [Vec3(0.0, 0.080, -0.080) * 3, Vec3(0.0, 0.080, -0.080) * 1.5]
    up_up_lf = [Vec3(0.0, 0.080, -0.080) * 3, Vec3(0.0, 0.080, -0.080) * 1.5, Vec3(-0.060, 0.060, -0.080) * 1.5]
    up_rt = [Vec3(0.0, 0.080, -0.080) * 3, Vec3(0.060, 0.080, -0.080) * 1.5]
    dn_rt = [Vec3(0.0, -0.080, -0.080) * 3, Vec3(0.060, -0.080, -0.080) * 1.5]
    up_rt_lf = [Vec3(0.0, 0.080, -0.080) * 3, Vec3(0.060, 0.080, -0.080) * 1.5, Vec3(-0.060, 0.080, -0.080) * 1.5]

    def __init__(self, top_y):
        self.schedule = deque()

        self.left_edge(top_y - 5)

        y = top_y - 7
        z = 1
        self.sched_tile(Tiles.short_strip, phase=0, xyz=(2,y,z), traj=self.lf_dn, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(3.2,y,z), traj=self.lf_dn, event=T_Evt.EAST)

        self.left_edge2(top_y - 15)

        y = top_y - 12
        z = 1
        self.sched_tile(Tiles.short_strip, phase=0, xyz=(1,y,z), traj=self.dn_rt, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(0.5,y,z), traj=self.dn_rt, event=T_Evt.REMOVE)

        self.left_edgeX(top_y - 17)
        self.bottom_edge(top_y - 19, traj=self.dn_lf)
        self.right_edgeX(top_y - 17)

        y = top_y - 16
        z = 1
        self.sched_tile(Tiles.short_strip, phase=0, xyz=(11,y,z), traj=self.up_rt, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(9.5,y,z), traj=self.up_rt, event=T_Evt.WEST)

        self.right_edge2(top_y - 10)

        y = top_y - 10
        z = 1
        self.sched_tile(Tiles.short_strip, phase=0, xyz=(12,y,z), traj=self.up_lf, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(13.5,y,z), traj=self.up_lf, event=T_Evt.EAST)

        self.right_edge(top_y - 4.3)
        self.top_edge(top_y - 3, traj=self.up_lf)

        self.count = 0

    def whole_row(self, y):
        print('yywh1', y)
        z = 1
        self.schedule.append(dict(shape=Tiles.off_edge_diamond, phase=45, xyz=(2.5,y,z), traj=self.up_lf, short=True, event=T_Evt.EA_PT))
        print('yywh2', y)
        self.schedule.append(dict(shape=Tiles.off_edge_diamond, phase=45, xyz=(5,y,z), traj=self.up_lf, short=True, event=T_Evt.EA_PT))
        print('yywh3', y)
        self.schedule.append(dict(shape=Tiles.off_edge_diamond, phase=45, xyz=(7.5,y,z), traj=self.up_lf, short=True, event=T_Evt.EA_PT))

    def split_row(self, y):
        print('yysp1', y)
        z = 1
        self.schedule.append(dict(shape=Tiles.edge_diamond, phase=45, xyz=(3.5,y,z), traj=self.up_lf, short=True, event=T_Evt.EA_PT))
        print('yysp2', y)
        self.schedule.append(dict(shape=Tiles.edge_diamond, phase=45, xyz=(6,y,z), traj=self.up_lf, short=True, event=T_Evt.EA_PT))
        print('yysp3', y)
        self.schedule.append(dict(shape=Tiles.edge_diamond, phase=45, xyz=(9,y,z), traj=self.up_hl, short=True, event=T_Evt.NONE))

    def sched_tile(self, shape, phase, xyz, traj, event):
        # short is nearly always False, so cut it out of the (too long) parameter list
        self.schedule.append(dict(shape=shape, phase=phase, xyz=xyz, traj=traj, short=False, event=event))

    def popup(self):
        tile_spec = self.schedule.popleft()
        self.count += 1
        start_pos = tile_spec['xyz']
        this_tile = tile_spec['shape'](start_pos, "tile"+str(self.count),
                                       tile_spec['phase'])
        trajectory = [Vec3(v) for v in tile_spec['traj']]
        use_short_cushion = tile_spec['short']
        event = tile_spec['event']
        return this_tile, trajectory, use_short_cushion, event

    def tiles_left(self):
        return len(self.schedule)

    def bottom_edge(self, y, traj):
        z = 1
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(2+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(4+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(6+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.short_strip, phase=0, xyz=(8+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(10+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(10+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(11.5+1.2,y,z), traj=traj, event=T_Evt.EAST)

    def top_edge(self, y, traj):
        z = 1
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(2+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(4+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(6+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.short_strip, phase=0, xyz=(8+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(10+1.3333,y,z), traj=traj, event=T_Evt.NONE)
        self.sched_tile(Tiles.edge_strip, phase=0, xyz=(10+1.3333,y,z), traj=self.up_rt, event=T_Evt.NONE)

    def left_edge(self, y_top):
        z = 1
        y = y_top - 1
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(1.2,y,z), traj=self.up_lf, event=T_Evt.START)
        for i in range(3):
            y = y_top - i * 1.5
            self.sched_tile(Tiles.edge_strip, phase=90, xyz=(0.7,y,z), traj=self.up_lf, event=T_Evt.NONE)
        y = y_top - 4 * 1.5
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(0.7,y,z), traj=self.up_lf, event=T_Evt.SOUTH)

    def left_edgeX(self, y_top):
        z = 1
        for i in range(3):
            y = y_top - i * 1.5
            self.sched_tile(Tiles.edge_strip, phase=90, xyz=(1.7,y,z), traj=self.lf_up, event=T_Evt.NONE)
        y = y_top - 4
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(0.7,y,z), traj=self.up_lf, event=T_Evt.SOUTH)

    def left_edge2(self, y_top):
        x = 2
        z = 1
        for i in range(3):
            y = y_top - i * 1.5
            if i == 1:
                self.sched_tile(Tiles.short_strip, phase=90, xyz=(x,y,z), traj=self.up_rt, event=T_Evt.NONE)
            else:
                self.sched_tile(Tiles.edge_strip, phase=90, xyz=(x,y,z), traj=self.up_rt, event=T_Evt.NONE)
        y = y_top - 3 * 1.5
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(x,y,z), traj=self.up_rt, event=T_Evt.SOUTH)

    def right_edge(self, y_bot):
        z = 1
        for i in range(3):
            y = y_bot + i * 1.5
            self.sched_tile(Tiles.edge_strip, phase=90, xyz=(11.5,y,z), traj=self.rt_dn, event=T_Evt.NONE)
        y = y_bot
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(10.5,y,z), traj=self.up_rt, event=T_Evt.REMOVE)

    def right_edgeX(self, y_bot):
        z = 1
        for i in range(3):
            y = y_bot + i * 1.5
            self.sched_tile(Tiles.edge_strip, phase=90, xyz=(11.5,y,z), traj=self.rt_dn, event=T_Evt.NONE)
        y = y_bot + 4
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(11.5,y,z), traj=self.rt_dn, event=T_Evt.NORTH)

    def right_edge2(self, y_bot):
        x = 11
        z = 1
        for i in range(3):
            y = y_bot + i * 1.5
            if i == 1:
                self.sched_tile(Tiles.short_strip, phase=90, xyz=(x,y,z), traj=self.lf_dn, event=T_Evt.NONE)
            else:
                self.sched_tile(Tiles.edge_strip, phase=90, xyz=(x,y,z), traj=self.lf_dn, event=T_Evt.NONE)
        y = y_bot + 3 * 1.5
        self.sched_tile(Tiles.edge_square, phase=0, xyz=(x,y,z), traj=self.lf_dn, event=T_Evt.NORTH)


class TileDispenser2(TileDispenser):
    """
    Creates a schedule of tiles to dispense for the inner tiles.
    """
    def __init__(self, top_y):
        self.schedule = deque()

        self.whole_row(top_y - 5)
        self.split_row(top_y - 6)

        self.count = 0
