import pytest

from peewee_validates import ValidationError
from peewee_validates import StringField
from peewee_validates import validate_email
from peewee_validates import validate_equal
from peewee_validates import validate_function
from peewee_validates import validate_length
from peewee_validates import validate_matches
from peewee_validates import validate_none_of
from peewee_validates import validate_not_empty
from peewee_validates import validate_one_of
from peewee_validates import validate_range
from peewee_validates import validate_regexp
from peewee_validates import validate_required

field = StringField()


def test_validate_required():
    validator = validate_required()

    for value in (None,):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in ('okay', '', '  '):
        field.value = value
        validator(field, {})


def test_validate_not_empty():
    validator = validate_not_empty()

    for value in ('', '  '):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, 'alright', '123'):
        field.value = value
        validator(field, {})


def test_validate_length():
    validator = validate_length(low=2, high=None, equal=None)

    for value in ('1', [1]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, '22', 'longer', [1, 2]):
        field.value = value
        validator(field, {})

    validator = validate_length(low=None, high=2, equal=None)

    for value in ('123', [1, 2, 3]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, '22', '', [1, 2]):
        field.value = value
        validator(field, {})

    validator = validate_length(low=None, high=None, equal=2)

    for value in ('242', '', [1, 2, 3]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, '22', [1, 2]):
        field.value = value
        validator(field, {})

    validator = validate_length(low=2, high=4, equal=None)

    for value in ('1', '', [1, 2, 3, 4, 5]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, '22', '2222', [1, 2]):
        field.value = value
        validator(field, {})


def test_validate_one_of():
    validator = validate_one_of(('a', 'b', 'c'))

    for value in ('1', '', [1, 2, 3, 4, 5]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, 'a', 'b', 'c'):
        field.value = value
        validator(field, {})


def test_validate_none_of():
    validator = validate_none_of(('a', 'b', 'c'))

    for value in ('a', 'b', 'c'):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, '1', '', [1, 2, 3, 4, 5]):
        field.value = value
        validator(field, {})


def test_validate_range():
    validator = validate_range(low=10, high=100)

    for value in (8, 800):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, 10, 100):
        field.value = value
        validator(field, {})


def test_validate_equal():
    validator = validate_equal('yes')

    for value in ('no', 100):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {})

    for value in (None, 'yes'):
        field.value = value
        validator(field, {})


def test_validate_matches():
    validator = validate_matches('other')

    for value in ('no', 100):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {'other': 'yes'})

    for value in (None, 'yes'):
        field.value = value
        validator(field, {'other': 'yes'})


def test_validate_regexp():
    validator = validate_regexp('^[a-z]{3}$', flags=0)

    for value in ('123', 'abcd', [123, 123]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {'other': 'yes'})

    for value in (None, 'yes', 'abc'):
        field.value = value
        validator(field, {'other': 'yes'})


def test_validate_function():
    def verify(value, check):
        return value == check

    validator = validate_function(verify, check='tim')

    for value in ('123', 'abcd', [123, 123]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {'other': 'yes'})

    for value in (None, 'tim'):
        field.value = value
        validator(field, {'other': 'yes'})


def test_validate_email():
    validator = validate_email()

    for value in ('bad', '())@asdfsd.com', 'tim@().com', [123, 123]):
        field.value = value
        with pytest.raises(ValidationError):
            validator(field, {'other': 'yes'})

    for value in (None, 'tim@example.com', 'tim@localhost'):
        field.value = value
        validator(field, {'other': 'yes'})
