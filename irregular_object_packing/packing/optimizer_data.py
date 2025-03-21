import logging
import pickle
from dataclasses import dataclass, field, fields

import numpy as np
from numpy import ndarray
from pandas import DataFrame
from pyvista import PolyData
from tabulate import tabulate

from irregular_object_packing.mesh.collision import (
    compute_and_add_all_collisions,
    compute_cat_violations,
)
from irregular_object_packing.mesh.sampling import (
    resample_pyvista_mesh,
)
from irregular_object_packing.mesh.utils import convert_faces_to_polydata_input
from irregular_object_packing.packing.nlc_optimisation import construct_transform_matrix

STATE_DIRECTORY = "../dump/state/"


@dataclass
class SimConfig:
    max_a: float = 1 / 12 * np.pi
    """The maximum rotation angle per growth step."""
    max_t: float = None
    """The maximum translation per growth step."""
    init_f: float = 0.1
    """Final scale."""
    final_scale: float = 1.0
    """The initial scale factor."""
    itn_max: int = 200
    """The maximum number of iterations per scaling step."""
    n_scale_steps: int = 9
    """The number of scaling steps."""
    r: float = 0.3
    """The coverage rate."""
    plot_intermediate: bool = False
    """Whether to plot intermediate results."""
    log_lvl: int = logging.ERROR
    """The log level maximum level is 3."""
    padding: float = 0.0
    """The padding which is added to the inside of the cat cells."""
    sampling_disabled: bool = False
    alpha: float = 0.05
    beta: float = 0.1
    n_threads: int = None
    """Whether to use sequential scaling."""
    container_volume: float = 10.0
    """The volume of the container."""
    new_cat: bool = False,

    handle_collisions: bool = True


@dataclass
class IterationData:
    i: int
    """The iteration step."""
    i_b: int
    """The scale iteration step."""
    f_start: float
    """start value of the scale."""
    f_target: float
    """The maximum value of the scale."""
    n_succes_scale: int
    """The number of objects that have succesfully been scaled to the current limit."""
    sample_rate: int
    """The sample rate of the object surface mesh."""
    cat_violations: list = field(default_factory=list)
    container_violations: list = field(default_factory=list)
    collisions: list = field(default_factory=list)

    @property
    def table_str(self):
        return f"i:\t{self.i},\ni_b:\t{self.i_b},\nfe:\t{self.f_target:.3f},\nsuccess: {self.n_succes_scale}"


