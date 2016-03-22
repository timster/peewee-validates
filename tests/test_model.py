import pytest

import peewee

from peewee_validates import PeeweeField
from peewee_validates import ModelValidator
from peewee_validates import ValidationError

from tests.models import BasicFields
from tests.models import ComplexPerson
from tests.models import Organization
from tests.models import Person


def test_not_instance():
    with pytest.raises(AttributeError):
        ModelValidator(Person)

    with pytest.raises(AttributeError):
        PeeweeField(Person, peewee.CharField())


def assert_instance_works():
    validator = ModelValidator(Person())
    rv = validator.validate({'name': 'timster'})
    assert not rv.errors
    assert isinstance(rv.data, Person)
    assert rv.data.name == 'timster'


def test_required():
    validator = ModelValidator(Person())
    rv = validator.validate()
    assert rv.errors['name'] == 'required field'


def test_clean():
    class TestValidator(ModelValidator):
        def clean(self, data):
            super().clean(data)
            data['name'] += 'awesome'
            return data

    validator = TestValidator(Person())
    rv = validator.validate({'name': 'tim'})
    assert rv.data['name'] == 'timawesome'
    assert not rv.errors


def test_clean_error():
    class TestValidator(ModelValidator):
        def clean(self, data):
            raise ValidationError('required')

    validator = TestValidator(Person())
    rv = validator.validate({'name': 'tim'})
    assert rv.data['name'] == 'tim'
    assert rv.errors['__base__'] == 'required field'


def test_choices():
    validator = ModelValidator(ComplexPerson(name='tim'))

    rv = validator.validate({'organization': 1, 'gender': 'S'})
    assert rv.errors['gender'] == 'must be one of the choices: M, F'
    assert 'name' not in rv.errors

    rv = validator.validate({'organization': 1, 'gender': 'M'})
    rv = validator.validate({'gender': 'M'})
    assert not rv.errors


def test_default():
    validator = ModelValidator(BasicFields())
    rv = validator.validate()

    assert rv.data['field1'] == 'Tim'
    assert rv.errors['field2'] == 'required field'
    assert rv.errors['field3'] == 'required field'


def test_missing_related():
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))

    rv = validator.validate({'organization': 999})
    assert rv.errors['organization'] == 'unable to find related object'

    rv = validator.validate()
    assert rv.errors['organization'] == 'required field'


def test_missing_related_callable_default():
    def getorg():
        return 99

    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))
    validator._meta.fields['organization'].default = getorg

    rv = validator.validate()
    assert rv.errors['organization'] == 'unable to find related object'


def test_working_related():
    org = Organization.get(id=1)
    validator = ModelValidator(ComplexPerson(organization=1, name='tim', gender='M'))

    rv = validator.validate()
    assert rv.data.organization == org


def test_unique():
    person = Person(name='tim')
    person.save()

    validator = ModelValidator(Person(name='tim'))
    rv = validator.validate({'gender': 'M'})
    assert rv.errors['name'] == 'must be a unique value'

    validator = ModelValidator(person)
    rv = validator.validate({'gender': 'M'})
    assert not rv.errors


def test_unique_index():
    obj = BasicFields(field1='one', field2='two', field3='three')
    obj.save()

    validator = ModelValidator(BasicFields(field1='one', field2='two', field3='three'))
    rv = validator.validate()
    assert rv.errors['field1'] == 'fields must be unique together'
    assert rv.errors['field2'] == 'fields must be unique together'

    validator = ModelValidator(obj)
    rv = validator.validate()
    assert not rv.errors
