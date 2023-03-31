# %%

import numpy as np
import pyvista as pv
from sklearn.cluster import KMeans


def print_mesh_info(mesh: pv.PolyData, description="", suppress_scientific=True):
    with np.printoptions(precision=4, suppress=suppress_scientific):
        print(
            f"Mesh info {description}: {mesh}, \nvolume: {mesh.volume}, \nbounding box:"
            f" {mesh.bounds} \ncenter of mass: {mesh.center_of_mass()}\n"
        )


def resample_pyvista_mesh_kmeans(mesh, target_vertices):
    # Convert PyVista mesh to NumPy points|
    points = mesh.points

    # Cluster points using KMeans to get the target number of vertices
    kmeans = KMeans(n_clusters=target_vertices)
    kmeans.fit(points)
    new_points = kmeans.cluster_centers_

    # Create a new mesh from the reduced points
    cloud = pv.PolyData(new_points)

    # Regenerate the surface mesh using Delaunay triangulation
    new_mesh = cloud.reconstruct_surface()

    # Extract the surface of the 3D triangulation
    new_mesh = new_mesh.extract_surface()

    # Smooth the mesh
    new_mesh = new_mesh.smooth(n_iter=10)

    return new_mesh


def resample_pyvista_mesh(mesh: pv.PolyData, target_faces):
    # Compute the decimation factor based on the target number of faces
    num_faces = mesh.n_faces
    if num_faces < target_faces:
        raise ValueError("Target number of faces must be less than the number of faces in the mesh.")
    decimation_factor = 1 - target_faces / num_faces

    # Decimate the mesh using the decimation factor
    new_mesh = mesh.decimate(decimation_factor, inplace=False)

    print(new_mesh)
    # Smooth the mesh
    new_mesh = new_mesh.smooth(n_iter=10)

    return new_mesh