@dataclass
class State:
    shape0: PolyData
    description: str
    container0: PolyData
    settings: SimConfig
    iteration_data: IterationData
    tf_arrays: ndarray

    @property
    def filedir(self):
        return f"{STATE_DIRECTORY}state-{self.description}-n{len(self.tf_arrays)}_cv{self.container0.volume:.1f}_f{self.iteration_data.f_target}.pickle"

    def write_state(self):
        with open(self.filedir, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load_state(filename: str) -> "State":
        with open(filename, "rb") as f:
            data = pickle.load(f)

        return data


class OptimizerData:
    """Data structure for conveniently getting per-step meshes from the data generated
    by the optimizer."""
    config: SimConfig
    shape0: PolyData
    shape: PolyData
    container0: PolyData
    container: PolyData
    normals: list
    cat_cells: list
    tf_arrays: ndarray
    previous_tf_arrays: ndarray
    time_per_step: ndarray
    its_per_step: ndarray
    fails_per_step: ndarray
    errors_per_step: ndarray
    description: str
    _data = {}
    _index = -1

    def __init__(self):
        self.normals = []
        self.cat_cells = []
        self.tf_arrays = np.empty(0)
        self.i_b = 0
        self.i = 0
        self.seed=None
        return

    def __getitem__(self, key):
        return self._data[key]

    def check_setup(self):
        assert self.shape0 is not None, "setup not correct: shape0 is None"
        assert self.container0 is not None, "setup not correct: container0 is None"
        assert len(self.tf_arrays) > 0, "setup not correct: tf_arrays is empty"


    def add(self, tf_arrays: ndarray, normals: list, cat_cells: list, iteration_data: IterationData):
        self._data[self._index] = {
            "tf_arrays": tf_arrays.copy(),
            "normals": normals.copy(),
            "cat_cells": cat_cells.copy(),
            "iterationData": iteration_data,
        }
        # self._data[ref] = self._data[self._index]
        self._index += 1

    def _tf_arrays(self, index: int):
        return self._data[index]["tf_arrays"]

    def _cat_cells(self, index: int) -> list:
        return self._data[index]["cat_cells"]

    def _iteration_data(self, index: int) -> IterationData:
        return self._data[index]["iterationData"]

    def _get_mesh(self, index: int, obj_id: int, mesh: PolyData) -> PolyData:
        tf_array = self._tf_arrays(index)[obj_id]
        return mesh.transform(
            construct_transform_matrix(tf_array[0], tf_array[1:4], tf_array[4:7]),
            inplace=False,
        )

    def _get_meshes(self, index: int, mesh: PolyData) -> list[PolyData]:
        return [
            mesh.transform(
                construct_transform_matrix(tf_array[0], tf_array[1:4], tf_array[4:7]),
                inplace=False,
            )
            for tf_array in self._tf_arrays(index)
        ]

    @property
    def idx(self):
        """The index of the latest saved iteration."""
        return self._index - 1

    @property
    def n_objs(self) -> int:
        return len(self.tf_arrays)

    @property
    def object_coords(self) -> ndarray:
        return self.tf_arrays[:, 4:]

    @property
    def object_rotations(self) -> ndarray:
        rads = self.tf_arrays[:, 1:4]
        return np.rad2deg(rads)

    @property
    def object_scales(self) -> ndarray:
        return self.tf_arrays[:, 0]
    # ------------------- Public methods -------------------
    def mesh_before(self, iteration: int, obj_id: int):
        """Get the mesh of the object at the given iteration, before the
        optimisation."""

        return self._get_mesh(iteration - 1, obj_id, self.resample_mesh(iteration))

    def mesh_after(self, iteration: int, obj_id: int):
        """Get the mesh of the object at the given iteration, after the optimisation."""
        return self._get_mesh(iteration, obj_id, self.resample_mesh(iteration))

    def cat_mesh(self, iteration: int, obj_id: int) -> PolyData:
        """Get the mesh of the cat cell that corresponds to the object from the given
        iteration."""
        return PolyData(
            *convert_faces_to_polydata_input(self._cat_cells(iteration)[obj_id])
        )

    def status(self, iteration: int) -> IterationData:
        """Get the data of the given iteration."""
        return self._iteration_data(iteration)

    def violating_mesh_ids(self, iteration: int) -> list[int]:
        status = self.status(iteration)
        mesh_ids = set()
        for obj_id in status.cat_violations:
            mesh_ids.add(obj_id)
        for obj_id in status.container_violations:
            mesh_ids.add(obj_id)
        for (a, b, _n) in status.collisions:
            mesh_ids.add(a)
            mesh_ids.add(b)

        return list(mesh_ids)

    def resample_mesh(self, iteration: int) -> PolyData:
        """Resample the given mesh with the sample rate of the given iteration."""
        status = self.status(iteration)
        try:
            return resample_pyvista_mesh(mesh=self.shape0, target_faces=status.sample_rate)
        except ValueError:
            return self.shape0

    def meshes_before(self, iteration: int):
        """Get the meshes of all objects at the given iteration, before the
        optimisation."""
        if iteration < 0:
            return ValueError("No meshes before iteration 0")
        return self._get_meshes(iteration - 1, self.resample_mesh(iteration))

    def meshes_after(self, iteration: int):
        """Get the meshes of all objects at the given iteration, after the
        optimisation."""
        return self._get_meshes(iteration, self.resample_mesh(iteration))

    def cat_meshes(self, iteration: int) -> list[PolyData]:
        """Get the meshes of all cat cells that correspond to the objects from the given
        iteration."""
        if self._cat_cells(iteration) is None:
            raise ValueError("No cat data stored yet for iteration " + str(iteration))
        return [
            PolyData(*convert_faces_to_polydata_input(self._cat_cells(iteration)[obj_id]))
            for obj_id in range(len(self._tf_arrays(iteration)))
        ]

    def recreate_scene(self, iteration: int):
        """Recreate the scene at the given iteration."""
        meshes_before = self.meshes_before(iteration)
        meshes_after = self.meshes_after(iteration)
        cat_meshes = self.cat_meshes(iteration)
        compute_and_add_all_collisions(meshes_before, cat_meshes, self.container0, set_contacts=True)
        compute_and_add_all_collisions(meshes_after, cat_meshes, self.container0, set_contacts=True)

        return meshes_before, meshes_after, cat_meshes, self.container0

    def recreate_object_scene(self, iteration, object_id):
        """Recreate the scene before and after at the given iteration for the given object."""
        mesh_before = self.mesh_before(iteration, object_id)
        mesh_after = self.mesh_after(iteration, object_id)
        cat_mesh = self.cat_mesh(iteration, object_id)
        compute_cat_violations([mesh_before, mesh_after], [cat_mesh, cat_mesh], set_contacts=True)

        return mesh_before, mesh_after, cat_mesh

    def current_meshes(self, shape: PolyData = None):
        """Construct mesh objects from the latest self.tf_arrays ."""
        if shape is None:
            shape = self.shape

        return [shape.transform(
                construct_transform_matrix(tf_array[0], tf_array[1:4], tf_array[4:7]), inplace=False,
                )
                for tf_array in self.tf_arrays]

    def final_meshes_before(self):
        """Get the meshes of all objects at the final iteration, before the
        optimisation."""
        return [self.shape.transform(
            construct_transform_matrix(tf_array[0], tf_array[1:4], tf_array[4:7]), inplace=False,
        )
            for tf_array in self.tf_arrays]

    def final_cat_meshes(self):
        """Get the meshes of all cat cells that correspond to the objects from the final
        iteration."""
        if self._index <= 0:
            ValueError("No cat data stored yet")
        return [
            PolyData(*convert_faces_to_polydata_input(self.cat_cells[obj_id]))
            for obj_id in range(self.n_objs)
        ]

    def before_and_after_meshes(self, iteration: int, mesh: PolyData):
        """Get the meshes of all objects at the given iteration, before and after the
        optimisation."""
        return (
            self.meshes_before(iteration),
            self.meshes_after(iteration),
            self.cat_meshes(iteration),
        )

    def _report(self, iteration=None):
        if iteration is None:
            iteration = self.idx
        tabulate(
            [self._tf_arrays(i) for i in range(self.idx)],
            headers=["scale", "r_x", "ry", "rz", "t_x", "t_y", "t_z"],
        )


    def report(self):
        return DataFrame(
            data=self.tf_arrays, columns=["scale", "r_x", "ry", "rz", "t_x", "t_y", "t_z"]
        )

    def print_report(self, notebook=False):
        table = tabulate(
            [self.status(i) for i in range(self.idx)],  # type: ignore
            headers=[field.name for field in fields(IterationData)],
            tablefmt="html" if notebook else "grid",
            showindex=True,
        )
        print(table)
        return table

    def write_state(self):
        """Write the current state to a file."""
        state = State(
            container0=self.container0,
            shape0=self.shape0,
            description=self.description,
            settings=self.config,
            iteration_data=self.status(self.idx),
            tf_arrays=self.tf_arrays,
        )
        with open(state.filedir, "wb") as f:
            pickle.dump(state, f)  # noqa: F821

    def write_positions(self, dir):
        """Write the current positions to a file."""
        positions = np.empty((self.n_objs, 6))
        positions[:, 0:3] = self.object_coords
        positions[:, 3:6] = self.object_rotations

        with open(dir+".pos", "wb") as f:
            np.savetxt(f, positions, delimiter=" ")


    @staticmethod
    def load_state(filename: str) -> 'State':
        """Load the current state from a file."""
        with open(f"{STATE_DIRECTORY}{filename}", "rb") as f:
            state: State = pickle.load(f)

        return state


