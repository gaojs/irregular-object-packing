import pyvista as pv
from trimesh import Trimesh
from irregular_object_packing.packing import nlc_optimisation
from irregular_object_packing.packing.chordal_axis_transform import face_coord_to_points_and_faces

# from irregular_object_packing.packing.growth_based_optimisation import Optimizer


def create_plot(object_locations, object_meshes: list[pv.PolyData], object_cells, container_mesh, plotter=None):
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
        object_mesh = object_meshes[i]
        # object_mesh.transform(np.eye(4), object_locations[i])
        plotter.add_mesh(object_mesh.decimate(0.1), color="r", opacity=0.7)

        plotter.add_mesh(object_cells[i], color="y", opacity=0.3)

    # Set background color and show the plot
    # plotter.background_color = "black"
    plotter.show()


def plot_full_comparison():
    pass


def plot_step_comparison(original_mesh: Trimesh, tf_arrs, cat_cell_mesh_1, cat_cell_mesh_2=None):
    tf_init, tf_fin = tf_arrs
    if cat_cell_mesh_2 is None:
        cat_cell_mesh_2 = cat_cell_mesh_1

    object_mesh = original_mesh.copy()
    post_mesh = object_mesh.copy()

    original_tranform = nlc_optimisation.construct_transform_matrix(tf_init)
    modified_transform = nlc_optimisation.construct_transform_matrix(tf_fin)

    init_mesh = pv.wrap(object_mesh.apply_transform(original_tranform)).decimate(0.1)
    post_mesh = pv.wrap(post_mesh.apply_transform(modified_transform)).decimate(0.1)

    plotter = pv.Plotter(shape="1|1", notebook=True)  # replace with the filename/path of your first mesh
    plotter.subplot(0)
    plotter.add_title("Initial Placement")
    plotter.add_mesh(init_mesh, color="red", opacity=0.8)
    plotter.add_mesh(cat_cell_mesh_1, color="yellow", opacity=0.4)

    # create the second plot
    # plot2 = pv.Plotter()
    plotter.subplot(1)
    plotter.add_title("Optimized Placement")
    plotter.add_mesh(post_mesh, color="red", opacity=0.8)
    plotter.add_mesh(cat_cell_mesh_2, color="yellow", opacity=0.4)
    plotter.show()

    return plotter


# def plot_state(optimizer: Optimizer):
#     object_meshes = optimizer.get_processed_meshes()
#     cat_meshes = optimizer.get_cat_meshes()

#     create_plot(optimizer.tf_arrs, object_meshes, cat_meshes, optimizer.container.to_mesh())


def generate_tinted_colors(num_tints, base_color_1="FFFF00", base_color_2="FF0000"):
    """
    Generates two lists of hex colors with corresponding tints.
    """
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
        tint_1_rgb = tuple(min(base_color_1_rgb[j] + i * step_size, 255) for j in range(3))
        tint_2_rgb = tuple(min(base_color_2_rgb[j] + i * step_size, 255) for j in range(3))

        # Convert the tinted colors back to hex format and add them to the lists
        tinted_color_1_hex = f"#{''.join(hex(c)[2:].zfill(2) for c in tint_1_rgb)}"
        tinted_color_2_hex = f"#{''.join(hex(c)[2:].zfill(2) for c in tint_2_rgb)}"

        tinted_colors_1.append(tinted_color_1_hex)
        tinted_colors_2.append(tinted_color_2_hex)

    return tinted_colors_1, tinted_colors_2
