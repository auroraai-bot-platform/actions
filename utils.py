from actions.classification_codes import (
    REGION_CODES,
    MUNICIPALITY_CODES,
    HOSPITAL_DISTRICT_CODES,
    SERVICE_CLASS_CODES,
    TARGET_GROUP_CODES,
    SERCVICE_COLLECTION_CODES
)

### SLOTS CONFIGURATIONS ###

## FIXED SLOT NAMES AND DEFAULT VALUES USED IN API CALLS ##

# Life situation meter (key) and its slot name (value):
LIFE_SITUATION_SLOTS = {
    'family': '3x10d_family',
    'finance': '3x10d_finance',
    'friends': '3x10d_friends',
    'health': '3x10d_health',
    'housing': '3x10d_housing',
    'improvement_of_strengths': '3x10d_improvement_of_strengths',
    'life_satisfaction': '3x10d_life_satisfaction',
    'resilience': '3x10d_resilience',
    'self_esteem': '3x10d_self_esteem',
    'working_studying': '3x10d_working_studying'
}

DEFAULT_LIFE_SITUATION_FEATURES = None
DEFAULT_LIFE_SITUATION_METER_VALUES = {
    'family': [],
    'finance': [],
    'friends': [],
    'health': [],
    'housing': [],
    'improvement_of_strengths': [],
    'life_satisfaction': [],
    'resilience': [],
    'self_esteem': [],
    'working_studying': []
}

# AuroraApi service recommender excepts integer values between zero and ten for features.
MIN_FEATURE_VALUE = 0
MAX_FEATURE_VALUE = 10

SEARCH_TEXT_SLOT = 'sr_param_search_text'
DEFAULT_SEARCH_TEXT_VALUE = 'palvelu'

INCLUDE_NATIONAL_SERVICES_SLOT = 'sr_filter_include_national_services'
INCLUDE_NATIONAL_SERVICES_DEFAULT_VALUE = None

RESULT_LIMIT_SLOT = 'sr_param_result_limit'
DEFAULT_RESULT_LIMIT = 5

RERANK_SLOT = 'sr_param_rerank'

DEFAULT_SESSION_ID = 'xyz-123'

# SLOT NAMES FOR API FILTER PARAMETERS
REGION_FILTER_SLOT = 'sr_filter_region'
MUNICIPALITY_FILTER_SLOT = 'sr_filter_municipality'
HOSPITAL_DISTRICT_FILTER_SLOT = 'sr_filter_hospital_district'
SERVICE_CLASS_FILTER_SLOT = 'sr_filter_service_class'
TARGET_GROUP_FILTER_SLOT = 'sr_filter_target_group'
SERCVICE_COLLECTION_FILTER_SLOT = 'sr_filter_service_collection'

# FILTER CONFIGURATION DICTIONARY
""" For each filter following parameters must be defined:
    slot_name: Fixed name of the slot which holds the value of the filter.
    codes: If the filter in api expects fixed values defined in koodistot.suomi.fi, the codes must be stored here.
    default_value: Default value of filter (not used at the moment)
    validate_codes: Whether or not slot values should be validated agains koodistot codes defined in codes.
                    If used koodistot codes are not up to date, disable validate_codes.
    use_value_over_key: If koodistot codes dictionary value item is the one filter needs as input instead of key.
"""
API_FILTERS = {
    'region_filter': {
        'slot_name': REGION_FILTER_SLOT,
        'codes': REGION_CODES,
        'default_value': None,
        'validate_codes': True,
        'use_value_over_key': False
    },
    'municipality_filter': {
        'slot_name': MUNICIPALITY_FILTER_SLOT,
        'codes': MUNICIPALITY_CODES,
        'default_value': None,
        'validate_codes': True,
        'use_value_over_key': False
    },
    'hospital_district_filter': {
        'slot_name': HOSPITAL_DISTRICT_FILTER_SLOT,
        'codes': HOSPITAL_DISTRICT_CODES,
        'default_value': None,
        'validate_codes': True,
        'use_value_over_key': False
    },
    'service_class_filter': {
        'slot_name': SERVICE_CLASS_FILTER_SLOT,
        'codes': SERVICE_CLASS_CODES,
        'default_value': None,
        'validate_codes': True,
        'use_value_over_key': True
    },
    'target_group_filter': {
        'slot_name': TARGET_GROUP_FILTER_SLOT,
        'codes': TARGET_GROUP_CODES,
        'default_value': None,
        'validate_codes': True,
        'use_value_over_key': False
    },
    'service_collection_filter': {
        'slot_name': SERCVICE_COLLECTION_FILTER_SLOT,
        'codes': SERCVICE_COLLECTION_CODES,
        'default_value': None,
        'validate_codes': False,
        'use_value_over_key': False
    }
}

