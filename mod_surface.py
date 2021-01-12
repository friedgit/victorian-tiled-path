from panda3d.core import *
from itertools import product


# from mod_border_occluder import Border_Occluder
from mod_tiles import T_Evt
import tile_poly as tile

UNHIDE = True
# UNHIDE = False
DBP = True
# DBP = False


class Surface:
    def __init__(self, x1, y1,
                 grout_wd, tip_rad):
        # Path to front door
        self.x0 = 0
        self.x1 = x1
        self.y0 = 0
        self.y1 = y1
        self.grout_wd = grout_wd
        self.tip_rad = tip_rad

        self.movable_np = render.attachNewNode("movable")
        self.last_attached_node = None

        # Add cushions to movable
        self.cushion_rad = 0.2
        # projection is negative so really an indentation
        projection = self.grout_wd - self.tip_rad
        self.offset = self.cushion_rad - projection

        # top end only of concrete path
        for y in [self.y1 + self.offset]:
            wallSolid = CollisionTube(self.x0, y, 0, self.x1, y, 0, self.cushion_rad)
            wallNode = CollisionNode("path_end")
            wallNode.addSolid(wallSolid)
            wall = self.movable_np.attachNewNode(wallNode)
            if UNHIDE: wall.show()

        # left border only of concrete path
        for x in [self.x0 - self.offset]:
            wallSolid = CollisionTube(x, self.y0, 0, x, self.y1, 0, self.cushion_rad)
            wallNode = CollisionNode("path_bord")
            wallNode.addSolid(wallSolid)
            wall = self.movable_np.attachNewNode(wallNode)
            if UNHIDE: wall.show()

        self.concrete_base()

    def concrete_base(self):
        # Create a (vertical) card whose dimensions are ((x1-x0), (y1-y0))
        cm = CardMaker('card')
        cm.setFrame(self.x0, self.x1, self.y0, self.y1)
        cm_node = cm.generate()
        self.floor_np = render.attachNewNode(cm_node)

        # apply concrete texture, scaled down and repeated
        tex = loader.loadTexture("tex/cement.jpg")
        self.floor_np.setTexture(tex)
        ts = TextureStage.getDefault()
        tex_scale = 4
        xtex = tex_scale * (self.x1 - self.x0)
        ytex = tex_scale * (self.y1 - self.y0)
        self.floor_np.setTexScale(ts, xtex, ytex)

        # Rotate card downwards from vertical to horizontal
        self.floor_np.setHpr(0, -90.0, -0)

    def internal_border(self, to_dir, on_tile):
        corners = on_tile.corner_nodes()
        xys = [np.getPos(self.movable_np) for np in corners]
        # Reverse the offset if defending a point
        point_events = [T_Evt.EA_PT, T_Evt.WE_PT, T_Evt.NO_PT, T_Evt.SO_PT]
        offset = -self.offset if to_dir in point_events else self.offset
        if to_dir in [T_Evt.EAST, T_Evt.EA_PT]:
            x = max([p.x for p in xys]) + self.grout_wd + offset
            wallSolid = CollisionTube(x, self.y0, 0, x, self.y1, 0, self.cushion_rad)
        elif to_dir in [T_Evt.WEST, T_Evt.WE_PT]:
            x = min([p.x for p in xys]) - self.grout_wd - offset
            wallSolid = CollisionTube(x, self.y0, 0, x, self.y1, 0, self.cushion_rad)
        elif to_dir in [T_Evt.NORTH, T_Evt.WE_PT]:
            y = max([p.y for p in xys]) + self.grout_wd + offset
            wallSolid = CollisionTube(self.x0, y, 0, self.x1, y, 0, self.cushion_rad)
        elif to_dir in [T_Evt.SOUTH, T_Evt.SO_PT]:
            y = min([p.y for p in xys]) - self.grout_wd - offset
            wallSolid = CollisionTube(self.x0, y, 0, self.x1, y, 0, self.cushion_rad)
        wallNode = CollisionNode("path_internal")
        wallNode.addSolid(wallSolid)
        wall = self.movable_np.attachNewNode(wallNode)
        self.remove_last_attached()
        self.last_attached_node = wall
        if UNHIDE: wall.show()

    def remove_last_attached(self):
        if self.last_attached_node:
            self.last_attached_node.node().clearSolids()
            self.last_attached_node.clear()

    def collision_nodes(self):
        """ for debug """
        print('called')
        collision_nodeCollection = self.movable_np.findAllMatches('*')
        for nodePath in collision_nodeCollection:
            print('a node')
            collision_node = nodePath.node()
            print(collision_node.name)
            # there is at most one solid per collision node
            solids = collision_node.getSolids()
            if solids:
                solid = solids[0]
                print(solid)
                print(solid.point_a, solid.point_b)

    def gut_collision_nodes(self):
        collision_nodeCollection = self.movable_np.findAllMatches('path_[ti]*')
        for nodePath in collision_nodeCollection:
            collision_node = nodePath.node()
            collision_node.clearSolids()

    def intrusion(self, x0, x1, y0, y1):
        cm = CardMaker('intrusion')
        cm.setFrame(x0, x1, y0, y1)  # card dimensions are ((x1-x0), (y1-y0))
        cm_node = cm.generate()
        self.intr_np = render.attachNewNode(cm_node)
        overlay_thickness = 0.001
        self.intr_np.setPos(0, 0, overlay_thickness)
        self.intr_np.setHpr(0, -90.0, -0)
        xys2 = list(product([x0, x1], [y0, y1]))
        # rearrange points in anti-clockwise cyclic order
        xy_ac = [xys2[0], xys2[2], xys2[3], xys2[1]]
        xys = [Vec3(*xy, 0) for xy in xy_ac]
        print('intru', xys)
        self.prism_wall(xys, False)

    def embraced(self, point, vec, closeness):
        dist = vec.dist_from_2D(point)
        return abs(dist) < closeness

    def collinear(self, vec1, vec2, closeness):
        d1 = vec1.dist_from_2D(vec2.p1, infinite=True)
        d2 = vec1.dist_from_2D(vec2.p2, infinite=True)
        return abs(d1) < closeness and abs(d2) < closeness

    def tile_wall(self, flung_tile, clipped):
        # Get the floor based locations of all the corner nodes of the tile after it has settled
        corners = flung_tile.corner_nodes()
        xys = [np.getPos(self.movable_np) for np in corners]
        if DBP: print('xxx', xys)
        self.prism_wall(xys, clipped)

    def prism_wall(self, xys, clipped):
        closeness_tol = 0.3

        collision_cylinders = []
        collision_nodeCollection = self.movable_np.findAllMatches('path*')
        for nodePath in collision_nodeCollection:
            collision_node = nodePath.node()
            solids = collision_node.getSolids()
            if solids:
                # At most one collision solid per node
                solid = solids[0]
                collision_cylinders.append(dict(
                    vec=tile.Vector2D(solid.point_a, solid.point_b), radius=solid.radius))
        if DBP: print(collision_cylinders)

        # First we build up lists of sets identifying the (up to 2) cylinders which
        # embrace the p1s and p2s of the line segments of the tile edges.
        # Note p2 of a preceding segment is the same as p1 of its succeeding segment.
        p1_embs = []
        p2_embs = []
        for i, (p1, p2) in enumerate(zip(xys, tile.rotate_by_1(xys))):

            # Start with empty sets for the p1 and p2 of this segment, then append
            # an index to any collision cylinder which embraces the p1 and then the p2
            p1_embs.append(set())
            p2_embs.append(set())
            for j, cyl in enumerate(collision_cylinders):
                closeness = cyl['radius'] + closeness_tol
                if self.embraced(p1, cyl['vec'], closeness):
                    p1_embs[i].add(j)
                if self.embraced(p2, cyl['vec'], closeness):
                    p2_embs[i].add(j)

            # Test for intersections in the 2 sets of cylinders which embrace p1 and
            # p2 for this segment. If there are no intersections, then the segment
            # is exposed to collisions from any subsequently arriving tile, and
            # so requires a new cushion to protect it.
            if DBP: print("p1_embs[i]", p1_embs[i])
            if DBP: print("p2_embs[i]", p2_embs[i])
            if not(p1_embs[i] & p2_embs[i]):
                # No intersections of cylinders embracing p1 and p2 but
                # still need to test if any of the cylinders in the p1 set are
                # collinear with any of the cylinders in the p2 set
                any_collinear = False
                for pair in product(p1_embs[i], p2_embs[i]):
                    any_collinear = any_collinear or self.collinear(collision_cylinders[pair[0]]['vec'],
                                                                    collision_cylinders[pair[1]]['vec'],
                                                                    closeness=0.1)
                if not any_collinear:
                    # need a new cushion for this segment
                    if DBP: print('seg', i, p1, p2)
                    seg = tile.Vector2D(p1, p2)
                    norm = seg.norm_2D()
                    tan = seg.tan_2D()
                    if DBP: print('new normals x y', norm.x, norm.y)
                    # pull back in opposite direction to normal
                    q1x = p1.x - norm.x * self.offset
                    q1y = p1.y - norm.y * self.offset
                    q2x = p2.x - norm.x * self.offset
                    q2y = p2.y - norm.y * self.offset
                    # trim length if exposed or clipped
                    if not p1_embs[i] or clipped:
                        q1x += tan.x * self.offset
                        q1y += tan.y * self.offset
                    if not p2_embs[i] or clipped:
                        q2x -= tan.x * self.offset
                        q2y -= tan.y * self.offset

                    wallSolid = CollisionTube(q1x, q1y, p1.z, q2x, q2y, p2.z, self.cushion_rad)
                    wallNode = CollisionNode("path_tile")
                    wallNode.addSolid(wallSolid)
                    wall = self.movable_np.attachNewNode(wallNode)
                    if UNHIDE: wall.show()
