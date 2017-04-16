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

    field.value = None
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'okay'
    validator(field, {})

    field.value = ''
    validator(field, {})


def test_validate_not_empty():
    validator = validate_not_empty()

    field.value = ''
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = '  '
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'okay'
    validator(field, {})


def test_validate_length():
    validator = validate_length(low=2, high=None, equal=None)

    field.value = '1'
    with pytest.raises(ValidationError):
        validator(field, {})

    validator = validate_length(low=None, high=2, equal=None)

    field.value = '123'
    with pytest.raises(ValidationError):
        validator(field, {})

    validator = validate_length(low=None, high=None, equal=2)

    field.value = '123'
    with pytest.raises(ValidationError):
        validator(field, {})

    validator = validate_length(low=2, high=4, equal=None)

    field.value = '1'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = '12345'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = '1234'
    validator(field, {})

    field.value = (1, 2, 3, 4)
    validator(field, {})


def test_validate_one_of():
    validator = validate_one_of(('a', 'b', 'c'))

    field.value = 'd'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'a'
    validator(field, {})


def test_validate_none_of():
    validator = validate_none_of(('a', 'b', 'c'))

    field.value = 'a'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'd'
    validator(field, {})


def test_validate_range():
    validator = validate_range(low=10, high=100)

    field.value = 8
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 800
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 50
    validator(field, {})


def test_validate_equal():
    validator = validate_equal('yes')

    field.value = 'no'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'yes'
    validator(field, {})


def test_validate_matches():
    validator = validate_matches('other')

    field.value = 'no'
    with pytest.raises(ValidationError):
        validator(field, {'other': 'yes'})

    field.value = 'yes'
    validator(field, {'other': 'yes'})


def test_validate_regexp():
    validator = validate_regexp('^[a-z]{3}$', flags=0)

    field.value = '123'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'abcd'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'abc'
    validator(field, {})


def test_validate_function():
    def verify(value, check):
        return value == check

    validator = validate_function(verify, check='tim')

    field.value = 'abcd'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'tim'
    validator(field, {})


def test_validate_email():
    validator = validate_email()

    field.value = 'bad'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = '())@asdfsd.com'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'tim@().com'
    with pytest.raises(ValidationError):
        validator(field, {})

    field.value = 'tim@example.com'
    validator(field, {})

    field.value = 'tim@localhost'
    validator(field, {})
