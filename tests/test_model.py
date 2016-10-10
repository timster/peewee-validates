import pytest

import peewee

from peewee_validates import ModelValidator
from peewee_validates import ValidationError

from tests.models import BasicFields
from tests.models import ComplexPerson
from tests.models import Organization
from tests.models import Person


def test_not_instance():
    with pytest.raises(AttributeError):
        ModelValidator(Person)


def assert_instance_works():
    validator = ModelValidator(Person())
    valid = validator.validate({'name': 'timster'})
    assert valid
    assert isinstance(validator.data, Person)
    assert validator.data.name == 'timster'


def test_required():
    validator = ModelValidator(Person())
    valid = validator.validate()
    assert not valid
    assert validator.errors['name'] == 'must be provided'


def test_clean():
    class TestValidator(ModelValidator):
        def clean(self, data):
            super().clean(data)
            data['name'] += 'awesome'
            return data

    validator = TestValidator(Person())
    valid = validator.validate({'name': 'tim'})
    assert valid
    assert validator.data['name'] == 'timawesome'


def test_clean_error():
    class TestValidator(ModelValidator):
        def clean(self, data):
            raise ValidationError('required')

    validator = TestValidator(Person())
    valid = validator.validate({'name': 'tim'})
    assert not valid
    assert validator.data['name'] == 'tim'
    assert validator.errors['__base__'] == 'must be provided'


def test_choices():
    validator = ModelValidator(ComplexPerson(name='tim'))

    valid = validator.validate({'organization': 1, 'gender': 'S'})
    assert not valid
    assert validator.errors['gender'] == 'must be one of the choices: M, F'
    assert 'name' not in validator.errors

    valid = validator.validate({'organization': 1, 'gender': 'M'})
    assert valid

    valid = validator.validate({'gender': 'M'})
    assert valid


def test_default():
    validator = ModelValidator(BasicFields())
    valid = validator.validate()
    assert not valid
    assert validator.data['field1'] == 'Tim'
    assert validator.errors['field2'] == 'must be provided'
    assert validator.errors['field3'] == 'must be provided'


def test_missing_related():
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))

    valid = validator.validate({'organization': 999})
    assert not valid
    assert validator.errors['organization'] == 'unable to find related object'

    valid = validator.validate()
    assert not valid
    assert validator.errors['organization'] == 'must be provided'


def test_missing_related_callable_default():
    def getorg():
        return 99

    # validator = ModelValidator(ComplexPerson(name='tim', gender='M'))
    # validator._meta.fields['organization'].default = getorg

    # valid = validator.validate()
    # assert not valid
    # assert validator.errors['organization'] == 'unable to find related object'


def test_working_related():
    org = Organization.get(id=1)
    # validator = ModelValidator(ComplexPerson(organization=1, name='tim', gender='M'))

    # valid = validator.validate()
    # assert not valid
    # assert validator.data.organization == org


def test_unique():
    person = Person(name='tim')
    person.save()

    validator = ModelValidator(Person(name='tim'))
    valid = validator.validate({'gender': 'M'})
    assert not valid
    assert validator.errors['name'] == 'must be a unique value'

    validator = ModelValidator(person)
    valid = validator.validate({'gender': 'M'})
    assert valid


def test_unique_index():
    obj = BasicFields(field1='one', field2='two', field3='three')
    obj.save()

    validator = ModelValidator(BasicFields(field1='one', field2='two', field3='three'))
    valid = validator.validate()
    assert not valid
    assert validator.errors['field1'] == 'fields must be unique together'
    assert validator.errors['field2'] == 'fields must be unique together'

    validator = ModelValidator(obj)
    valid = validator.validate()
    assert valid
