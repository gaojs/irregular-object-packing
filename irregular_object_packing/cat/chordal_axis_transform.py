"""In step 4.2.1 of the algorithm in [Ma et al.

2018], The CAT is computed by using the following steps:
1. Create a Tetrahedron Mesh from all the points on the surface mesh of both the objects and the container as the input points.
2. Use onlty those tetrahedrons that constructed of points from multiple objects.
3. Compute the chordal axis of each tetrahedron.
4. Compute the chordal axis of the whole object by taking the union of all the chordal axis of the tetrahedrons.
"""
# %%

# %%
import io
from contextlib import redirect_stdout

import numpy as np
import pyvista as pv
import tetgen

from irregular_object_packing.cat.tetra_cell import TetraCell
from irregular_object_packing.cat.utils import (
    create_face_normal,
    get_cell_arrays,
    n_related_objects,
)

CDT_DEFAULTS = {
    # "nobisect": True,
    "steinerleft": 0,
    "mindihedral": 0,
    "minratio": 10.0,
    "quality": False,
    "cdt": True,
    "switches": "O0/0Q",
}


def compute_cdt(meshes: list[pv.PolyData], tetgen_kwargs=None) -> pv.UnstructuredGrid:
    """Compute the constrained Delaunay triangulation of the meshes

    Args:
        meshes (list[pv.PolyData]): list of meshes

    Returns:
        pv.PolyData: constrained Delaunay triangulation
    """
    tetgen_kwargs = tetgen_kwargs or CDT_DEFAULTS
    mesh_sum = pv.PolyData()
    for mesh in meshes:
        mesh_sum.merge(mesh, merge_points=False, inplace=True)

    # mitigate the annoying output of tetgen generated by the -D flag
    f = io.StringIO()
    with redirect_stdout(f):
        mesh = tetgen.TetGen(mesh_sum)
        mesh.tetrahedralize(order=1, **tetgen_kwargs)

    return mesh.grid

def split_and_process(cell: TetraCell, tetmesh_points: np.ndarray, normals: list[list[np.ndarray]], cat_cells: list[list[np.ndarray]], normals_per_points):
    """Splits the cell into faces and processes them."""
    # 0. split the cell into faces
    split_faces = cell.split(tetmesh_points)
    # FIXME: Bug for larger object
    added_objs = []
    for i, faces in enumerate(split_faces):

        obj_id = cell.objs[i]
        obj_point = tetmesh_points[cell.points[i]]
        obj_covered = obj_id in added_objs

        for face in faces:
            face_normal = create_face_normal(np.ascontiguousarray(face[:3]), np.ascontiguousarray(obj_point))
            normals[obj_id].append(face_normal)
            normals_per_points[cell.points[i]].append(face_normal)

            if not obj_covered:
                cat_cells[obj_id].append(face)

        if not obj_covered:
            added_objs.append(obj_id)


def filter_relevant_cells(cells: list[int], objects_npoints: list[int]):
    """Filter out cells that only belong to a single object.

    parameters:
    cells (ndarray): an array of shape (n_cells, 4) with the indices of the points in the cell. shape: [id0, id1, id2, id3]
    objects_npoints (List[int]): A list of the number of points for each object.
    """
    relevant_cells: list[TetraCell] = []
    skipped_cells = []

    for i, cell in enumerate(cells):
        rel_objs = n_related_objects(objects_npoints, cell=cell)
        cell = TetraCell(cell, rel_objs, i)
        if cell.nobjs == 1:
            skipped_cells.append(cell)
        else:
            relevant_cells.append(cell)

    return relevant_cells, skipped_cells


def process_cells_to_normals(tetmesh_points: np.ndarray, rel_cells: list[TetraCell], n_objs: int) -> tuple[list[np.ndarray], list[np.ndarray]]:
    # initialize face normals list
    face_normals = []
    for _i in range(n_objs):
        face_normals.append([])

    face_normals_pp = []
    for _i in range(len(tetmesh_points)):
        face_normals_pp.append([])

    # initialize cat cells list
    cat_cells = []
    for _i in range(n_objs):
        cat_cells.append([])

    for cell in rel_cells:
        # mutates face_normals and cat_cells
        split_and_process(cell, tetmesh_points, face_normals, cat_cells, face_normals_pp)

    return face_normals, cat_cells, face_normals_pp

def compute_cat_faces(tetmesh: pv.UnstructuredGrid, npoints_per_object, obj_coords: list[np.ndarray]) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Compute the CAT faces of the objects in the list and the container. The n_points_per_object is a list of the number of points for each object and should be added in the same order as the objects provided to the compute_cdt() function."""

    # assert (tetmesh.celltypes == 10).all(), "Tetmesh must be of type tetrahedron"
    # [ ] TODO: add the obj_coords substraction to the computation here so that the optimisation becomes easier

    # filter tetrahedron mesh to only contain tetrahedrons with points from more than one object
    cells = get_cell_arrays(tetmesh.cells)

    rel_cells, _ = filter_relevant_cells(cells, npoints_per_object)

    face_normals, cat_cells, normalspp = process_cells_to_normals(tetmesh.points, rel_cells, len(npoints_per_object))

    return face_normals, cat_cells, normalspp
def compute_cat_cells(
    object_meshes: list[pv.PolyData],
    container: pv.PolyData,
    obj_coords: list[np.ndarray],
    tetgen_kwargs: dict,
):
    """Compute the CAT cells of the objects in the list and the container. First a
    Tetrahedral mesh is created from the pointcloud of all the objects points and the
    container points. Then, for each tetrahedron that has points from at least 2
    different objects, the faces of the CAT mesh are computed.

    Args:
        - object_points_list: a list of point clouds which define the surface meshes of the objects
        - container_points: a point cloud of surface mesh of the container

    Returns:
        - dictionary of the CAT cells for each object.
    """

    tetmesh = compute_cdt(object_meshes + [container], tetgen_kwargs)

    # The point sets are sets(uniques) of tuples (x,y,z) for each object, for quick lookup
    # NOTE: Each set in the list might contain points from different objects.
    obj_point_sets = [set(map(tuple, obj.points)) for obj in object_meshes] + [
        set(map(tuple, container.points))
    ]

    # Each cat cell is a list of faces, each face is a list of points
    compute_cat_faces(tetmesh, obj_point_sets, obj_coords)

    del tetmesh

# %%
