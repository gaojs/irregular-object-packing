#%%
import numpy as np
import pyvista as pv
import seaborn as sns
import trimesh
from matplotlib import pyplot as plt
from numpy import ndarray
from pyvista import PolyData

from irregular_object_packing.mesh.sampling import mesh_simplification_condition
from irregular_object_packing.performance_analysis import plots  # noqa E402

# from irregular_object_packing.packing.growth_based_optimisation import Optimizer

def plot_step(optimizer, step, meshes, cat_meshes, container):
    plotter = pv.Plotter()
    plot_simulation_scene(plotter, meshes, cat_meshes, container, c_kwargs={"show_edges": False, "edge_color": "purple"})
    plotter.add_text(optimizer.status(step).table_str, position="upper_left")
    plotter.show()
    return plotter

def create_plot(
    object_locations,
    object_meshes: list[pv.PolyData],
    object_cells,
    container_mesh,
    plotter=None,
):
    # Create a PyVista plotter object
    if plotter is None:
        plotter = pv.Plotter()

    # Create a container mesh with specified opacity
    container = pv.wrap(container_mesh)
    plotter.add_title("objects with CAT cells in Container", font_size=24, shadow=True)
    plotter.add_mesh(container, opacity=0.2)

    # Loop over objects and create a PyVista mesh for each object
    for i in range(len(object_locations)):
        # object_mesh = pv.PolyData(object_meshes[i])
        object_mesh = pv.wrap(object_meshes[i])
        # object_mesh.transform(np.eye(4), object_locations[i])
        plotter.add_mesh(object_mesh.decimate(0.1), color="r", opacity=0.7)  # noqa E501

        plotter.add_mesh(object_cells[i], color="y", opacity=0.3)

    # Set background color and show the plot
    # plotter.background_color = "black"
    plotter.show()


def plot_full_comparison(
    meshes_before,
    meshes_after,
    cat_cell_meshes,
    container,
    plotter=None,
    title_left="Initial Placement",
    title_right="Improved Placement",
):
    if plotter is None:
        plotter = pv.Plotter(shape="1|1")

    colors = generate_tinted_colors(len(meshes_before))
    plotter.subplot(0)
    plotter.add_title(title_left)
    plotter.add_mesh(container, opacity=0.3)
    for i, mesh in enumerate(meshes_before):
        plotter.add_mesh(mesh, color=colors[1][i], opacity=0.9)

    for i, cat_mesh in enumerate(cat_cell_meshes):
        plotter.add_mesh(cat_mesh, color=colors[0][i], opacity=0.5)
        open_edges = cat_mesh.extract_feature_edges(
            boundary_edges=False, feature_edges=False, manifold_edges=False
        )
        if open_edges.n_points > 0:
            plotter.add_mesh(open_edges, color="black", line_width=1)

    plotter.subplot(1)
    plotter.add_title(title_right)
    plotter.add_mesh(container, opacity=0.3)
    for i, mesh in enumerate(meshes_after):
        plotter.add_mesh(mesh, color=colors[1][i], opacity=0.9)

    for i, cat_mesh in enumerate(cat_cell_meshes):
        plotter.add_mesh(cat_mesh, color=colors[0][i], opacity=0.5)

    return plotter


def plot_step_comparison(
    mesh_before,
    mesh_after,
    cat_cell_mesh_1,
    cat_cell_mesh_2=None,
    other_meshes=None,
    plotter=None,
    title_left="Initial Placement",
    title_right="Improved Placement",
):
    if plotter is None:
        plotter = pv.Plotter()

    if cat_cell_mesh_2 is None:
        cat_cell_mesh_2 = cat_cell_mesh_1

    plotter = pv.Plotter(
        shape="1|1", notebook=True
    )  # replace with the filename/path of your first mesh
    plotter.subplot(0)
    plotter.add_title(title_left)
    plotter.add_mesh(mesh_before, color="red", opacity=0.8)
    open_edges = cat_cell_mesh_1.extract_feature_edges(
        boundary_edges=True, feature_edges=False, manifold_edges=False
    )
    plotter.add_mesh(open_edges, color="black", line_width=1, opacity=0.8)
    plotter.add_mesh(cat_cell_mesh_1, color="yellow", opacity=0.4)

    # create the second plot
    # plot2 = pv.Plotter()
    plotter.subplot(1)
    plotter.add_title(title_right)
    plotter.add_mesh(mesh_after, color="red", opacity=0.8)
    plotter.add_mesh(cat_cell_mesh_2, color="yellow", opacity=0.4)
    if other_meshes is not None:
        for mesh in other_meshes:
            plotter.add_mesh(mesh, color="red", opacity=0.8)
    plotter.show()

    return plotter


