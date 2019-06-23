from .xml2dict import xml2dict
from .errors import DrsReturnError, DrsParserError


class DrsResponse:
    """
    The DrsResponse object deals with the (pretty convoluted) xml response of the Doctorsender API
    """

    def __init__(self, res):
        """
        Initialize a DrsResponse object with an API return
        :param res: A requests Response object, containing the response of an Doctorsender API call
        """
        self.xml = res.content
        self._xml2dict()

    @property
    def content(self):
        """
        :return: Returns the inner content of the API response (remove all unnecessary stuff around
        """
        return self._drs_reduce_dict()

    def _xml2dict(self):
        """
        Sets a dict property that contains the full response converted into a dictionary
        """
        d = xml2dict(self.xml)
        self.dict = self._remove_env_str(d)

    def _key_value(self, ele):
        if type(ele) == dict:
            if type(ele['item']) == dict:
                # One
                return {ele['item']['key']: ele['item']['value']}

            # Case i.e. for dsIpGroupGetNames
            elif type(ele['item']) == str:
                return ele['item']

            # In some cases (e.g. getting all categories, the result is a list of id and name of each object)
            elif type(ele['item']) == list:
                # Case UserLists
                if ele['item'][0]['item']['key'] == 'listName':
                    k = ele['item'][0]['item']['value']
                    v = dict()
                    for kv_pair in ele['item']:
                        # The listname is already the key of each user list dict, so we exclude it from the value dict
                        if kv_pair['item']['value'] != k:
                            v.update(self._key_value(kv_pair))

                # Case languages, categories, countries
                else:
                    k = ele['item'][0]['item']['value']
                    for kv_pair in ele['item']:
                        if kv_pair['item']['key'] in {'name', 'language'}:
                            v = kv_pair['item']['value']

                return {k: v}
            else:
                raise DrsParserError

        elif type(ele) == list:
            res_dict = dict()
            for i, child in enumerate(ele):
                # Returns an have multiple shapes. dsSettingsGetAllFromEmail e.g. returns
                try:
                    res_dict.update(self._key_value(child))
                except (TypeError, ValueError):
                    res_dict.update({i: ele[i]['item']})
            return res_dict

        elif type(ele) == str:
            return ele

        else:
            print(ele)
            print(type(ele))

    def _drs_reduce_dict(self):
        # Remove the first layer
        res_list = self.dict['Envelope']['Body']['{ns1}webserviceResponse']['webserviceReturn']

        for i, sub_dict in enumerate(res_list):

            # Check for the error value, if there is an error, the error message is in the next dict in the dict-list
            if sub_dict['item']['key'] == 'error':
                if sub_dict['item']['value'] == 'true':
                    raise DrsReturnError(res_list[i + 1]['item']['value'])

            elif sub_dict['item']['key'] == 'msg':
                res_dict = self._key_value(sub_dict['item']['value'])

        return res_dict

    def _remove_env_str(self, d):
        for k, v in d.items():
            if type(v) == dict:
                v = self._remove_env_str(v)

            if '{http://schemas.xmlsoap.org/soap/envelope/}' in k:
                d[k.replace('{http://schemas.xmlsoap.org/soap/envelope/}', '')] = d.pop(k)

            return d
