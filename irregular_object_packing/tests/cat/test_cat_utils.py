import unittest

import numpy as np
from parameterized import parameterized
from pyvista import UnstructuredGrid

from irregular_object_packing.cat.utils import (
    compute_face_unit_normal,
    create_face_normal,
    get_cell_arrays,
    get_tetmesh_cell_arrays,
    n_related_objects,
    sort_by_occurrance,
)


class TestSortByOccurrence(unittest.TestCase):
    def assert_sorted_correctly(self, sorted_point_ids, sorted_object_ids, expected_point_ids, expected_object_ids):
        self.assertListEqual(list(sorted_point_ids), expected_point_ids)
        self.assertListEqual(list(sorted_object_ids), expected_object_ids)


    def test_zero(self):
        point_ids = [0]
        object_ids = [0]
        self.assertRaises(ValueError, sort_by_occurrance, point_ids, object_ids)

    def test_3331(self):
        point_ids = [1, 2, 3, 4]
        object_ids = [6, 6, 6, 1]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [1,2,3,4], [6, 6, 6, 1])
        self.assertEqual(expected_case, (3,1))

    def test_2222(self):
        point_ids = [1, 2, 3, 4]
        object_ids = [1, 1, 2, 2]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [ 3, 4, 1, 2], [2, 2, 1,1])
        self.assertEqual(expected_case, (2,2))

    def test_2211(self):
        point_ids = [ 1, 2, 3, 4]
        object_ids = [1, 2, 2, 3]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [2, 3, 4, 1], [2, 2, 3, 1])
        self.assertEqual(expected_case, (2,1,1))

    def test_2211_unsorted(self):
        point_ids = [5, 2, 1, 3]
        object_ids = [2, 1, 2, 4]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [5,1,3,2], [2, 2, 4, 1])
        self.assertEqual(expected_case, (2,1,1))

    def test_4444(self):
        point_ids = [1, 2, 3, 4]
        object_ids = [1, 1, 1, 1]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [1, 2, 3, 4], [1, 1, 1, 1])
        self.assertEqual(expected_case, (4,))

    def test_4444_reversed(self):
        point_ids = [4, 3, 2, 1]
        object_ids = [1, 1, 1, 1]

        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [4, 3, 2, 1], [1, 1, 1, 1])
        self.assertEqual(expected_case, (4,))

    def test_1111(self):
        point_ids = [1, 2, 3, 4]
        object_ids = [4, 3, 2, 1]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [1, 2, 3, 4], [4, 3, 2, 1])
        self.assertEqual(expected_case, (1,1,1,1))

    def test_1111_reversed(self):
        point_ids = [4, 3, 2, 1]
        object_ids = [1, 2, 3, 4]
        sorted_point_ids, sorted_object_ids, expected_case = sort_by_occurrance(point_ids, object_ids)
        self.assert_sorted_correctly(sorted_point_ids, sorted_object_ids, [1, 2, 3, 4], [4, 3, 2, 1])
        self.assertEqual(expected_case, (1,1,1,1))


    def test_empty_errors(self):
        self.assertRaises(ValueError, sort_by_occurrance, [], [])

    def test_inequal_lengths(self):
        point_ids = [2, 3]
        object_ids = [2, 2, 3, 3, 3]
        self.assertRaises(ValueError, sort_by_occurrance, point_ids, object_ids)


class TestComputeFaceUnitNormal(unittest.TestCase):
    @parameterized.expand([
        # 3 points, with point on the positive z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
         np.array([1, 1, 1]),
         np.array([0, 0, 1])),
        # 3 points, with point on the negative z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
         np.array([1, 1, -1]),
         np.array([0, 0, -1])),
        # 4 points, with point on the positive z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0]]),
         np.array([1, 1, 1]),
         np.array([0, 0, 1])),
        # 4 points, with point on the negative z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0], [1, 1, 0]]),
         np.array([1, 1, -1]),
         np.array([0, 0, -1])),
    ])
    def test_normal_cases(self, points, v_i, expected_normal):
        result = compute_face_unit_normal(points, v_i)
        np.testing.assert_array_almost_equal(result, expected_normal)

    @parameterized.expand([
        # 2D points
        (np.array([[0, 0], [0, 1], [1, 0]]), np.array([1, 1])),
        # 5 points
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], [1, 1, 1]]), np.array([1, 1, 1])),
    ])
    def test_exception_cases(self, points, v_i):
        with self.assertRaises(AssertionError):
            compute_face_unit_normal(points, v_i)

