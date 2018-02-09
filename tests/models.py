import peewee
try:
    M2M_RELATED = 'related_name'
    from playhouse.fields import ManyToManyField
except ImportError:
    M2M_RELATED = 'backref'
    from peewee import ManyToManyField

database = peewee.SqliteDatabase(':memory:')


def getname():
    return 'Tim'


class BasicFields(peewee.Model):
    field1 = peewee.CharField(default=getname)
    field2 = peewee.CharField()
    field3 = peewee.CharField()

    class Meta:
        database = database
        indexes = (
            (('field1', 'field2'), True),
            (('field3',), False),
        )


class Organization(peewee.Model):
    name = peewee.CharField(null=False)

    class Meta:
        database = database


class PayGrade(peewee.Model):
    name = peewee.CharField(null=False)

    class Meta:
        database = database


class Person(peewee.Model):
    name = peewee.CharField(null=False, max_length=5, unique=True)

    class Meta:
        database = database


class ComplexPerson(Person):
    GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'))
    gender = peewee.CharField(choices=GENDER_CHOICES)

    organization = peewee.ForeignKeyField(Organization, null=False)
    pay_grade = peewee.ForeignKeyField(PayGrade, null=True)

    class Meta:
        database = database
        indexes = (
            (('gender', 'name'), True),
            (('name', 'organization'), True),
        )


class Student(peewee.Model):
    name = peewee.CharField(max_length=10)

    class Meta:
        database = database


class Course(peewee.Model):
    name = peewee.CharField(max_length=10)

    params = {M2M_RELATED: 'courses'}
    students = ManyToManyField(Student, **params)

    class Meta:
        database = database


Organization.create_table(fail_silently=True)
PayGrade.create_table(fail_silently=True)
ComplexPerson.create_table(fail_silently=True)
Person.create_table(fail_silently=True)
BasicFields.create_table(fail_silently=True)

Student.create_table(fail_silently=True)
Course.create_table(fail_silently=True)
Course.students.get_through_model().create_table(fail_silently=True)

organization = Organization(name='main')
organization.save()
