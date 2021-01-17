"""
Functions used to duplicate a group of tiles with inter-group spacing the same
as the inter-tile spcing within the group.
"""

import math

# from mod_key_move import DBP
from mod_tiles import T_Evt


DBP = True
# DBP = False


def coord_fn(point, shift_dir, aligned):
    """
    Sort function which orders 2D property (tile position) in a 1D linear order
    according to the desired shift direction, and whether or not the tiles are
    aligned in the shift direction.
    """
    if shift_dir in [T_Evt.SOUTH, T_Evt.NORTH]:
        if aligned:
            return point.y
        else:
            return point.x
    elif shift_dir in [T_Evt.EAST, T_Evt.WEST]:
        if aligned:
            return point.x
        else:
            return point.y
    assert('Invalid shift direction')


def calc_repeat_shift(shift_dir, settled_tile_nps):
    """
    Calculates the shift to apply to a group of tiles in the desired direction,
    North, South, East, or West
    Able to work both with groups which are aligned in the shift direction, like this
    [ ][ ][ ]
    [ ][ ][ ]
    or not aligned, but in a diamond pattern, like this
    X  X  X  X
     X  X  X  X
    """
    rvs_sort = False if shift_dir in [T_Evt.SOUTH, T_Evt.WEST] else True

    shift_aligned = sorted(settled_tile_nps,
                           key=lambda tile: coord_fn(tile.getPos(), shift_dir, aligned=False),
                           reverse=rvs_sort)

    grid_rank_list = []
    matched_rank_ix = None
    final_rank_ix = None
    last_tile_sort = None
    close_sort_ix = None
    # There are two types of search going on in this loop. The first is just
    # a close grouped sequence where the tiles start off all aligned in the
    # shift direction. If that is observed it takes priority and the loop
    # breaks as soon as the alignment ceases. The second is where they're
    # never aligned in the shift direction but typically zig-zag. Then the
    # loop breaks when a tile is found whose co-ordinate in the shift
    # direction, its grid_rank, matches an earlier tile.
    for i, tile in enumerate(shift_aligned):
        if DBP: print(i, tile.getPos())

        # Search for close grouped sequence
        tile_sort = coord_fn(tile.getPos(), shift_dir, aligned=False)
        if last_tile_sort is not None:
            if math.isclose(tile_sort, last_tile_sort, abs_tol=1e-02):
                # Looking for a close grouped sequence at the start
                close_sort_ix = i
            else:
                if close_sort_ix is not None:
                    # A close grouped sequence began but has now terminated.
                    # If it exists then this takes priority and we stop looking
                    # for a matched rank.
                    break
        last_tile_sort = tile_sort

        # Search for matching grid rank
        tile_rank = coord_fn(tile.getPos(), shift_dir, aligned=True)
        for rank_ix, rank in enumerate(grid_rank_list):
            if DBP: print(rank_ix, rank, tile_rank, matched_rank_ix, grid_rank_list)
            if math.isclose(tile_rank, rank, abs_tol=1e-02):
                matched_rank_ix = rank_ix
                break
        grid_rank_list.append(tile_rank)
        if matched_rank_ix is not None:
            final_rank_ix = i
            break

    if close_sort_ix is not None:
        # Just use the in-line points in the initial close grouped sequence
        # which should pre-empt any matching grid rank
        final_rank_ix = close_sort_ix + 1
        matched_rank_ix = 0

    # We expect to terminate on one or the other types of search
    reduced_aligned = shift_aligned[:final_rank_ix]

    # Order the points so we can create a chain of consecutive vectors whose sum,
    # head to toe, amounts to the last point minus the first point
    rear_most = sorted(reduced_aligned,
                       key=lambda tile: coord_fn(tile.getPos(), shift_dir, aligned=True),
                       reverse=(not rvs_sort))
    if DBP:
        print('first', rear_most[0].getPos())
        print('last', rear_most[-1].getPos())
        print('matched', shift_aligned[final_rank_ix].getPos())
        print('common', rear_most[matched_rank_ix + 1].getPos())

    # Generate a preliminary shift vector in the desired direction
    forward = rear_most[-1].getPos() - rear_most[0].getPos()
    # Test if it is aligned to the shift direction
    if math.isclose(coord_fn(forward, shift_dir, aligned=False), 0.0, abs_tol=1e-02):
        # rectilinear pattern, or in-line diagonals: ignore matched point
        matched_origin = rear_most[matched_rank_ix].getPos()
    else:
        # non-rectilinear, probably diagonal: use matched point
        matched_origin = shift_aligned[final_rank_ix].getPos()
    common = rear_most[matched_rank_ix + 1].getPos()
    delta = common - matched_origin
    shift = forward + delta
    return shift


def repeat_tiles(num_times, dir, settled_tile_nps):
    """
    Duplicates a group of tiles num_times over in direction dir.
    """
    shift = calc_repeat_shift(dir, settled_tile_nps)
    print('shift', shift)
    repeated_tiles = []
    for tile in settled_tile_nps:
        for i in range(num_times):
            copy_np = tile.copyTo(render)
            tile_pos = tile.getPos()
            copy_np.setPos(tile_pos + shift * (i+1))
            repeated_tiles.append(copy_np)
    return repeated_tiles


def cumulative_dups(settled_tile_nps):
    """
    Duplicates the group settled_tile_nps 1 times to the East to form a new
    group which itself is then duplicated 8 times to the South. Hence the
    original supplied group is duplicated a total of (1 + 1) x (1 + 8) = 18
    times.
    """
    repeated_tile_nps = repeat_tiles(1, T_Evt.EAST, settled_tile_nps)
    settled_tile_nps.extend(repeated_tile_nps)
    repeated_tile_nps = repeat_tiles(8, T_Evt.SOUTH, settled_tile_nps)
    settled_tile_nps.extend(repeated_tile_nps)