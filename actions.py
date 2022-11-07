from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset, Restarted
from actions.servicerec.api import ServiceRecommenderAPI, SessionAttributesAPI
import json
from urllib.parse import urlparse, parse_qs, urlencode
from actions.utils import Filters, find_municipality
from actions.utils import (
    LIFE_SITUATION_SLOTS,
    DEFAULT_LIFE_SITUATION_FEATURES,
    DEFAULT_LIFE_SITUATION_METER_VALUES,
    MIN_FEATURE_VALUE,
    MAX_FEATURE_VALUE,
    AGE_SLOT,
    DEFAULT_AGE_VALUE,
    MUNICIPALITY_SLOT,
    DEFAULT_MUNICIPALITY_VALUE,
    SESSION_TRANSFER_TARGET_SERVICE_SLOT,
    DEFAULT_SESSION_TRANSFER_TARGET_SERVICE,
    SEARCH_TEXT_SLOT,
    DEFAULT_SEARCH_TEXT_VALUE,
    INCLUDE_NATIONAL_SERVICES_SLOT,
    INCLUDE_NATIONAL_SERVICES_DEFAULT_VALUE,
    RESULT_LIMIT_SLOT,
    DEFAULT_RESULT_LIMIT,
    RERANK_SLOT,
    DEFAULT_SESSION_ID,
    API_FILTERS,
    RECOMMENDATIONS_SLOT,
    BUTTON_PRESSED_SLOT,
    BUTTON_PRESSED_INTENT,
    SHOW_API_CALL_PARAMETERS_SLOT,
    WHITELIST_SLOT,
    BLACKLIST_SLOT
)

af = Filters().filters


# todo: Add responses for different languages.
API_ERROR_MESSAGE = 'En valitettavasti pysty hakemaan palveluita juuri nyt.'
NO_SERVICES_MESSAGE = 'En löytänyt yhtään tilanteeseesi sopivaa palvelua.'
NO_SERVICE_CHANNELS_MESSAGE = 'Palvelulla ei toistaiseksi ole yhtään palvelukanavaa.'
NO_SERVICE_CHANNEL_ITEMS_MESSAGE = '...tätä tietoa ei ole saatavilla.'


class CarouselTemplate:

    def __init__(self, template_type: str = 'generic'):

        if template_type == 'generic':

            self.template = {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': [
                    ]
                }
            }
        # Todo: add more templates when needed.
        else:
            pass

    def add_element(self, element: object):
        self.template['payload']['elements'].append(element.element)
        return self.template

class CarouselElement:

    def __init__(self, service_id: str, name: str, image_url: str = None):
        self.service_id = service_id
        self.payload_body = f'/{BUTTON_PRESSED_INTENT}' + \
                            '{"' + f'{BUTTON_PRESSED_SLOT}' + \
                            '":"' + f'{self.service_id}'

        self.element = {
            'title': name,
            'image_url': image_url,
            'buttons': [{
                'title': 'Lisätietoja',
                'type': 'postback',
                'payload': self.payload_body + '_moreinfo"}'
                },
                {
                'title': 'Yhteystiedot',
                'type': 'postback',
                'payload': self.payload_body + '_contactinfo"}'
                },
                {
                'title': 'Palvelun kotisivu',
                'type': 'postback',
                'payload': self.payload_body + '_homepage"}'
                }
            ]
        }

class ApiParams:
    def __init__(self):
        self.session_id = DEFAULT_SESSION_ID

        self.params = {}

    def add_params(self, **kwargs):
        """ Updates api parameters """

        for arg in kwargs:
            if isinstance(kwargs[arg], bool):
                self.params[arg] = kwargs[arg]
            elif not kwargs[arg]:
                continue
            else:
                self.params[arg] = kwargs[arg]
        return self.params

class ApiFilters:
    def __init__(self):
        self.filters = {}

    def add_filters(self, **kwargs):
        """ Updates api filters """

        for arg in kwargs:
            if not kwargs[arg]:
                if isinstance(kwargs[arg], (int, float)):
                    self.filters[arg] = kwargs[arg]
                else:
                    continue
            else:
                self.filters[arg] = kwargs[arg]
        return self.filters

