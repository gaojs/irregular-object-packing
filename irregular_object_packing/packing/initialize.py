"""Initialization phase of the packing algorithm."""
# %%
from typing import List

import numpy as np
import trimesh
from pyvista import PolyData, StructuredGrid
from scipy.optimize import minimize
from scipy.spatial import Voronoi

from irregular_object_packing.mesh.utils import pyvista_to_trimesh


def random_coordinate_within_bounds(bounding_box: np.ndarray) -> np.ndarray:
    """Generates a random coordinate within the bounds of the bounding box."""
    x = np.random.uniform(bounding_box[0][0], bounding_box[1][0])
    y = np.random.uniform(bounding_box[0][1], bounding_box[1][1])
    z = np.random.uniform(bounding_box[0][2], bounding_box[1][2])
    random_positions = np.array((x, y, z))
    return random_positions


# def random_coordinate_within_bounds(bounding_box: np.ndarray, N=1000) -> np.ndarray:
#     """generates a random coordinate within the bounds of the bounding box"""
#     x = np.random.uniform(bounding_box[0][0], bounding_box[1][0], N)
#     y = np.random.uniform(bounding_box[0][1], bounding_box[1][1], N)
#     z = np.random.uniform(bounding_box[0][2], bounding_box[1][2], N)
#     random_positions = np.array((x, y, z)).reshape(N, 3)
#     return random_positions


def get_min_bounding_mesh(mesh: PolyData) -> PolyData:
    """Selects one of 'Box', 'Sphere' or 'Cylinder' bounding mesh of mesh that has the
    smallest volume.

    Args:
        mesh (PolyData): original mesh

    Returns:
        PolyData: bounding mesh
    """
    options = [mesh.bounding_box_oriented, mesh.bounding_sphere, mesh.bounding_cylinder]
    volume_min = np.argmin([i.volume for i in options])
    bounding_mesh = options[volume_min]
    return bounding_mesh


def get_max_radius(mesh: PolyData) -> float:
    """Returns the maximum distence from the center of mass to the mesh points.

    Args:
        mesh (PolyData): original mesh

    Returns:
        float: maximum dimension
    """
    distances = np.linalg.norm(mesh.points - mesh.center_of_mass(), axis=1)
    max_distance = np.max(distances)
    return max_distance


def init_coordinates(
    container: PolyData,
    mesh: PolyData,
    coverage_rate: float = 0.3,
    f_init: float = 0.1,
) -> tuple[np.ndarray, int]:
    """Places the objects inside the container at initial location.

    Args:
        container (PolyData): container mesh
        mesh (PolyData): mesh of the objects
        coverage_rate (float): percentage of the container volume that should be filled

    returns:
        tuple[np.ndarray, int]: coordinates of the objects and number of skipped objects
    """
    # TODO: Make sure the container is a closed surface mesh
    # max_dim_mesh = max(np.abs(mesh.bounds)) * 2 # for sphere this is the same, but quicker. for other shapes might be different
    max_dim_mesh = get_max_radius(mesh) * 2
    min_distance_between_meshes = f_init ** (1 / 3) * max_dim_mesh
    max_volume = container.volume * coverage_rate

    tri_container = pyvista_to_trimesh(container)

    objects_coords = []
    acc_vol, skipped = 0, 0
    while acc_vol < max_volume:
        coord = random_coordinate_within_bounds(tri_container.bounds)
        if coord_is_correct(
            coord, tri_container, objects_coords, min_distance_between_meshes
        ):
            objects_coords.append(coord)
            acc_vol += mesh.volume
        else:
            skipped += 1

    return objects_coords, skipped  # type: ignore


def coord_is_correct(
    coord,
    container: trimesh.Trimesh,
    object_coords: list[np.ndarray],
    min_distance_between_meshes: float,
):
    # PolyData([coord]).select_enclosed_points(container)["SelectedPoints"][0]
    if container.contains([coord]):
        distance_arr = [
            np.linalg.norm(coord - i) > min_distance_between_meshes
            for i in object_coords
        ]
        # positive for inside mesh, negative for outside
        distance_to_container = trimesh.proximity.signed_distance(container, [coord])[0]  # type: ignore
        distance_arr.append(distance_to_container > min_distance_between_meshes / 2)

        if np.alltrue(distance_arr):
            return True
    return False


def filter_coords(
    container: PolyData, mesh_volume, coverage_rate, min_distance, coords
):
    max_volume = container.volume * coverage_rate
    acc_vol = 0
    skipped = 0
    objects_coords = []
    # object is centered at the origin

    points_inside = PolyData(coords).select_enclosed_points(container)

    i = -1
    while acc_vol < max_volume:
        i += 1
        coord = points_inside.points[i]
        distance_arr = [True] + [
            np.linalg.norm(coord - i) > min_distance for i in objects_coords
        ]

        if np.alltrue(distance_arr):
            point = container.find_closest_point(coord)
            distance_to_container = np.linalg.norm(coord - point)
            if distance_to_container > min_distance / 2:
                objects_coords.append(coord)
                acc_vol += mesh_volume
                continue

            skipped += 1
    return skipped, objects_coords


