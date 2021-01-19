from panda3d.core import *
from mod_tiles import T_Evt


UNHIDE = True
# UNHIDE = False
DBP = True
# DBP = False


class Border_Occluder:
    def __init__(self, border_np):
        self.border_np = border_np
        self.border_tile_trace = []
        self.unoccluded_ixs = []
        self.margin_wd = 4.0
        # self.z_off = -0.05
        self.z_off = 2

    def get_tile_trace(self):
        return self.border_tile_trace

    def register_occlusion(self, to_dir, on_tile):
        corners = on_tile.corner_nodes()
        xys = [np.getPos(self.border_np) for np in corners]
        self.border_tile_trace.append(dict(to_dir=to_dir, xys=xys))
        if DBP:
            print("border_tile_trace")
            for rec in self.border_tile_trace:
                print(rec['to_dir'])
                for p in rec['xys']:
                    print(p)

    def margin_occluder(self, i0, no_tail):

        # This table is purely for deriving the notional 'to' direction from the actual 'from'
        # direction in the cases where the 'to' direction is REMOVE. eg. if the 'from' direction
        # is SOUTH and the 'to' direction is REMOVE, REMOVE is replaced by a notional EAST
        # so that the derived notional direction always follows an anti-clockwise progression.
        # This holds for margin occluders only. If the 'to' direction points in the opposite
        # direction then that indicates a requirement for an intrusion occculder instead.
        to_from_from = {T_Evt.EAST: T_Evt.NORTH,
                        T_Evt.NORTH: T_Evt.WEST,
                        T_Evt.WEST: T_Evt.SOUTH,
                        T_Evt.SOUTH: T_Evt.EAST}

        # Derives the correct ordinals to take from the corner tile based on the 'to' direction,
        # based on the assumption that a margin occluder skirts the outer edge of the border tiles
        # and we are traversing in an ant-clockwise direction. The concept of the 'tail wing' is
        # to extend the margin occluder backwards by the margin width in order to butt up to the
        # head of the previous margin occluder, while the head stops at the corner of its tile.
        # ordinals = {T_Evt.EAST: {'from':'SW', 'to':'SE'},  # south west tail wing, south east head
        #             T_Evt.NORTH: {'from':'SE', 'to':'NE'},  # south east tail wing, north east head
        #             T_Evt.WEST: {'from':'NE', 'to':'NW'},  # north east tail wing, north west head
        #             T_Evt.SOUTH: {'from':'NW', 'to':'SW'}}  # north west tail wing, south west head

        # Ordinals where the margin occluder skirts the inner edge of the border tiles, traversing
        # in an anti-clockwise direction. Alternative solution to create occluder grout line.
        ordinals = {T_Evt.EAST: {'from':'NW', 'to':'NE'},
                    T_Evt.NORTH: {'from':'SW', 'to':'NW'},
                    T_Evt.WEST: {'from':'SE', 'to':'SW'},
                    T_Evt.SOUTH: {'from':'NE', 'to':'SE'}}

        last_ix = len(self.border_tile_trace) - 1
        wrap_ix = 0 if i0 == last_ix else i0 + 1

        if DBP:
            print('---margin occluder using indices incl in range [', i0, ',', wrap_ix, ')')
            for i in [i0, wrap_ix]:
                rec = self.border_tile_trace[i]
                print(rec['to_dir'])
                for p in rec['xys']:
                    print(p)

        from_rec = self.border_tile_trace[i0]
        to_rec = self.border_tile_trace[wrap_ix]
        to_dir = to_rec['to_dir']

        if to_dir == T_Evt.REMOVE:
            from_dir = from_rec['to_dir']
            # derive to dir from from dir
            to_dir = to_from_from[from_dir]
        elif to_dir == T_Evt.START:
            # TODO Assume we always start from north west going anti-clockwise
            to_dir = T_Evt.WEST

        ordinal = ordinals[to_dir]
        start_pt = self.point_facing(from_rec['xys'], ordinal['from'])
        end_pt = self.point_facing(to_rec['xys'], ordinal['to'])

        if DBP: print('start_pt', start_pt, 'end_pt', end_pt)

        margin_stakes = self.stake_out_margin(to_dir, start_pt, end_pt, no_tail)
        if DBP:
            print('margin_stakes')
            for stake in margin_stakes: print(stake)

        occluder_name = 'margin_' + str(i0)
        occluder = CardMaker(occluder_name)
        occluder.setFrame(*margin_stakes)
        occluder_node = occluder.generate()
        occluder_nodepath = self.border_np.attachNewNode(occluder_node)

        return occluder_nodepath

    def stake_out_margin(self, to_dir, start_pt, end_pt, no_tail):
        if DBP: print(to_dir, start_pt, end_pt, no_tail)
        if to_dir == T_Evt.EAST:
            x = 0 if no_tail else -self.margin_wd
            y = -self.margin_wd
            wing_in = start_pt + Vec3(x, 0, 0)
            wing_out = start_pt + Vec3(x, y, 0)
            end_out = end_pt + Vec3(0, y, 0)
            end_in = Vec3(end_pt)
        if to_dir == T_Evt.NORTH:
            x = +self.margin_wd
            y = 0 if no_tail else -self.margin_wd
            wing_in = start_pt + Vec3(0, y, 0)
            wing_out = start_pt + Vec3(x, y, 0)
            end_out = end_pt + Vec3(x, 0, 0)
            end_in = Vec3(end_pt)
        elif to_dir == T_Evt.WEST:
            x = 0 if no_tail else self.margin_wd
            y = +self.margin_wd
            wing_in = start_pt + Vec3(x, 0, 0)
            wing_out = start_pt + Vec3(x, y, 0)
            end_out = end_pt + Vec3(0, y, 0)
            end_in = Vec3(end_pt)
        if to_dir == T_Evt.SOUTH:
            x = -self.margin_wd
            y = 0 if no_tail else self.margin_wd
            wing_in = start_pt + Vec3(0, y, 0)
            wing_out = start_pt + Vec3(x, y, 0)
            end_out = end_pt + Vec3(x, 0, 0)
            end_in = Vec3(end_pt)
        # return points in anti-clockwise order
        return [wing_in, wing_out, end_out, end_in]

    def point_facing(self, xys, ordinal_dir):
        """
        Applies to a rectilinear aligned square or rectangular tile, whose 4 corners
        can be identified by the 4 ordinal directions NW, SW, SW, SE. Selects
        and returns the appropriate corner, with a z offset so that the point floats
        above or below the tiles
        """
        if ordinal_dir in ['NW', 'SW']:
            ordinal_x = min([p.x for p in xys])
        else:
            ordinal_x = max([p.x for p in xys])
        if ordinal_dir in ['SW', 'SE']:
            ordinal_y = min([p.y for p in xys])
        else:
            ordinal_y = max([p.y for p in xys])
        # apply small z offset so occluder can occlude and not intersect tiles
        return Vec3(ordinal_x, ordinal_y, self.z_off)

    def intrusion_occluder(self, i0, matched_dir):
        # Derives the correct ordinals to take from the corner tile based on the 'to' direction,
        # based on the assumption that an intrusion occluder skirts the inner edge of the intrusion
        # border tiles and we are traversing in an anti-clockwise direction.
        # ordinals = {T_Evt.EAST: {'entry':'SE', 'exit':'SW'},
        #             T_Evt.NORTH: {'entry':'NE', 'exit':'SE'},
        #             T_Evt.WEST: {'entry':'NW', 'exit':'NE'},
        #             T_Evt.SOUTH: {'entry':'SW', 'exit':'NW'}}

        # Ordinals where the intrusion occluder skirts the outer edge of the intrusion border tiles,
        # traversing in an anti-clockwise direction. Alternative solution to create occluder grout line.
        ordinals = {T_Evt.EAST: {'entry':'NW', 'exit':'NE'},
                    T_Evt.NORTH: {'entry':'SW', 'exit':'NW'},
                    T_Evt.WEST: {'entry':'SE', 'exit':'SW'},
                    T_Evt.SOUTH: {'entry':'NE', 'exit':'SE'}}


        for j in range(i0, i0+3):
            self.unoccluded_ixs.remove(j)
        if DBP: print('---intrusion occluder using indices incl in range [', i0, ',', i0+3, ')',
                      self.unoccluded_ixs)
        occluder_name = 'intrusion_' + str(i0) + '_' + str(i0+3)
        if DBP: print(occluder_name)

        # establish the points
        intrusion_pts = []
        ordinal = ordinals[matched_dir]
        for int_ix in range(4):
            occl_rec = self.border_tile_trace[i0 + int_ix]
            ord_key = 'exit' if int_ix // 2 == 1 else 'entry'
            pt = self.point_facing(occl_rec['xys'], ordinal[ord_key])
            intrusion_pts.append(pt)

        if DBP:
            print('intrusion_pts')
            for pt in intrusion_pts:
                print(pt)

        intrusion_stakes = self.stake_out_intrusion(matched_dir, intrusion_pts)

        if DBP:
            print('intrusion_stakes')
            for stake in intrusion_stakes: print(stake)

        occluder = CardMaker(occluder_name)
        occluder.setFrame(*intrusion_stakes)
        occluder_node = occluder.generate()
        occluder_nodepath = self.border_np.attachNewNode(occluder_node)

        return occluder_nodepath

    def stake_out_intrusion(self, matched_dir, intrusion_pts):
        # apply the margin to the intrusion opening
        entry_pt = intrusion_pts[0]
        exit_pt = intrusion_pts[3]
        if matched_dir == T_Evt.EAST:
            y_min = min(entry_pt.y, exit_pt.y) - self.margin_wd
            entry_pt.y = exit_pt.y = y_min
        elif matched_dir == T_Evt.NORTH:
            x_max = max(entry_pt.x, exit_pt.x) + self.margin_wd
            entry_pt.x = exit_pt.x = x_max
        elif matched_dir == T_Evt.WEST:
            y_max = max(entry_pt.y, exit_pt.y) + self.margin_wd
            entry_pt.y = exit_pt.y = y_max
        elif matched_dir == T_Evt.SOUTH:
            x_min = min(entry_pt.x, exit_pt.x) - self.margin_wd
            entry_pt.x = exit_pt.x = x_min
        # intrusions are entered and exited in CLOCKWISE direction,
        # so we have to reverse this for the occlusion polygon
        return [exit_pt, intrusion_pts[2], intrusion_pts[1], entry_pt]

    def detect_intrusion(self):
        detected_occluder_nps = []
        # intrusion sequences, anti-clockwise only
        intr_seqs = {T_Evt.SOUTH: [T_Evt.EAST, T_Evt.SOUTH],
                     T_Evt.NORTH: [T_Evt.WEST, T_Evt.NORTH],
                     T_Evt.EAST: [T_Evt.NORTH, T_Evt.EAST],
                     T_Evt.WEST: [T_Evt.SOUTH, T_Evt.WEST]}

        poss_matched_seq = {}
        # At most 2 parallel sequences to match, not 3, because the 3rd event that completes
        # a sequence (a) results in the removal of that sequence, and (b) must never
        # simultaneously begin a new sequence.
        ix_for_seq = {0: None, 1: None}
        self.unoccluded_ixs = list(range(len(self.border_tile_trace)))
        for i, rec in enumerate(self.border_tile_trace):
            to_dir = rec['to_dir']
            if DBP: print(i, to_dir)
            # Look for in progress sequences first
            complete_ix = None
            for ix in ix_for_seq:
                if ix_for_seq[ix] is not None:
                    # A possible matched sequence is in progress
                    seq = poss_matched_seq[ix]
                    if to_dir == seq[ix_for_seq[ix]]:
                        # continued match
                        ix_for_seq[ix] += 1
                        # test seq for completion and mark it complete if achieved
                        if ix_for_seq[ix] == 2:
                            # There will only ever be one completed sequence
                            complete_ix = ix
                        if DBP: print('poss cont seq', ix, to_dir, poss_matched_seq, ix_for_seq)
                    else:
                        # aborted match attempt so clear out this aborted sequence
                        poss_matched_seq[ix] = None
                        ix_for_seq[ix] = None
                        if DBP: print('aborted del key', ix, to_dir, poss_matched_seq, ix_for_seq)
            if complete_ix is not None:
                # got a match, so clear out this matched sequence
                poss_matched_seq[complete_ix] = None
                ix_for_seq[complete_ix] = None
                if DBP: print('matched all', complete_ix, to_dir, poss_matched_seq, ix_for_seq)
                # intrusion which started 2 events back
                detected_occluder_nps.append(self.intrusion_occluder(i - 2, to_dir))
            else:
                # An event that completes a match will never simultaneously start a new seq
                # but others could. Look for slots to start a new sequence
                for ix in ix_for_seq:
                    if ix_for_seq[ix] is None:
                        if to_dir in intr_seqs:
                            poss_matched_seq[ix] = intr_seqs[to_dir]
                            ix_for_seq[ix] = 0
                            if DBP: print('poss new', ix, to_dir, poss_matched_seq, ix_for_seq)
                            # only want one slot for the new sequence
                            break
        last_ix = None
        for ix in self.unoccluded_ixs:
            no_tail = True if last_ix is not None and last_ix < ix - 1 else False
            last_ix = ix
            detected_occluder_nps.append(self.margin_occluder(ix, no_tail))
        return detected_occluder_nps