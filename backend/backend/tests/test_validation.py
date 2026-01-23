import pytest
from backend.app.main import _validate_and_coerce_row
from fastapi import HTTPException


def test_validate_int_and_string():
    cols = {
        'age': {'data_type': 'int', 'required': True, 'validation': None},
        'name': {'data_type': 'string', 'required': True, 'validation': 'full_name'},
        'score': {'data_type': 'float', 'required': False}
    }

    params, keys = _validate_and_coerce_row({'age': '30', 'name': 'Alice', 'score': '12.5'}, cols)
    assert params['age'] == 30
    assert params['name'] == 'Alice'
    assert pytest.approx(params['score'], 0.001) == 12.5
    assert set(keys) == {'age', 'name', 'score'}


def test_invalid_full_name():
    cols = {'name': {'data_type': 'string', 'required': True, 'validation': 'full_name'}}
    with pytest.raises(HTTPException):
        _validate_and_coerce_row({'name': 'John2'}, cols)


def test_missing_required():
    cols = {'email': {'data_type': 'string', 'required': True, 'validation': 'email'}}
    with pytest.raises(HTTPException):
        _validate_and_coerce_row({'email': ''}, cols)


def test_boolean_coercion():
    cols = {'active': {'data_type': 'bool', 'required': False}}
    params, keys = _validate_and_coerce_row({'active': 'true'}, cols, enforce_required=False)
    assert params['active'] is True