class ValidateSlots:

    @staticmethod
    def validate_result_limit(tracker):
        """
        Will check if result limit slot has a proper value. Otherwise default limit is used.
        """
        try:
            limit = int(tracker.get_slot(RESULT_LIMIT_SLOT))
        except:
            limit = DEFAULT_RESULT_LIMIT
        return limit

    @staticmethod
    def validate_age(tracker):
        """
        Will check if age slot has a proper value.
        """
        try:
            age = int(tracker.get_slot(AGE_SLOT))
        except:
            age = DEFAULT_AGE_VALUE
        return age

    @staticmethod
    def validate_municipality(tracker):
        """
        Will check if municipality slot has a proper value, both
        code or name of municipality is accepted. Note that
        municipality filter slot is different and is validated by its
        own class method as it may contain list of values.
        """
        try:
            slot_content = tracker.get_slot(MUNICIPALITY_SLOT)
            if isinstance(slot_content, str):
                code = find_municipality(slot_content)
        except:
            code = DEFAULT_MUNICIPALITY_VALUE
        return code

    @staticmethod
    def validate_search_text(tracker):
        """
        Will check if search text slot has a value. Otherwise default value is used.
        """
        try:
            search_text = str(tracker.get_slot(SEARCH_TEXT_SLOT))
        except:
            search_text = DEFAULT_SEARCH_TEXT_VALUE
        return search_text

    @staticmethod
    def validate_feat(tracker):
        """ Creates life situation feature vector by trying to fetch all slots
            values determined in LIFE_SITUATION_SLOTS. In case a feature slot has
            invalid value it has no effect on recommendations.
        """

        feats = {}
        for key in LIFE_SITUATION_SLOTS.keys():
            try:
                slot_value = int(tracker.get_slot(LIFE_SITUATION_SLOTS[key]))
                if MAX_FEATURE_VALUE >= slot_value >= MIN_FEATURE_VALUE:
                    feats[key] = [slot_value]
                else:
                    continue
            except:
                continue

        if not bool(feats):
            feats = DEFAULT_LIFE_SITUATION_METER_VALUES

        return feats

    @staticmethod
    def validate_list_slot(tracker, codefilter):
        """
        Check if list slot has a proper value which has corresponding
        code. Otherwise the slot value does not effective factor.
        """

        try:
            slot_value = tracker.get_slot(codefilter.slot)
            validated_slot_value = codefilter.validate_selection(slot_value)
        except:
            return None

        return validated_slot_value

    @staticmethod
    def validate_bool_slot(tracker, slot_name):
        """
        Will check if boolean slot holds proper value. If not, filter is not used.
        """

        try:
            slot_value = tracker.get_slot(slot_name)
            if isinstance(slot_value, str):
                try:
                    int_value = int(slot_value)
                    if int_value == 1:
                        return True
                    else:
                        return False
                except:
                    if slot_value.lower() == 'yes':
                        return True
                    else:
                        return False
            if isinstance(slot_value, bool):
                return slot_value
        except:
            return None

    def validate_filters(self, tracker):
        api_filters = ApiFilters()

        api_filters.add_filters(
            include_national_services=self.validate_bool_slot(tracker, INCLUDE_NATIONAL_SERVICES_SLOT),
            municipality_codes=self.validate_list_slot(tracker, af['municipality_filter']),
            region_codes=self.validate_list_slot(tracker, af['region_filter']),
            hospital_district_codes=self.validate_list_slot(tracker, af['hospital_district_filter']),
            service_classes=self.validate_list_slot(tracker, af['service_class_filter']),
            target_groups=self.validate_list_slot(tracker, af['target_group_filter']),
            service_collections=self.validate_list_slot(tracker, af['service_collection_filter'])
        )

        return api_filters.filters

class WhiteBlackList:
  def __init__(self, services: dict):
    self.services = services

  @staticmethod
  def sort_by_weight(elem):
    return elem[3]

  def resort_by_match(self, white: str, black: str):
    weighted_services = []
    ids = [service['service_id'] for service in self.services['recommended_services']]
    names = [service['service_name'] for service in self.services['recommended_services']]
    descriptions = [service['service_description'] for service in self.services['recommended_services']]

    for sid, name, desc in zip(ids, names, descriptions):
        if white in desc:
            weighted_services.append((sid, name, desc, 1))
        else:
            if black in desc:
                weighted_services.append((sid, name, desc, 1000))
            else:
                weighted_services.append((sid, name, desc, 2))

    weighted_services.sort(key=self.sort_by_weight)
    new_services = {'recommended_services': []}
    for x in weighted_services:
        new_services['recommended_services'].append({'service_id': x[0],
                                                     'service_name': x[1],
                                                     'service_description': x[2],
                                                     'weight': x[3]})

    return new_services