# FUNCTIONAL SLOTS (are needed when recommendations are presented in botfront)
RECOMMENDATIONS_SLOT = 'sr_recommended_services'

BUTTON_PRESSED_SLOT = 'sr_button_pressed'
BUTTON_PRESSED_INTENT = 'sr.buttonpressed'

SHOW_API_CALL_PARAMETERS_SLOT = 'sr_show_request_parameters'

# DEMONSTRATING NEW FUNCTIONALITY - SLOTS (api cannot use these at the moment)
WHITELIST_SLOT = 'sr_whitelist'
BLACKLIST_SLOT = 'sr_blacklist'

# todo: Add responses for different languages.
API_ERROR_MESSAGE = 'En valitettavasti pysty hakemaan palveluita juuri nyt.'
NO_SERVICES_MESSAGE = 'En löytänyt yhtään tilanteeseesi sopivaa palvelua.'
NO_SERVICE_CHANNELS_MESSAGE = 'Palvelulla ei toistaiseksi ole yhtään palvelukanavaa.'
NO_SERVICE_CHANNEL_ITEMS_MESSAGE = '...tätä tietoa ei ole saatavilla.'

class CodeFilter:
    """ Filter object for each koodisto classification codes.
        This class is used to validate if user input in filter
        slot is valid and can be sent to api as is or needs
        preparation."""
    def __init__(self, codes: dict, slot_name: str, default_value: str, validate_codes: bool, use_value_over_key: bool):
        self.codes = codes
        self.slot = slot_name
        self.default_value = default_value
        self.validate_codes = validate_codes
        self.use_value_over_key = use_value_over_key

    def validate_selection(self, selection):
        if isinstance(selection, list):
            checked_selection = self.check_codes(selection)
        elif isinstance(selection, str):
            checked_selection = self.check_codes([selection])
        else:
            return None

        if checked_selection:
            if self.use_value_over_key:
                value_based_selection = self.value_over_key(checked_selection)
                return value_based_selection
            else:
                return checked_selection
        else:
            return None

    def check_codes(self, selection: list):
        """ Go through codes selected and check if they exists in the codes dictionary.
            Pass validation if filter settings say so."""
        if not self.validate_codes:
            return selection

        for code in selection:
            if code in self.codes.keys():
                continue
            else:
                selection.remove(code)
        return selection

    def value_over_key(self, selection: list):
        """ If api parameter is based on code values instead of code key,
        we must select parameter value accordingly."""
        selection_values = []

        for code in selection:
            try:
                value = self.codes[code]
                selection_values.append(value)
            except KeyError:
                continue

        return selection_values

class Filters:
    """ Generates filter objects as initialization. """
    def __init__(self):
        self.filters = dict()
        self.make_filters()

    def make_filters(self):
        for key, value in API_FILTERS.items():
            self.filters[key] = CodeFilter(codes=API_FILTERS[key]['codes'],
                                           slot_name=API_FILTERS[key]['slot_name'],
                                           default_value=API_FILTERS[key]['default_value'],
                                           validate_codes=API_FILTERS[key]['validate_codes'],
                                           use_value_over_key=API_FILTERS[key]['use_value_over_key'])
