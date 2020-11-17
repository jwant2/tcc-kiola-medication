from django.utils.translation import ugettext_noop, pgettext
from kiola.cares import const as cares_const
from django.utils.translation import ugettext_lazy as _, ugettext_noop, pgettext_lazy, get_language

ADVERSE_REACTION_TYPE__ALLERGY = ugettext_noop("Allergy")
ADVERSE_REACTION_TYPE__SIDE_EFFECT = ugettext_noop("Side Effect")
ADVERSE_REACTION_TYPE__INTOLERANCE = ugettext_noop("Intolerance")
ADVERSE_REACTION_TYPE__IDIOSYNCRATIC = ugettext_noop("Idiosyncratic")
ADVERSE_REACTION_TYPE__UNKNOWN = ugettext_noop("Unknown")
