#%%
from math import ceil

import pyvista as pv


def get_pv_manifold_shape(container_name, data_dir="../../data"):
    """Returns the container from a string"""
    if container_name == "cube":
        return pv.Cube().triangulate()
    elif container_name == "sphere":
        return pv.Sphere().triangulate()
    elif container_name == "cylinder":
        raise NotImplementedError('Cylinder is not a manifold shape. If you know how to make it manifold, please implement it and submit a pull request.')
        # return pv.Cylinder().triangulate()
    elif container_name == "tetrahedron":
        return pv.Tetrahedron()
    elif container_name == "cone":
        return pv.Cone().triangulate()
    elif container_name == "rbc_normal":
        return pv.read(f"{data_dir}/mesh/RBC_normal.stl")
    elif container_name == "sickle_red_blood_cell":
        return pv.read(f"{data_dir}/mesh/sickleCell.stl")
    else:
        raise ValueError(f"Shape {container_name} not found")

ALL_SHAPES = ["cube", "sphere", "cylinder", "tetrahedron", "cone", "rbc_normal", "sickle_red_blood_cell"]


def capped_cylinder(radius=0.5, height=1, center=(0, 0, 0), direction=(0, 0, 1), resolution=10):
    cylinder = pv.CylinderStructured(center=(0.0, 0.0, 0.0), theta_resolution=resolution, z_resolution=5, direction=direction,
                           radius=radius, height=height).cast_to_unstructured_grid()

    # create the caps (disks)
    cap_bottom = pv.Disc(center=(0.0, 0.0, -height/2),
                         inner=0, outer=radius,
                         normal=(0, 0, 1), r_res=ceil(resolution/2), c_res=resolution)

    cap_top = pv.Disc(center=(0.0, 0.0, height/2),
                      inner=0, outer=radius,

                      normal=(0, 0, -1), r_res=ceil(resolution/2), c_res=resolution)

    cylinder.merge(cap_bottom, inplace=True, merge_points=False)
    cylinder.merge(cap_top, inplace=True, merge_points=False)
    cylinder  = cylinder.cast_to_unstructured_grid().extract_surface().triangulate()

    # Still not manifold

    return cylinder


# %%