class CreateFaceNormal(unittest.TestCase):
    @parameterized.expand([
        # format:
            # (points,
            #  v_i,
            #  expected_normal)

        # 3 points, with point on the positive z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
         np.array([1, 1, 1]),
         np.array([[1, 1, 1], [0,0,0], [0,0,1]])),
        # 3 points, with point on the negative z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
         np.array([1, 1, -1]),
         np.array([[1,1,-1], [0,0,0], [0, 0, -1]])),
        # 4 points, with point on the positive z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
         np.array([1, 1, 1]),
         np.array([[1,1,1],[0,0,0],[0, 0, 1]])),
        # 4 points, with point on the negative z-axis
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0]]),
         np.array([1, 1, -1]),
         np.array([[1,1,-1],[0,0,0], [0, 0, -1]])),
    ])
    def test_normal_cases(self, points, v_i, expected_normal):
        result = create_face_normal(points, v_i)
        np.testing.assert_array_almost_equal(result, expected_normal)

    @parameterized.expand([
        # 2D points
        (np.array([[0, 0], [0, 1], [1, 0]]), np.array([1, 1])),
        # 5 points
        (np.array([[0, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1], [1, 1, 1]]), np.array([1, 1, 1])),
    ])
    def test_exception_cases(self, points, v_i):
        with self.assertRaises(AssertionError):
            create_face_normal(points, v_i)

class TestMeshFunctions(unittest.TestCase):

    def test_get_cell_arrays(self):
        # # Test with no cells
        # cells = np.array([])
        # result = get_cell_arrays(cells)
        # self.assertEqual(result.size, 0)

        # Test with one cell
        cells = np.array([4, 1, 2, 3, 4])
        result = get_cell_arrays(cells)
        self.assertTrue(np.array_equal(result, np.array([[1, 2, 3, 4]])))

        # Test with two cells
        cells = np.array([4, 1, 2, 3, 4, 4, 5, 6, 7, 8])
        result = get_cell_arrays(cells)
        self.assertTrue(np.array_equal(result, np.array([[1, 2, 3, 4], [5, 6, 7, 8]])))

    def test_get_tetmesh_cell_arrays(self):
        # Test with no cells
        # grid = pv.UnstructuredGrid()
        # result = get_tetmesh_cell_arrays(grid)
        # self.assertEqual(result.size, 0)

        # Test with one cell
        cells = np.array([4, 0, 1, 2, 3], dtype=np.int64)
        grid = UnstructuredGrid(cells, np.array([10], dtype=np.float64), np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float64))
        result = get_tetmesh_cell_arrays(grid)
        self.assertTrue(np.array_equal(result, np.array([[0, 1, 2, 3]])))

        # Test with two cells
        cells = np.array([4, 0, 1, 2, 3, 4, 4, 5, 6, 7])
        grid = UnstructuredGrid(cells, np.array([10, 10]), np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 1], [1, 1, 0], [0, 1, 1], [1, 0, 1]], dtype=np.float64))
        result = get_tetmesh_cell_arrays(grid)
        self.assertTrue(np.array_equal(result, np.array([[0, 1, 2, 3], [4, 5, 6, 7]])))


class nRelatedObjects(unittest.TestCase):
    def test_belongs_to_single_object(self):
        # # Test with no objects
        # Test with one object
        objects_npoints = [4]
        cell = np.array([0, 1, 2, 3])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [0, 0, 0, 0])

        objects_npoints = [10]
        cell = np.array([0, 4, 5, 9])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [0, 0, 0, 0])

    def test_belongs_to_multiple_objects(self):
        # Test with two objects
        objects_npoints = [2, 2]
        cell = np.array([0, 1, 2, 3])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [0, 0, 1, 1])

        # Test with three objects non equal
        objects_npoints = [2, 4, 2]
        cell = np.array([0, 1, 4, 5])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [0, 0, 1, 1])

        # Test with four objects non equal
        objects_npoints = [2, 4, 2, 2]
        cell = np.array([0, 1, 4, 6])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [0, 0, 1, 2])

        # test for a lot of objects unsorted
        objects_npoints = np.ones(100) * 8
        cell = np.array([160, 79, 80, 8])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [20, 9, 10, 1])

        # test for increasing points in objects
        objects_npoints = np.array([1, 2, 3, 4, 5, 6, 7, 8])
        cell = np.array([5, 3, 2, 10])
        result = n_related_objects(objects_npoints, cell)
        self.assertEqual(result.tolist(), [2, 2, 1, 4])

if __name__ == '__main__':
    unittest.main()