class ActionShowInfo(Action):
    """
    Prints out info user has chosen from carousel.
    """
    def name(self):
        return 'action_show_info'

    @staticmethod
    def remove_duplicates(records: list):
        out = []
        for r in records:
            if r not in out:
                out.append(r)
        return out

    @staticmethod
    def get_service(service_list, service_id):
        for service in service_list['recommended_services']:
            if service['service_id'] == service_id:
                return service

    def empty_message(self, dispatcher):
        dispatcher.utter_message(NO_SERVICE_CHANNEL_ITEMS_MESSAGE)

    def run(self, dispatcher, tracker, domain):
        services = tracker.get_slot(RECOMMENDATIONS_SLOT)
        selection = tracker.get_slot(BUTTON_PRESSED_SLOT)
        service_id, button_id = str(selection).split('_')
        service = self.get_service(services, service_id)

        if button_id == 'contactinfo':
            if service['service_channels']:
                dispatcher.utter_message(template=f'{service["service_name"]} -palvelun palvelukanavien yhtestiedot:')
                for record in service['service_channels']:
                    emails = '\n'.join(map(str, self.remove_duplicates(record['emails'])))
                    phone_numbers = '\n'.join(map(str, self.remove_duplicates(record['phone_numbers'])))
                    address = record['address']
                    dispatcher.utter_message(template=f'{record["service_channel_name"]}: ')
                    if emails:
                        dispatcher.utter_message(template=f'Sähköposti: {emails}')
                    if phone_numbers:
                        dispatcher.utter_message(template=f'Puhelin: {phone_numbers}')
                    if address:
                        dispatcher.utter_message(template=f'Osoite: {address}')
            else:
                dispatcher.utter_message(NO_SERVICE_CHANNELS_MESSAGE)

        if button_id == 'moreinfo':
            if service['service_channels']:
                dispatcher.utter_message(template=f'{service["service_name"]} -palvelun palvelukanavien lisätiedot:')
                for record in service['service_channels']:
                    hours = '\n'.join(map(str, record['service_hours']))
                    dispatcher.utter_message(template=f'{record["service_channel_name"]}: ')
                    if hours:
                        dispatcher.utter_message(template=f'Aukioloajat: {hours}')
                    else:
                        self.empty_message(dispatcher)
            else:
                dispatcher.utter_message(NO_SERVICE_CHANNELS_MESSAGE)

        if button_id == 'homepage':
            if service['service_channels']:
                dispatcher.utter_message(template=f'{service["service_name"]} -palvelun palvelukanavien kotisivut:')
                for record in service['service_channels']:
                    web_pages = '\n'.join(map(str, record['web_pages']))
                    dispatcher.utter_message(template=f'{record["service_channel_name"]}: ')
                    if web_pages:
                        dispatcher.utter_message(template=f'Web-sivut: {web_pages}')
                    else:
                        self.empty_message(dispatcher)
            else:
                dispatcher.utter_message(NO_SERVICE_CHANNELS_MESSAGE)

        return []

