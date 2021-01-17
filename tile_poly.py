from panda3d.core import *
import math


class Tile():
    """
    Create a thin (zscale reduced) tile object based on a polygonal prism,
    with the correct texture or colour, with collider nodes at the tips, and
    an optional large one (if the tile is square) at the c of g. Shape can be
    scaled (scale), and rotated (phase). The symmetric rotation specifier (sym_rot)
    was included to identify when a spinning tile could stop spinning - eg 90 degrees
    for a square tile vs 180 degrees for a rectagle and 360 degrees for a triangle,
    but is not important now that tiles are moved with a fixed orientation.
    """

    def __init__(self, pos, shape, face_color, tip_rad, p_tag="fred", zscale=0.05, name="Tile",
                 cg=[0,0], cg_rad=1, sym_rot=90, phase=0, scale=1, hopper=False):
        self.sym_rot = sym_rot
        self.phase = phase
        self.name = p_tag

        if isinstance(face_color, tuple):
            # if it is a tuple, then it is an RGBA
            self.gNode = TilePoly(shape, face_color)
            self.np = render.attachNewNode(self.gNode.node)
            self.np.setScale(scale, scale, zscale)
        else:
            # otherwise assume it is a texture string path
            white = (1, 1, 1, 1)
            self.gNode = TilePoly(shape, white)
            self.np = render.attachNewNode(self.gNode.node)
            self.np.setScale(scale, scale, zscale)
            tex1 = loader.loadTexture(face_color)
            self.np.setTexture(tex1)
        self.np.setPos(pos)
        self.np.setH(phase)

        colliderNode = CollisionNode("collider" + name)
        # Add central collider node
        if hopper:
            colliderNode.addSolid(CollisionSphere(*cg, 0, (cg_rad + tip_rad)/scale))
        # Add the satellite collision solids and location identifier nodes
        # at the corners, compensating for scale so that the collision solids
        # are the same size regardless of tile scale
        for i, corner in enumerate(shape):
            colliderNode.addSolid(CollisionSphere(*corner, 0, tip_rad/scale))
            corner_node = self.np.attachNewNode('cnr' + str(i))
            corner_node.setPos(*corner, 0)

        self.collider = self.np.attachNewNode(colliderNode)
        self.collider.setPythonTag("owner", self)
        self.collider.show()

    def corner_nodes(self):
        return sorted(self.np.findAllMatches('cnr*'), key=lambda np: np.name)


