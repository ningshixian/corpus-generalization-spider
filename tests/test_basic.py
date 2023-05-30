# -*- coding: utf-8 -*-

# from .context import sample

import unittest
import pytest

'''Unittest 单元测试 '''

def func(x):
    return x + 1


class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test(self):
        self.assertEqual(func(3), 4)


def test_answer():
    assert func(3) == 5


if __name__ == '__main__':
    unittest.main()
    # py.test test_basic.py