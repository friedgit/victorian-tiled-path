import sys
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from mod_duplicator import cumulative_dups
from panda3d.core import *
from direct.stdpy.pickle import Pickler, load

from mod_tiles import T_Evt, Tiles, TileDispenser, TileDispenser2
from mod_surface import Surface
from mod_border_occluder import Border_Occluder

UNHIDE = True
# UNHIDE = False
DBP = True
# DBP = False


"""
Technically:

np2 = np1.attachNewNode('abc')
is exactly equivalent to:

np2 = NodePath('abc')
np2.reparentTo(np1)
"""


class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.disableMouse() # if you leave mouse mode enabled camera position will be governed by Panda mouse control

        properties = WindowProperties()
        properties.setSize(1000, 750)
        self.win.requestProperties(properties)

        # Enable fast exit
        self.accept("escape", sys.exit)

        self.mm_per_unit = 75
        self.grout_wd = 0.05
        self.grout_wd = 2.5 / self.mm_per_unit

        self.flung_tile, self.trajectory, self.use_short_cushion, self.event = (None, None, None, None)

        self.top_limit = 22

        self.setup_lighting()

        intr_top = 16/3
        intr_ht = 23/3 - 0.1
        self.floor = Surface(1350 / self.mm_per_unit, self.top_limit,
                             self.grout_wd, Tiles.tip_rad)
        self.border_tiles_np = self.render.attachNewNode("border")
        self.bord_occl = Border_Occluder(self.border_tiles_np)
        self.inner_tiles_np = self.render.attachNewNode("inner")

        self.pusher = CollisionHandlerPusher()
        self.cTrav = CollisionTraverser()
        self.cTrav.setRespectPrevTransform(True)

        self.pusher.addInPattern('into')

        # Accept the events sent by the collisions.
        self.accept('into', self.ouch)

        self.count_threshold = 50
        self.veloc_attn_ratio = 0.94  # minimum that works for tile13

        self.border_tile_nps = []
        self.inner_tile_nps = []

        # self.lastTime = 0
        self.init_new_sched()

        self.keyMap = {"west": False, "east": False, "north": False, "south": False}

        # Try to reopen the file
        try:
            input = open('zoo.pkl', 'rb')
            # input = open('zoo-not.pkl', 'rb')

            # Loading from pickle, so do not stash
            self.stash = False
        except:
            # Stashing to pickle after tiling from scratch
            self.stash = True

        if not self.stash:
            # Load the pickled data into the relevant lists / dicts
            self.load_layout(input)
        else:
            self.taskMgr.add(self.spinPrismTask, "spinPrismTask", extraArgs=[
                TileDispenser(self.top_limit), self.border_tile_nps, None],
                             appendTask=True, uponDeath=self.lay_inner_tiles)
        self.re_enable_mouse_camera()
        # self.lift_border()
        self.activate_shifting(None)

    def re_enable_mouse_camera(self):
        mat = Mat4(camera.getMat())
        mat.invertInPlace()
        base.mouseInterfaceNode.setMat(mat)
        base.enableMouse()

    def init_new_sched(self):
        self.hit_count = 0
        self.trigger = True
        self.sunk = False
        self.count_down = self.count_threshold
        self.hit_bottom_row = False

    def lift_border(self):
        # This step is required to make the pickled tiles appear
        for tile in self.border_tile_nps:
            tile.reparentTo(self.border_tiles_np)

        # height = 0.01
        height = 1
        self.border_tiles_np.setZ(self.border_tiles_np.getZ() + height)

    def lay_inner_tiles(self, task):
        self.lift_border()

        self.init_new_sched()
        self.taskMgr.add(self.spinPrismTask, "spinPrismTask", extraArgs=[
            TileDispenser2(self.top_limit), self.inner_tile_nps, cumulative_dups],
                         appendTask=True, uponDeath=self.activate_shifting)

    def activate_shifting(self, task):
        if self.stash:
            self.stash_layout()

        # self.lift_border()

        # This step is required to make the tiles shiftable
        for tile in self.inner_tile_nps:
            tile.reparentTo(self.inner_tiles_np)

        self.taskMgr.add(self.move, "moveTask")
        self.accept_arrow_keys()

    def load_layout(self, input):
        tiled_floor = load(input)

        self.floor = tiled_floor['floor']

        self.border_tile_nps = tiled_floor['border_tiles']
        for tile in self.border_tile_nps:
            tile.reparentTo(self.border_tiles_np)

        self.inner_tile_nps = tiled_floor['inner_tiles']
        for tile in self.inner_tile_nps:
            tile.reparentTo(self.inner_tiles_np)

        self.bord_occl.border_tile_trace = tiled_floor['border_tile_trace']
        self.detected_occluder_nps = self.bord_occl.detect_intrusion()

    def stash_layout(self):
        output = open('zoo.pkl', 'wb')
        p = Pickler(output)

        tiled_floor = dict(floor=self.floor,
                           inner_tiles=self.inner_tile_nps,
                           border_tiles=self.border_tile_nps,
                           border_tile_trace=self.bord_occl.get_tile_trace())
        p.dump(tiled_floor)

        output.close()

    def setup_lighting(self):
        # Add a simple point light
        plight = PointLight('plight')
        plight.setColor(VBase4(0.5, 0.5, 0.5, 1))
        plnp = self.render.attachNewNode(plight)
        plnp.setPos(4, -4, 4)
        self.render.setLight(plnp)

        # Add an ambient light
        alight = AmbientLight('alight')
        alight.setColor(VBase4(0.2, 0.2, 0.2, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)
        self.render.setShaderAuto()

        # Move camera for a better view
        self.camera.setPos(7, -14, 22)
        # self.camera.setPos(5, -33, 50)
        self.camera.setP(-45)
        self.zoomIn()

    def accept_arrow_keys(self):
        # Accept the control keys for movement
        self.accept("arrow_left", self.setKey, ["west", True])
        self.accept("arrow_right", self.setKey, ["east", True])
        self.accept("arrow_up", self.setKey, ["north", True])
        self.accept("arrow_down", self.setKey, ["south", True])
        self.accept("arrow_left-up", self.setKey, ["west", False])
        self.accept("arrow_right-up", self.setKey, ["east", False])
        self.accept("arrow_up-up", self.setKey, ["north", False])
        self.accept("arrow_down-up", self.setKey, ["south", False])

    def move(self, task):
        dt = globalClock.getDt()
        delta = 2
        if self.keyMap["west"]:
            self.inner_tiles_np.setX(self.inner_tiles_np.getX() - delta * dt)
        if self.keyMap["east"]:
            self.inner_tiles_np.setX(self.inner_tiles_np.getX() + delta * dt)
        if self.keyMap["north"]:
            self.inner_tiles_np.setY(self.inner_tiles_np.getY() + delta * dt)
        if self.keyMap["south"]:
            self.inner_tiles_np.setY(self.inner_tiles_np.getY() - delta * dt)
        return Task.cont

    # Records the state of the arrow keys
    def setKey(self, key, value):
        self.keyMap[key] = value

    def ouch(self, collEntry):
        tile_name = collEntry.getFromNodePath().getPythonTag("owner").name
        tile_num = int(tile_name.split("tile")[1])

        if DBP: print(tile_name, tile_num, self.hit_threshold)
        if DBP:
            if collEntry.getIntoNodePath().hasPythonTag("owner"):
                print(collEntry.getIntoNodePath().getPythonTag("owner").name)
        if DBP: print('hit by', collEntry, 'solid', collEntry.getFrom())

        if self.trajectory:
            self.velocity = self.trajectory.pop(0)
        self.hit_count += 1

    def zoomIn(self):
        self.camera.setPos(9, 16, 40)
        self.camera.setP(-90)

    def zoomOut(self):
        self.camera.setPos(1, 0, 80)
        self.camera.setP(-90)

    def spinPrismTask(self, tile_dispatcher, settled_tile_nps, duplicator, task):
        # Appears to be called 60 times a second
        print('flung_tile', self.flung_tile)

        # Initialise, within the cyclic task, not within MyApp's __init__, otherwise the initial position
        # of the first tile gets pickled, as well as its final position
        if not self.flung_tile:
            self.flung_tile, self.trajectory, self.use_short_cushion, self.event = tile_dispatcher.popup()

            # Both of these required to stop tile going through the side
            base.pusher.addCollider(self.flung_tile.collider, self.flung_tile.np)
            base.cTrav.addCollider(self.flung_tile.collider, self.pusher)

            # hit threshold before deceleration starts depends on number of velocity changes
            self.hit_threshold = len(self.trajectory)

            # Velocity defined in units per frame intervals (of 1 /60 th second)
            self.velocity = self.trajectory.pop(0)

        low_z = 0
        # if DBP: print('set velocity 1', self.velocity)
        new_pos = self.flung_tile.np.getPos() + self.velocity
        # if DBP: print('new position', new_pos)
        if new_pos.getZ() <= low_z or self.sunk:
            # stopped sinking
            new_pos.setZ(low_z)
            self.sunk = True
            self.velocity.setZ(low_z)

        if DBP: print('AAA')
        # may have stopped sinking
        if self.hit_count < self.hit_threshold:
            if DBP: print('--B')
            self.flung_tile.np.setFluidPos(new_pos)
            if DBP: print('set position', self.flung_tile.np.getPos())
            if DBP: print('set velocity', self.velocity)
        else:
            if DBP: print('BBB')
            if self.trigger:
                if DBP: print('CCC')
                # keep updating pos
                self.flung_tile.np.setFluidPos(new_pos)
                if DBP: print('got position', self.flung_tile.np.getPos())
                if DBP: print('got velocity', self.velocity)
                if self.count_down > 0:
                    if DBP: print('DDD')
                    self.count_down -= 1
                    self.velocity = self.velocity * self.veloc_attn_ratio
                else:
                    if DBP: print('--D')
                    self.trigger = False
            else:
                if DBP: print('--C')
                # first tile settled
                if DBP: print('tile has arrived and settled')
                # remove flung tile's tile collider
                self.flung_tile.collider.node().clearSolids()
                base.cTrav.removeCollider(self.flung_tile.collider)

                settled_tile_nps.append(self.flung_tile.np)

                if self.event != T_Evt.NONE:
                    if not duplicator:
                        # no duplicator implies intrusions
                        self.bord_occl.register_occlusion(self.event, self.flung_tile)
                    if self.event == T_Evt.REMOVE:
                        self.floor.remove_last_attached()
                    elif self.event == T_Evt.START:
                        pass
                    else:
                        self.floor.internal_border(self.event, self.flung_tile)

                # clip wall length if hit bottom row
                self.floor.tile_wall(self.flung_tile, self.use_short_cushion)

                if tile_dispatcher.tiles_left():
                    if DBP: print('EEE')
                    self.flung_tile, self.trajectory, self.use_short_cushion, self.event = tile_dispatcher.popup()
                    if DBP: print('initial heading', self.flung_tile.np.getH())

                    base.pusher.addCollider(self.flung_tile.collider, self.flung_tile.np)
                    base.cTrav.addCollider(self.flung_tile.collider, self.pusher)

                    self.hit_count = 0
                    self.trigger = True
                    self.sunk = False
                    self.count_down = self.count_threshold
                    # hit threshold before deceleration starts depends on number of velocity changes
                    self.hit_threshold = len(self.trajectory)
                    self.velocity = self.trajectory.pop(0)
                else:
                    if DBP: print('--E')
                    if DBP: print('all tiles have arrived')
                    # self.zoomIn()
                    if DBP: self.floor.gut_collision_nodes()
                    if duplicator:
                        duplicator(settled_tile_nps)
                    else:
                        pass
                        # There's no duplicator for border tiles but there are intrusions
                        self.detected_occluder_nps = self.bord_occl.detect_intrusion()
                        pass

                    self.flung_tile = None
                    return Task.done

        return Task.cont


app = MyApp()
app.run()