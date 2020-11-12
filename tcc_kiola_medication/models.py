from django.db import models

#from healthy_heart.models import *

import kiola.kiola_med.models
from kiola.kiola_med.models import *

#from healthy_heart.models import Compound

class MedCompound(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class MedCompoundTwo(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Presc(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


