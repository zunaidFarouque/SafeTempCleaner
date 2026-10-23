from unittest.mock import patch
from src.single_instance import SingleInstanceChecker


def test_single_instance_checker():
    checker = SingleInstanceChecker(mutex_name="Global\\SafeTempCleaner_Test_Mutex")
    # In test environment, should check cleanly
    assert checker.mutex_name == "Global\\SafeTempCleaner_Test_Mutex"
