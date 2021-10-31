import unittest
import numpy as np
from cogs.mathbot.mathbot import rpn_parser, rpn_eval, gaussian_elimination, NoSolution


class MyTestCase(unittest.TestCase):
    def test_rpn(self):
        equations = {
            '1 + 1': 2,
            '2 - 3': -1,
            '3 * 10': 30,
            '6 / 2': 3,
            '3 ^ 3': 27,
            'sqrt(16)': 4,
            '7!': 5040,
            '1+ 3': 4,
            '-2 (-8)': 16,
            '3! + 10²': 106,
            '10⁻²': 0.01,
            '√(3²+4²)': 5,
            '3.7x-5': -18.5,
        }
        for equation, expected_result in equations.items():
            print(f'{equation=}, {expected_result=}, ', end='')
            rpn_notation = rpn_parser(equation)
            actual_result = rpn_eval(rpn_notation)
            self.assertEqual(actual_result, expected_result)
            print(f'{actual_result=}')

    def test_gaussian(self):
        matrices = ((np.array([[3, -4, -1, 17],
                               [-1, 3, 1, -12],
                               [-2, 4, 1, -16]], dtype=float), (1, -3, -2)),
                    (np.array([[2, 1, -2, 1, 9],
                               [-1, 3, 1, -4, -8],
                               [6, -2, -4, 5, 32],
                               [10, -7, 5, -7, 48]], dtype=float), (8, 5, 9, 6)),
                    (np.array([[2, 1, 2, 1, 45],
                               [1, 3, 1, -4, 8],
                               [6, -2, 6, 5, 122],
                               [10, -7, 10, -7, 93]], dtype=float), NoSolution)
                    )
        for matrix, expected_result in matrices:
            print(f'{matrix=}, {expected_result=}, ', end='')
            if isinstance(expected_result, tuple):
                actual_result = gaussian_elimination(matrix)
                for a, e in zip(actual_result, expected_result):
                    self.assertAlmostEqual(a, e, places=12)
                print(f'{actual_result=}')
            else:
                with self.assertRaises(expected_result):
                    gaussian_elimination(matrix)
                actual_result = expected_result
                print(f'{actual_result=}')


if __name__ == '__main__':
    unittest.main()