def none_to_dict(obj):
    if obj is None:
        return {}
    else:
        return obj


def plot_step_single(
    mesh,
    cat_cell_mesh_1,
    other_meshs=None,
    container=None,
    tetmesh=None,
    mesh_opacity=0.9,
    cat_opacity=0.4,
    plotter=None,
    clipped=False,
    title="",
    c_kwargs=None, m_kwargs=None, cat_kwargs=None, oms_kwargs=None,
):
    c_kwargs, m_kwargs, cat_kwargs = [none_to_dict(d) for d in [c_kwargs, m_kwargs, cat_kwargs]]

    if plotter is None:
        plotter = pv.Plotter()

    plotter = pv.Plotter(
        notebook=True
    )  # replace with the filename/path of your first mesh
    plotter.add_title(title)
    cat_cell_mesh_1.extract_feature_edges(
        boundary_edges=True, feature_edges=False, manifold_edges=False
    )
    if clipped:
        try:
            plotter.add_mesh_clip_plane(mesh, opacity=mesh_opacity, color="red", cmap='bwr', scalars="collisions", **m_kwargs)
        except KeyError:
            plotter.add_mesh(mesh, opacity=mesh_opacity, color="blue")
        plotter.add_mesh_clip_plane(cat_cell_mesh_1, opacity=cat_opacity, color="yellow", **cat_kwargs)
    else:
        try:
            plotter.add_mesh(mesh, opacity=mesh_opacity, color="red", cmap='bwr', scalars="collisions", **m_kwargs)
        except KeyError:
            plotter.add_mesh(mesh, opacity=mesh_opacity, color="blue", **m_kwargs)
        plotter.add_mesh(cat_cell_mesh_1, opacity=cat_opacity, color="yellow", **cat_kwargs)

    if container is not None:
        plotter.add_mesh(container, opacity=0.3, **c_kwargs)

    if tetmesh is not None:
        plotter.add_mesh_clip_box(tetmesh, opacity=0.3, show_edges=True, edge_color="green")

    for i in range(len(other_meshs)) if other_meshs is not None else []:
        plotter.add_mesh(other_meshs[i], opacity=0.4, **none_to_dict(oms_kwargs[i]))

    plotter.show()

    return plotter


def generate_tinted_colors(num_tints, base_color_1="FFFF00", base_color_2="FF0000"):
    """Generates two lists of hex colors with corresponding tints."""
    # Convert the base colors to RGB format
    base_color_1_rgb = tuple(int(base_color_1[i : i + 2], 16) for i in (0, 2, 4))
    base_color_2_rgb = tuple(int(base_color_2[i : i + 2], 16) for i in (0, 2, 4))

    # Calculate the step size for the tints
    step_size = 255 // (num_tints + 1)

    # Initialize the lists of tinted colors
    tinted_colors_1 = []
    tinted_colors_2 = []

    # Generate the tinted colors
    for i in range(1, num_tints + 1):
        tint_1_rgb = tuple(
            min(base_color_1_rgb[j] + i * step_size, 255) for j in range(3)
        )
        tint_2_rgb = tuple(
            min(base_color_2_rgb[j] + i * step_size, 255) for j in range(3)
        )

        # Convert the tinted colors back to hex format and add them to the lists
        tinted_color_1_hex = f"#{''.join(hex(c)[2:].zfill(2) for c in tint_1_rgb)}"
        tinted_color_2_hex = f"#{''.join(hex(c)[2:].zfill(2) for c in tint_2_rgb)}"

        tinted_colors_1.append(tinted_color_1_hex)
        tinted_colors_2.append(tinted_color_2_hex)

    return tinted_colors_1, tinted_colors_2