class ServiceListByLifeSituation(Action, ValidateSlots):
    """
    Get service recommendations based on slot values collected by the bot.
    Tracker store slots must follow naming convention determined in
    LIFE_SITUATION_SLOTS dictionary to have an effect on recommendation.
    """

    def name(self):
        return 'action_service_list_by_life_situation'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store, validates slot values,
        and calls service recommender api to fetch recommended services based on
        the recommend service method.
        Outputs recommendations as a list to the bot interface.
        Results slot with recommended services.
        """

        api_params = ApiParams()

        api_params.add_params(limit=self.validate_result_limit(tracker),
                              rerank=ValidateSlots.validate_bool_slot(tracker, RERANK_SLOT),
                              life_situation_meters=self.validate_feat(tracker),
                              service_filters=self.validate_filters(tracker))

        if show_request_parameters(tracker, SHOW_API_CALL_PARAMETERS_SLOT):
            dispatcher.utter_message(f'hakuparametrit: {str(json.dumps(api_params.params))}')

        try:
            api = ServiceRecommenderAPI()

            response = api.get_recommendations(params=api_params.params,
                                               method='recommend_service')

            if response.ok:
                services = response.json()

                ids = [service['service_id'] for service in services['recommended_services']]
                names = [service['service_name'] for service in services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    dispatcher.utter_message(template=f'Palvelu: {name}',
                                             buttons=element.element['buttons'])
            else:
                dispatcher.utter_message(template=API_ERROR_MESSAGE)
        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

        return [SlotSet(RECOMMENDATIONS_SLOT, services)]

class ServiceCarouselByLifeSituation(Action, ValidateSlots):
    """
    Get service recommendations based on slot values collected by the bot.
    Tracker store slots must follow naming convention determined in
    LIFE_SITUATION_SLOTS dictionary to have an effect on recommendation.
    """

    def name(self):
        return 'action_service_carousel_by_life_situation'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store, validates slot values,
        and calls service recommender api to fetch recommended services based on
        the recommend service method.
        Outputs recommendations as a carousel to the bot interface.
        Results slot with recommended services.
        """

        api_params = ApiParams()

        api_params.add_params(limit=self.validate_result_limit(tracker),
                              rerank=ValidateSlots.validate_bool_slot(tracker, RERANK_SLOT),
                              life_situation_meters=self.validate_feat(tracker),
                              service_filters=self.validate_filters(tracker))

        if show_request_parameters(tracker, SHOW_API_CALL_PARAMETERS_SLOT):
            dispatcher.utter_message(f'hakuparametrit: {str(json.dumps(api_params.params))}')

        try:
            api = ServiceRecommenderAPI()

            response = api.get_recommendations(params=api_params.params,
                                               method='recommend_service')

            if response.ok:
                services = response.json()

                ids = [service['service_id'] for service in services['recommended_services']]
                names = [service['service_name'] for service in services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                ct = CarouselTemplate()

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    ct.add_element(element)

                dispatcher.utter_message(attachment=ct.template)
            else:
                dispatcher.utter_message(template=API_ERROR_MESSAGE)
        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

        return [SlotSet(RECOMMENDATIONS_SLOT, services)]

class ServiceListByTextSearch(Action, ValidateSlots):
    """
    Get service recommendations based on unstructured text input.
    Presents recommended services as a list.
    """

    def name(self):
        return 'action_service_list_by_text_search'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store, validates slot values,
        and calls service recommender api to fetch recommended services based on
        the text search method.
        Outputs recommendations as a list to the bot interface.
        Results slot with recommended services.
        """

        api_params = ApiParams()

        api_params.add_params(limit=self.validate_result_limit(tracker),
                              rerank=ValidateSlots.validate_bool_slot(tracker, RERANK_SLOT),
                              search_text=self.validate_search_text(tracker),
                              service_filters=self.validate_filters(tracker))

        if show_request_parameters(tracker, SHOW_API_CALL_PARAMETERS_SLOT):
            dispatcher.utter_message(f'hakuparametrit: {str(json.dumps(api_params.params))}')

        try:
            api = ServiceRecommenderAPI()

            response = api.get_recommendations(params=api_params.params,
                                               method='text_search')

            if response.ok:
                services = response.json()

                ids = [service['service_id'] for service in services['recommended_services']]
                names = [service['service_name'] for service in services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    dispatcher.utter_message(template=f'Palvelu: {name}',
                                             buttons=element.element['buttons'])
            else:
                dispatcher.utter_message(template=API_ERROR_MESSAGE)
        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

        return [SlotSet(RECOMMENDATIONS_SLOT, services)]

class ServiceCarouselByTextSearch(Action, ValidateSlots):
    """
    Get service recommendations based on unstructured text input.
    Presents recommended services as a carousel.
    """

    def name(self):
        return 'action_service_carousel_by_text_search'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store, validates slot values,
        and calls service recommender api to fetch recommended services based on
        the text search method.
        Outputs recommendations as a carousel to the bot interface.
        Results slot with recommended services.
        """

        api_params = ApiParams()

        api_params.add_params(limit=self.validate_result_limit(tracker),
                              rerank=ValidateSlots.validate_bool_slot(tracker, RERANK_SLOT),
                              search_text=self.validate_search_text(tracker),
                              service_filters=self.validate_filters(tracker))

        if show_request_parameters(tracker, SHOW_API_CALL_PARAMETERS_SLOT):
            dispatcher.utter_message(f'hakuparametrit: {str(json.dumps(api_params.params))}')

        try:
            api = ServiceRecommenderAPI()

            response = api.get_recommendations(params=api_params.params,
                                               method='text_search')

            if response.ok:
                services = response.json()

                ids = [service['service_id'] for service in services['recommended_services']]
                names = [service['service_name'] for service in services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                ct = CarouselTemplate()

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    ct.add_element(element)

                dispatcher.utter_message(attachment=ct.template)
            else:
                dispatcher.utter_message(template=API_ERROR_MESSAGE)
        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

        return [SlotSet(RECOMMENDATIONS_SLOT, services)]

class ActionRestarted(Action):
    """
    Restarts bot session.
    """
    def name(self):
        return 'action_restart_chat'

    def run(self, dispatcher, tracker, domain):
        return[Restarted()]

class ActionSlotReset(Action):
    """
    Resets all slots to an original state.
    """
    def name(self):
        return 'action_slot_reset'

    def run(self, dispatcher, tracker, domain):
        return[AllSlotsReset()]

def show_request_parameters(tracker, slot):
    slot_value = ValidateSlots.validate_bool_slot(tracker, slot)
    if not slot_value:
        return False
    return slot_value
""" -----------------------------------------------------------------------
    Down below actions are bot specific demos or use case specific actions
    rather than generic ones above. 
    Following actions exists for the demo purpose:
    - ServiceDemo
    - HNRedirectAction
    - WhiteBlackListByTextSearch
    - WhiteBlackListByTextSearchSort
    -----------------------------------------------------------------------
"""

class ServiceDemo(Action, ValidateSlots):
    """
    Service recommendation using free text search demo action.
    Slots are collected but not used to make the search
    """

    def name(self):
        return 'action_service_demo'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store and makes a customized api call
        to fetch wanted services
        """

        try:
            toimiala = str(tracker.get_slot('toimiala'))
        except:
            toimiala = 'kauneudenhoito'

        try:
            kunta = str(tracker.get_slot('kunta')).lower().capitalize()
            value_list = list(MUNICIPALITY_CODES.values())
            key_list = list(MUNICIPALITY_CODES.keys())
            code = key_list[value_list.index(kunta)]
        except:
            code = '297'

        # parameters here are hard coded to get the wanted results for demo purposes
        params = {
        'search_text': 'terveyden suojelu laki ilmoitus kuopiossa',
        'service_filters': {
            'include_national_services': False,
            'municipality_codes': [code],
            'service_classes': ['http://uri.suomi.fi/codelist/ptv/ptvserclass2/code/P23']
            },
        'limit':int(3)
        }

        # Enable if you want to display actual parameters sent to api!
        dispatcher.utter_message(f'hakuparametrit: {str(params)}')

        try:
            api = ServiceRecommenderAPI()
            response = api.get_recommendations(params=params,
                                               method='text_search')

            if response.ok:
                services = response.json()
                ids = [service['service_id'] for service in services['recommended_services']]
                names = [service['service_name'] for service in services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    dispatcher.utter_message(template=f'Palvelu: {name}',
                                            buttons=element.element['buttons'])
            else:
                dispatcher.utter_message(template=API_ERROR_MESSAGE)
                dispatcher.utter_message(str(response))

        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

        return[SlotSet(RECOMMENDATIONS_SLOT, services)]

class HNRedirectAction(Action):
    """
    Determines whether the user is entitled to services in huolehtivat nuoret case
    """

    def name(self):
        return 'action_hn_redirect'

    def run(self, dispatcher, tracker, domain):
        on_tampereella = tracker.get_slot('hn_asuu_tre_alue')
        on_nuori = tracker.get_slot('hn_on_13_17v')
        if on_tampereella and on_nuori:
            hn_score = 0
            if tracker.get_slot('hn_läheinen_pärjää'):
                hn_score += 1
            score_slots_text = ['hn_huolehtii', 'hn_vastuu', 'hn_huolen_vaikutus','hn_syyllisyys']
            for slot in score_slots_text:
                slot_value = str(tracker.get_slot(slot)).lower()
                if slot_value == 'kyllä' or slot_value == 'toisinaan' or slot_value == 'jonkin verran':
                    hn_score += 1
            if hn_score >= 2:
                dispatcher.utter_message(template="utter_hn_palvelun_piirissä")
                return []
        dispatcher.utter_message(template="utter_hn_ei_palvelun_piirissä")
        return []

class WhiteBlackListByTextSearch(Action, ValidateSlots):
    """
    Get service recommendations based on text search and whitelist/blacklist items.
    Purpose is to call aurora api service recommendation endpoint with blacklist and whitelist
    parameters even though they are not used yet. Since the recommender cannot yet use
    these parameters it will result an error. Error message is passed to the bot so that
    it is transparent to the user.
    """

    def name(self):
        return 'action_service_list_by_whiteblack_text_search'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store, validates slot values,
        and calls service recommender api to fetch recommended services. Blacklist
        and whitelist are passed also with the request eventhough endpoint doesn't
        yet support them.
        Outputs recommendations as a list to the bot interface.
        Results slot with recommended services.
        """

        api_params = ApiParams()

        api_params.add_params(limit=self.validate_result_limit(tracker),
                              search_text=self.validate_search_text(tracker),
                              service_filters=self.validate_filters(tracker))

        try:
            whitelist_text = tracker.get_slot(WHITELIST_SLOT)
            blacklist_text = tracker.get_slot(BLACKLIST_SLOT)
        except:
            whitelist_text = 'NULL'
            blacklist_text = 'NULL'

        if not whitelist_text:
            whitelist_text = 'NULL'
        if not blacklist_text:
            blacklist_text = 'NULL'

        api_params.params['whitelist'] = whitelist_text
        api_params.params['blacklist'] = blacklist_text

        if show_request_parameters(tracker, SHOW_API_CALL_PARAMETERS_SLOT):
            dispatcher.utter_message(f'hakuparametrit: {str(json.dumps(api_params.params))}')

        try:
            api = ServiceRecommenderAPI()

            response = api.get_recommendations(params=api_params.params,
                                               method='text_search')

            if response.ok:
                services = response.json()
                wh = WhiteBlackList(services)
                resorted_services = wh.resort_by_match(white=whitelist_text, black=blacklist_text)
                new_services = resorted_services

                ids = [service['service_id'] for service in new_services['recommended_services']]
                names = [service['service_name'] for service in new_services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    dispatcher.utter_message(template=f'Palvelu: {name}',
                                             buttons=element.element['buttons'])

                return [SlotSet(RECOMMENDATIONS_SLOT, services)]

            else:
                dispatcher.utter_message(template=response.text)
        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

class WhiteBlackListByTextSearchSort(Action, ValidateSlots):
    """
    Get service recommendations based on text search and whitelist/blacklist items.
    Purpose is to call aurora api service recommendation endpoint and sort results
    with blacklist and whitelist items in custom sorter.
    """

    def name(self):
        return 'action_service_list_by_whiteblack_text_search_sorted'

    def run(self, dispatcher, tracker, domain):
        """
        Fetches slot values from the bot tracker store, validates slot values,
        and calls service recommender api to fetch recommended services. Recommendations
        are sorted by simple sorter function which uses blacklisted and whitelisted slot
        values for sorting services.
        """

        api_params = ApiParams()

        api_params.add_params(limit=self.validate_result_limit(tracker),
                              search_text=self.validate_search_text(tracker),
                              service_filters=self.validate_filters(tracker))

        try:
            whitelist_text = tracker.get_slot(WHITELIST_SLOT)
            blacklist_text = tracker.get_slot(BLACKLIST_SLOT)
        except:
            whitelist_text = 'NULL'
            blacklist_text = 'NULL'

        if not whitelist_text:
            whitelist_text = 'NULL'
        if not blacklist_text:
            blacklist_text = 'NULL'

        # Enable if you want to display actual parameters sent to api!
        if show_request_parameters(tracker, SHOW_API_CALL_PARAMETERS_SLOT):
            dispatcher.utter_message(f'hakuparametrit: {str(json.dumps(api_params.params))}')
            dispatcher.utter_message(f'tulosten sorttausparametrit: whitelist: {whitelist_text}, blacklist: {blacklist_text} ')

        try:
            api = ServiceRecommenderAPI()

            response = api.get_recommendations(params=api_params.params,
                                               method='text_search')

            if response.ok:
                services = response.json()
                wh = WhiteBlackList(services)
                resorted_services = wh.resort_by_match(white=whitelist_text, black=blacklist_text)
                new_services = resorted_services

                ids = [service['service_id'] for service in new_services['recommended_services']]
                names = [service['service_name'] for service in new_services['recommended_services']]

                if not ids:
                    dispatcher.utter_message(NO_SERVICES_MESSAGE)
                else:
                    dispatcher.utter_message('Palvelusuositukset:')

                for service_id, name in zip(ids, names):
                    element = CarouselElement(service_id, name)
                    dispatcher.utter_message(template=f'Palvelu: {name}',
                                             buttons=element.element['buttons'])
            else:
                dispatcher.utter_message(template=API_ERROR_MESSAGE)
        except ConnectionError:
            services = None
            dispatcher.utter_message(template=API_ERROR_MESSAGE)

        return [SlotSet(RECOMMENDATIONS_SLOT, services)]

class FetchSessionAttributes(Action):
    """
    Get user related attributes after session transfer.
    """

    def name(self):
        return 'action_fetch_session_attributes'

    def run(self, dispatcher, tracker, domain):
        """
        Documentation
        """

        metadata = tracker.get_slot('session_started_metadata')
        auroraai_access_token = metadata['auroraaiAccessToken']

        attribute_params = {'access_token': str(auroraai_access_token)}
        session_attributes = SessionAttributesAPI()
        response = session_attributes.get_attributes(params=attribute_params)
        attributes = response.json()

        # Store all fetched data into slots (atm data can contain [age, municipality_code, life_situation_meters])

        life_situation_meters = attributes["life_situation_meters"]

        all_slots = []
        for key in life_situation_meters.keys():
            try:
                slot_item = SlotSet(LIFE_SITUATION_SLOTS[key], str(life_situation_meters[key][0]))
                all_slots.append(slot_item)
            except:
                pass

        try:
            all_slots.append(SlotSet(MUNICIPALITY_SLOT, str(attributes["municipality_code"])))
        except:
            pass

        try:
            all_slots.append(SlotSet(AGE_SLOT, str(attributes["age"])))
        except:
            pass

        return all_slots

class PostSessionAttributes(Action, ValidateSlots):
    """
    Post user related attributes before session transfer.
    """

    def name(self):
        return 'action_post_session_attributes'

    def run(self, dispatcher, tracker, domain):
        """
        Documentation
        """

        api_params = ApiParams()
        attributes = ApiParams()

        service_channel_id = tracker.get_slot(SESSION_TRANSFER_TARGET_SERVICE_SLOT)

        attributes.add_params(age=self.validate_age(tracker),
                              life_situation_meters=self.validate_feat(tracker),
                              municipality_code=self.validate_municipality(tracker)
                              )

        api_params.add_params(service_channel_id=service_channel_id,
                              session_attributes=attributes.params
                              )

        api_for_session = SessionAttributesAPI()

        response = api_for_session.post_attributes(params=api_params.params)

        URL = response.text

        if response.ok:
            parsed_url = urlparse(URL)
            token_data = parse_qs(parsed_url.query)
            access_token = token_data['auroraai_access_token'][0]

        url_params = {'auroraai_access_token': access_token}

        """ 
        Here we need to hard code target service url for each service_channel_id 
        which can be the target. For our demo, this means testbot and palmubot. 
        In the future this uri (redirect link) will be part of service
        recommendations.
        """

        # Todo: get the redirect link from service recommendation!

        target_uris = {
            'fc66cd13-ae36-4592-b18d-e095a8d9a481': 'https://palmu.demo.aaibot.link/',
            'a24bd700-290a-41d8-b64a-8746ea20851b': 'https://testbot.demo.aaibot.link/'
        }

        link = target_uris[service_channel_id]
        session_transfer_link = link + '?' + urlencode(url_params)
        dispatcher.utter_message(session_transfer_link)

        return [SlotSet('access_token', access_token)]