def generate_sample_points(mesh: PolyData, container: PolyData, grid_spacing: float, min_distance: float, bounds=None) -> np.ndarray:
    """
    Generate sample points based on a structured grid within a specific mesh.

    :param mesh: A PyVista mesh
    :param grid_spacing: A tuple (dx, dy, dz) representing the grid spacing in each dimension
    :param bounds: A tuple (xmin, xmax, ymin, ymax, zmin, zmax) representing the bounds of the grid
    :return: A PyVista point cloud representing the sample points
    """
    if bounds is None:
        bounds = container.bounds

    xmin, xmax, ymin, ymax, zmin, zmax = np.array(bounds).flatten()
    dx, dy, dz = (grid_spacing, grid_spacing, grid_spacing)

    # Create the structured grid
    x = np.arange(xmin, xmax, dx)
    y = np.arange(ymin, ymax, dy)
    z = np.arange(zmin, zmax, dz)
    structured_grid = StructuredGrid(*np.meshgrid(x, y, z, indexing='ij'))

    # Clip the grid to the mesh
    sample_points: PolyData = structured_grid.clip_surface(container)
    points = []
    for p in sample_points.points:  # type: ignore
        if trimesh.proximity.signed_distance(pyvista_to_trimesh(container), [p])[0] > min_distance / 2:  # type: ignore
            points.append(p)

    return np.array(points)


def estimate_grid_spacing(volume, num_grid_points):
    if volume <= 0 or num_grid_points <= 0:
        raise ValueError("Volume and number of grid points must be positive")

    # Calculate the volume per grid point
    volume_per_point = volume / num_grid_points

    # Take the cube root of the volume per grid point
    cube_root = np.cbrt(volume_per_point)

    # Calculate the grid dimensions
    return cube_root


def objective_function(spacing, target_volume, min_distance, mesh, container):
    grid_points = generate_sample_points(mesh, container, spacing, min_distance)
    objective = np.abs(len(grid_points) * mesh.volume - target_volume)
    return -objective


def find_optimal_grid_spacing(mesh: PolyData, container: PolyData, coverage_rate: float, min_distance: float) -> float:
    target_volume = container.volume * coverage_rate
    n_objects = np.ceil(target_volume / mesh.volume)
    spacing0 = estimate_grid_spacing(container.volume, n_objects)
    # spacing0 = 0.5
    # pyvista_to_trimesh(container)

    res = minimize(
        objective_function,
        spacing0,
        args=(target_volume, min_distance, mesh, container),
        bounds=[(1e-6, None)],  # Avoid zero spacing
        method='SLSQP',
        options={
            'ftol': 1e-6,  # Function value tolerance
            'maxiter': 1000,  # Maximum number of iterations
        },
    )
    if res.success:
        return res.x
    else:
        raise RuntimeError(f"Could not find optimal grid spacing due to {res.message}")


def grid_initialisation(
    container: PolyData,
    mesh: PolyData,
    coverage_rate: float = 0.3,
    f_init: float = 0.1,
) -> np.ndarray:
    """Generates a grid of points within the bounds of the bounding box."""
    # Init
    max_dim_mesh = get_max_radius(mesh) * 2
    min_distance_between_meshes = f_init ** (1 / 3) * max_dim_mesh
    grid_dimensions = find_optimal_grid_spacing(mesh, container, coverage_rate, min_distance_between_meshes)
    grid_points = generate_sample_points(mesh, container, grid_dimensions, min_distance_between_meshes)
    return grid_points


# NOT IN USE CURRENTLY
class PartitionBuilder:
    vor: Voronoi
    container: PolyData
    points: np.ndarray
    seed_points: np.ndarray = np.empty((0))
    threshold: float = 0.01
    power_cells: List[np.ndarray] = []

    def __init__(self, container: PolyData, points: np.ndarray):
        self.container = container
        self.points = points
        self.seed_points = np.random.rand(len(points), 3) * 4
        self.vor = Voronoi(points)

    def power_cell_step(self):
        self.power_cells = []
        for i in range(len(self.points)):
            region = self.vor.regions[self.vor.point_region[i]]
            if len(region) > 0:
                vertices = self.vor.vertices[region]
                # power_cell = PolyData(vertices=vertices, faces=self.vor.ridge_vertices)
                # power_cell = power_cell.intersection(self.container)
                power_cell = vertices
                self.power_cells.append(power_cell)

        # centroids = []
        # for power_cell in self.power_cells:
        # # Use a library such as numpy to compute the centroid of the cell
        #     centroid = np.mean(power_cell, axis=0)
        #     centroids.append(centroid)

    def run(self):
        for _i in range(100):
            self.power_cell_step()

# %%