def create_packed_scene(
    container: PolyData,
    objects_coords: list[ndarray],
    mesh: PolyData,
    mesh_scale: float = 1,
    rotate: bool = False,
):
    """make a pyvista plotter with the container and the objects inside.

    Args:
        container (PolyData): container mesh
        objects_coords (List[np.ndarray]): list of coordinates of the objects
        mesh (PolyData): mesh of the objects
        mesh_scale (float, optional): scale of the objects. Defaults to 1.
    """
    objects = []
    colors = []
    for coord in objects_coords:
        new_mesh = mesh.copy()
        if rotate:
            new_mesh = new_mesh.transform(
                trimesh.transformations.random_rotation_matrix()
            )

        new_mesh = new_mesh.scale(mesh_scale)
        new_mesh = new_mesh.translate(coord)

        colors.append(trimesh.visual.random_color())  # noqa E501
        objects.append(new_mesh)

    plotter = pv.Plotter()
    plotter.add_mesh(container, color="white", opacity=0.3)
    for i, object in enumerate(objects):
        plotter.add_mesh(object, color=colors[i], opacity=0.9)

    return plotter


def plot_simulation_scene(plotter, meshes, cat_meshes, container, c_kwargs=None, m_kwargs=None, cat_kwargs=None,
                          ):
    c_kwargs, m_kwargs, cat_kwargs = [none_to_dict(d) for d in [c_kwargs, m_kwargs, cat_kwargs]]

    for i in range(len(meshes)):
        try:
            plotter.add_mesh(meshes[i], opacity=0.95, color="red", cmap='bwr', scalars="collisions", **m_kwargs)
            plotter.add_mesh(cat_meshes[i], opacity=0.6, color="yellow", **cat_kwargs)
        except KeyError:
            plotter.add_mesh(meshes[i], opacity=0.8, color="blue", **m_kwargs)
            plotter.add_mesh(cat_meshes[i], opacity=0.4, color="greenyellow", **cat_kwargs)
    plotter.add_mesh(container, color="white", opacity=0.3, **c_kwargs)


def generate_gif(optimizer, save_path, title="Optimization"):
    plotter = pv.Plotter(notebook=False, off_screen=True)
    plotter.open_gif(save_path)
    plotter.add_title(title)

    _, after_meshes, cat_meshes, container = optimizer.recreate_scene(0)
    for i in range(0, optimizer.idx):
        prev_meshes = after_meshes
        _, after_meshes, cat_meshes, container = optimizer.recreate_scene(i)
        plotter.clear()
        plot_simulation_scene(plotter, prev_meshes, cat_meshes, container)

        plotter.add_text(f"step {i}", position="upper_right")
        plotter.add_text(optimizer.status(i).table_str, position="upper_left")

        plotter.write_frame()
        plotter.clear()

        plot_simulation_scene(plotter, after_meshes, cat_meshes, container)
        plotter.add_text(f"step {i}", position="upper_right")
        plotter.add_text(optimizer.status(i).table_str, position="upper_left")
        plotter.write_frame()

    focus_point = [0, 0, 0]

    num_frames = 100
    rotation_step = 360 / num_frames

    for i in range(num_frames):
        # Compute the new camera position
        angle = i * rotation_step
        x_offset = 10 * np.sin(np.radians(angle))
        y_offset = 10 * np.cos(np.radians(angle))
        new_camera_position = [
            (focus_point[0] + x_offset, focus_point[1] + y_offset, focus_point[2] + 10),
            focus_point,
            (0, 0, 1),
        ]

        # Update the camera position
        plotter.camera_position = new_camera_position
        plotter.write_frame()

    plotter.close()


def plot_simplification_curve():
    fig, ax = plt.subplots()

    a = [0.02, 0.04, 0.06, 0.08, 0.1]
    a = [0.05]
    b = [0.1, 0.3, 0.5, 0.7, 0.9]

    x = np.linspace(0.01, 1, 1000)

    for ai in a:
        for bi in b:
            print(f"{ai} {bi}`")
            y = [mesh_simplification_condition(xi, ai, bi) for xi in x]
            ax.plot(x,y, label=fr"$\beta: {bi:.1f}$")

    ax.annotate(r"$\alpha = 0.05$", xy=(0.0, a[0]), xytext=(0.00, 0.1)) #, arrowprops={"arrowstyle": "->", "color": "black"})
    ax.plot([0], a, 'o', color='green',  zorder=100, clip_on=False)
    ax.set_xlabel(r"k")
    ax.set_ylabel(r"$\rho$")
    ax.legend()
    plt.savefig('simplification_curve.pdf')
    sns.despine()
    plt.show()


#%%
# plot_simplification_curve()
# %%