class TilePoly():
    """
    Generate a 3D solid in xyz plane from a 2D polygon in xy plane
    """

    def __init__(self, shape, face_color):
        # 2D Polygon and its 2D normals
        self.xys = shape[:]
        xy_normals = calcNormals(self.xys)

        """
        Coverage triangle indices for the top polygonal face (counter clockwise - illustrated) and
        bottom polygonal face (clockwise - not shown). Fails for some concave polygons like the cross.
    
                    .4        
                   .  \
                  .   .3
                 .  .  |                        
                . .   .2
               .. .   /
              0 --- 1
        """
        tri_top = [[0, vix + 1, vix + 2] for vix in range(len(self.xys) - 2)]
        tri_bot = [[0, vix - 1, vix - 2] for vix in range(len(self.xys), 2, -1)]

        # To hold vertex numbers belonging to the rectangular faces whose normals are xy normals
        rects = {}

        """
        Forward (counter clockwise) and back (clockwise) triangle indices for covering rectangular faces
             2 --------- 3
             |  b     f  |
             |     x     |
             |  f     b  |
             0 --------- 1
        """
        tri_fwd = [[0, 1, 3], [0, 3, 2]]
        tri_back = [[1, 0, 2], [1, 2, 3]]

        # Bottom face then top face
        zs = [-1, 1]

        # To hold vertex numbers belonging to the bottom and top faces
        polys = {}

        # All the vertex positions of the solid
        xyzs = [xy + [z] for z in zs for xy in self.xys]

        # There must be 3 separate vertices at each vertex position, each with a different normal,
        # which always points outwards from the solid
        format = GeomVertexFormat.getV3n3c4()
        vertexData = GeomVertexData('prism', format, Geom.UHStatic)
        vertexData.setNumRows(3 * len(xyzs))

        vertices = GeomVertexWriter(vertexData, 'vertex')
        normals = GeomVertexWriter(vertexData, 'normal')
        colors = GeomVertexWriter(vertexData, 'color')

        # sat is saturated 8 bits (+ 1) to use as denominator
        sat = 256
        white = (1, 1, 1, 1)
        brown = (0xa0 / sat, 0x98 / sat, 0x7c / sat, 1)

        for pos_num, xyz in enumerate(xyzs):
            edge_fwd = pos_num % len(self.xys)
            edge_back = (edge_fwd - 1) % len(self.xys)
            edge_nums = [edge_back, edge_fwd]
            for i in range(3):
                vertices.addData3f(*xyz)
                vnum = pos_num * 3 + i
                if i in [0, 1]:
                    edge_num = edge_nums[i]
                    normal = xy_normals[edge_num] + [0]
                    rects.setdefault(edge_num, []).append(vnum)
                else:
                    z_vec = xyz[2]
                    normal = [0, 0, z_vec]
                    polys.setdefault(z_vec, []).append(vnum)

                normals.addData3f(*normal)
                color = white if normal[2] == -1 else face_color
                colors.addData4f(color)

        # Store the tessellation triangles, counter clockwise from front.
        # Each vertex assigned to a triangle must have a normal vector that
        # points outwards from the triangle face, which thus determines which
        # of the 3 possible vertexes to chose at any given vertex position.
        # Each triangle's vertices should be specified in counter clockwise
        # order from the perspective of the vertices' normals (i.e. looking at the
        # outside of the face).
        primitive = GeomTriangles(Geom.UHStatic)

        # Cover the rectangular faces around the edges
        for edge_num in rects:
            # cater for wrap around back to the zeroth edge number
            tri_ix_pairs = tri_back if edge_num == (len(self.xys) - 1) else tri_fwd
            for tri_ixs in tri_ix_pairs:
                vnums = [rects[edge_num][tri_ix] for tri_ix in tri_ixs]
                primitive.addVertices(*vnums)

        # Cover the polygonal faces on the top and bottom
        for poly in polys:
            # Use clockwise indexing on the bottom (negative normal) face and
            # counter clockwise on the top (positive normal) face
            faces = tri_bot if poly < 0 else tri_top
            for tri_ixs in faces:
                vnums = [polys[poly][tri_ix] for tri_ix in tri_ixs]
                primitive.addVertices(*vnums)

        geom = Geom(vertexData)
        geom.addPrimitive(primitive)

        self.node = GeomNode('prism gnode')
        self.node.addGeom(geom)


class Vector2D():
    """
    2D working in x-y plane with z = 0
    """

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.dx = p2.x - p1.x
        self.dy = p2.y - p1.y
        self.hyp2 = self.dx * self.dx + self.dy * self.dy
        self.hyp = math.sqrt(self.hyp2)

    def norm_2D(self):
        return Vec3D(self.dy / self.hyp, -self.dx / self.hyp, 0)

    def tan_2D(self):
        return Vec3D(self.dx / self.hyp, self.dy / self.hyp, 0)

    def dist_from_2D(self, p, infinite=False):
        """ Distance of p0 from line segment or line through p1 and p2 """
        t = ((p.x - self.p1.x) * self.dx + (p.y - self.p1.y) * self.dy) / self.hyp2
        if t < 0 and not infinite:
            # closest is p1
            d2x = p.x - self.p1.x
            d2y = p.y - self.p1.y
        elif t > 1 and not infinite:
            # closest is p2
            d2x = p.x - self.p2.x
            d2y = p.y - self.p2.y
        else:
            # closest is a projection onto the line
            d2x = p.x - (self.p1.x + t * self.dx)
            d2y = p.y - (self.p1.y + t * self.dy)
        return math.sqrt(d2x * d2x + d2y * d2y)


def normal_2D(p1, p2):
    """
    2D working in x-y plane with points represented as 2 element lists.
    Mapping is y2 = p2[1], x2 = p2[0],  y1 = p1[1], x1 = p1[0]
    """
    x_diff = p2[0] - p1[0]
    y_diff = p2[1] - p1[1]
    hyp = math.sqrt(x_diff * x_diff + y_diff * y_diff)
    # right hand normal circulating counter clockwise
    return [y_diff / hyp, -x_diff / hyp]

def rotate_by_1(my_list):
    return my_list[1:] + my_list[:1]

def calcNormals(points):
    return [normal_2D(p1, p2) for p1, p2 in zip(points, rotate_by_1(points))]

if __name__ == '__main__':
    p1 = Vec3D(1, 2, 0)
    p2 = Vec3D(5, 7, 0)
    p3 = Vec3D(52, 3, 0)
    seg = Vector2D(p1, p2)
    dp3 = seg.dist_from_2D(p3)
    inf_dp3 = seg.dist_from_2D(p3, infinite=True)
    print('dp3', dp3)
    print('inf_dp3', inf_dp3)




