import json
import requests
import datetime as dt

from .response import DrsResponse
from .errors import *
from .statics import countries, languages, categories


class DoctorSenderClient:
    def __init__(self, user, token):
        self.user = user
        self.token = token
        self.url = 'https://soapwebservice.doctorsender.com/soapserver.php'
        self.ips = self._ip_groups()  # Should always be "default', call to ensure that user and token are valid

    def _construct_body(self, methode, data, ur_type):
        if data:
            data = f"""<data SOAP-ENC:arrayType="xsd:ur-type[{ur_type}]" xsi:type="SOAP-ENC:Array">
                {data}
            </data>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
                    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns1="ns1" xmlns:ns2="http://xml.apache.org/xml-soap" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
                        <SOAP-ENV:Header>
                            <ns1:app_auth>
                                <item>
                                    <key>user</key>
                                    <value>{self.user}</value>
                                </item>
                                <item>
                                    <key>pass</key>
                                    <value>{self.token}</value>
                                </item>
                            </ns1:app_auth>
                        </SOAP-ENV:Header>
                        <SOAP-ENV:Body>
                            <ns1:webservice>
                                <method xsi:type="xsd:string">{methode}</method>
                                {data}
                            </ns1:webservice>
                        </SOAP-ENV:Body>
                    </SOAP-ENV:Envelope>
                    """

    def _post_request(self, function_name: str, data: str, ur_type: int = 3, timeout=(10,40)) -> DrsResponse:
        """Every request to the API is a POST request (because fo the SOAP standard). This method constructs the request

        :param function_name: String with API function name as per Doctorsender API docs
        :param data: String in xml format containing all additional parameters for the call
        :param ur_type: Int, either 2 or 3, different depending on how the xml data looks like
        :return: DrsResponse object
        """
        headers = {'content-type': 'application/soap+xml'}
        body = self._construct_body(function_name, data, ur_type)

        response = requests.post(self.url, data=body.encode('utf-8'), headers=headers, timeout=timeout)

        # For easier debugging and further processing, the response is handed over as a DrsResponse object
        return DrsResponse(response)

    # ------ Segment Methods ------

    def segments(self, listname: str) -> dict:
        """
        Gets all segments for a given list
        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_segments.html#a6e4e54b8a7ebac3119e9724db6668ee9
        :param listname: String with the list name as displayed in Doctorsender
        :return: Dict with segment_id as key and segment_name as value
        """
        data = f'<item xsi:type="xsd:str">{listname}</item>'
        drs_response = self._post_request('dsSegmentsGetByListName', data)

        # If the lists does not exist or does not have segments, the drsResponse content is an empty string
        if drs_response.content:
            segments = drs_response.content
        else:
            segments = {}

        return segments

    def segment_count(self, segment_id: int) -> int:
        """Count users in a segment

        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_segments.html#a6a91a9d148530550258f4c752b13517d

        :param segment_id: int with the segment id
        :return: DrsResponse object, .content returns string with the number of users in the segment
        """
        data = f'<item xsi:type="xsd:int">{segment_id}</item>'
        drs_response = self._post_request('dsGetSegmentCount', data)

        try:
            count = int(drs_response.content)
        except ValueError:
            raise DrsSegmentError("The Doctorsender segment could not be found or contains an error.")

        return count

    def create_segment(self, list_name: str, segment_name: str, is_virtual: bool = False) -> int:
        """Create a new segment without any conditions

        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_segments.html#a480ce73993491e184b94a45ac0c04f23

        :param list_name: String with the list name as displayed in Doctorsender
        :param segment_name: String of the name of the new segment
        :param is_virtual: Bool, Virtual means invisible, set to False when Segment should be visible in the GUI
        :return: Int with the new segment_id
        """
        # Virtual means invisible in the GUI
        is_virtual = int(is_virtual)
        assert is_virtual in {0, 1}, "is_virtual needs to be true or false"
        data = f"""
            <item xsi:type="xsd:str">{list_name}</item>
            <item xsi:type="xsd:str">{segment_name}</item>
            <item xsi:type="xsd:int">{is_virtual}</item>
        """
        drs_response = self._post_request('dsSegmentsNew', data)
        try:
            segment_id = int(drs_response.content)
        except DrsReturnError as e:
            raise DrsListError(f"The list {list_name} could not be found.")

        return segment_id

    def segment_add_condition(self, segment_id: int, field_name: str, comparator: str, value: str, is_or: bool = False,
                               is_date: bool = False) -> int:
        """Add a new condition to an existing segment

        Notes: Each field can only have one condition, the api (.content in return object) returns false if the field
        does not exists

        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_segments.html#a6a8492fe606dee505fc335832b45f217

        :param segment_id: Id of the segment the condition shall apply for
        :param field_name: The field the condition compares against
        :param comparator: String, valid comparators are: <, >, ==, !=, <=, >=, like, not like, in, not in, segment
        :param value: String, value the field shall be compared with
        :param is_or: Boolean, only works if comparator is 'segment'
        :param is_date: Boolean, set to true if the value is a date
        :return: Int with amount of users in this segment after adding condition
        """
        # To make the API more accessible, the parameter comparator takes string version of standard Python comparators
        comparator_mapping = {'<': 'lt',
                              '>': 'gt',
                              '==': 'lt',
                              '!=': 'ne',
                              '<=': 'lte',
                              '>=': 'gte',
                              'like': 'like',
                              'not like': 'not like',
                              'in': 'in',
                              'not in': 'not in',
                              'segment': 'segment'}
        assert comparator in comparator_mapping.keys(), "Comperator must be in " \
                                                        "{<, >, ==, !=, <=, >=, like, not like, in, not in, segment}"
        comparator = comparator_mapping[comparator]

        data = f"""
            <item xsi:type="xsd:int">{segment_id}</item>
            <item xsi:type="xsd:str">{field_name}</item>
            <item xsi:type="xsd:str">{comparator}</item>
            <item xsi:type="xsd:str">{value}</item>
            <item xsi:type="xsd:bool">{is_or}</item>
        """

        if is_date:
            data += f"""<item xsi:type="xsd:bool">{is_date}</item>"""

        drs_response = self._post_request('dsSegmentsAddCondition', data)

        try:
            segment_count = int(drs_response.content)
        except DrsReturnError as e:
            raise DrsListError(e)
        except ValueError as e:
            raise DrsSegmentError(f"Either the field {field_name} does not exist or already has a condition. " /
                                  "With this error the segment became invalid. To continue working with it via API, " /
                                  "tit is advised relete segment and create it again.")

        return segment_count

    def segment_del_condition(self, segment_id: int, field_name: str) -> int:
        """Removed the condition for a given field in a given segment

        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_segments.html#a43b4a364c02d1bd151e5e4f79e166c68

        :param segment_id: Id of the segment the condition applies for
        :param field_name: The field name of the condition
        :return: Int with amount of users in the segment after removing condition
        """
        data = f"""
            <item xsi:type="xsd:int">{segment_id}</item>
            <item xsi:type="xsd:str">{field_name}</item>
        """
        drs_response = self._post_request('dsSegmentsDelCondition', data)
        try:
            segment_count = int(drs_response.content)
        except ValueError as e:
            raise ValueError(f"Return count is not an integer: {drs_response.content}")

        return segment_count

    def delete_segment(self, segment_id: int):
        """Delete a segment

        Warning: Will also return True if the segment did not exist in the first place

        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_segments.html#a77c4449df7d20441e588650b9497bd0c

        :param segment_id: Id of the segment the condition applies for
        :return: Boolean if deletion was successful
        """

        data = f"""<item xsi:type="xsd:int">{segment_id}</item>"""
        drs_response = self._post_request('dsSegmentsDel', data)

        # Response comes back as string 'true' or 'false', convert to boolean
        if drs_response.content == 'true':
            deleted = True
        elif drs_response.content == 'false':
            deleted = False
        else:
            raise DrsSegmentError(f"Error while trying to delete segment {segment_id}./n" /
                                  f"Response message: {drs_response.content}")

        return deleted

    def download_list(self, list_name: str, is_test_list: bool = False, field: str = 'email'):
        """Starts the process to download a list by requesting it and returning the download URL

        """

        data = f"""
            <item xsi:type="xsd:int">{list_name}</item>
            <item xsi:type="xsd:bool">{is_test_list}</item>
            <item xsi:type="xsd:str">{field}</item>
        """
        drs_response = self._post_request('dsSegmentsDel', data)

        return drs_response.content

    # ------------------------------ Campaign Methods ------------------------------

    def campaign(self, campaign_id: int) -> dict:
        """Gets both the campaign statistics (e.g. Amt Send, Amt Opend) and configuration parameters (e.g. from email) of a given campaign

        :param campaign_id: Int

        :return: Dict, empty if the campaign does not exist, else containing the following keys/fields and their values (all as string):
            'status', 'amount', 'opens', 'clicks', 'deliveries', 'bounced', 'complaints', 'unsubscribes', 'cvars',
            'unicViews', 'unicClics', 'id', 'category_id', 'name', 'subject', 'from_name', 'from_email', 'sender',
            'segment_id', 'segment', 'user_list', 'country', 'send_date', 'reply_to', 'list_unsubscribe', 'bounceds_soft'
        """

        available_fields = ["name", "amount", "subject", "from_name", "from_email", "sender", "segment_id",
                            "segment", "user_list", "country", "send_date", "reply_to", "list_unsubscribe"]
        # "text", "html", "utm_source", "utm_medium", "utm_term", "utm_content", "utm_campaign"

        data = f"""
            <item xsi:type="xsd:int">{campaign_id}</item>
            <item SOAP-ENC:arrayType="xsd:string[3]" xsi:type="SOAP-ENC:Array">
                {''.join(f'<item xsi:type="xsd:string">{field}</item>' for field in available_fields)}
            </item>
            <item xsi:type="xsd:int">1</item>
        """

        drs_response = self._post_request('dsCampaignGet', data)

        if drs_response.content:
            campaign_stats = drs_response.content
        else:
            raise DrsCampaignError(f"The campaign with the id {campaign_id} could not be found.")

        return campaign_stats

    def create_campaign(self, campaign_name: str, subject: str, from_name: str, from_email: str, reply_to: str,
                        html: str, plain: str, template_id: int = '', category_id: int = 1, country: str = 'DEU',
                        language_id: int = 3, list_unsubscribe: str = '', utm_campaign: str = '', utm_term: str = '',
                        utm_content: str = '', footer_usub_link: str = '', mirror_link: str = ''):
        """Creates (but not sends) a new campaign

        :param campaign_name: String with the name of the campaign
        :param subject: String with the email subject
        :param from_name: String with the from name for that email
        :param from_email: String with the from email for that email, the email needs be to available in drs
                           (can be checked with dsSettingsGetAllFromEmail)
        :param reply_to: String with the from email for that email, also needs to be set up and available
        :param html: Html template for the email
        :param plain: Text template for the email
        :param template_id: int of the template (header and footer) to be used
        :param category_id: The category id, all categories with their id can be retrieved with dsCategoryGetAll
        :param country: The iso3 country code for that mailing, can be retrieved with dsCountryGetAll
        :param language_id: The language id, can be retrieved with dsLanguageGetAll

        :return: Int with the id of the new campaign
        """
        # To avoid hard to catch 'SOAP-ENV:Client'-errors due to using non existing from_email or reply_to email address
        available_emails = self.from_emails()
        assert (from_email in available_emails) & (reply_to in available_emails), \
            f"from_email and reply_to needs to be set up. Available emails: {available_emails}"

        assert country in countries, "Country needs to be a valid iso-3 country code"
        assert str(language_id) in languages.keys(), f"Get valid Language ids via DoctorSenderClient.dsLanguageGetAll()"
        assert str(category_id) in categories.keys(), f"categoryid needs to be a valid Doctorsender category"

        assert bool(template_id) | bool(list_unsubscribe), "Either template id or list unsubscribe need to be defined"

        data = f"""
            <item xsi:type="xsd:str"><![CDATA[{campaign_name}]]></item>
            <item xsi:type="xsd:str"><![CDATA[{subject}]]></item>
            <item xsi:type="xsd:str"><![CDATA[{from_name}]]></item>
            <item xsi:type="xsd:str">{from_email}</item>
            <item xsi:type="xsd:str">{reply_to}</item>
            <item xsi:type="xsd:int">{category_id}</item>
            <item xsi:type="xsd:str">{country}</item>
            <item xsi:type="xsd:int">{language_id}</item>
            <item xsi:type="xsd:str"><![CDATA[{html}]]></item>
            <item xsi:type="xsd:str"><![CDATA[{plain}]]></item>
            <item xsi:type="xsd:str">{list_unsubscribe}</item>
            <item xsi:type="xsd:str">{utm_campaign}</item>
            <item xsi:type="xsd:str">{utm_term}</item>
            <item xsi:type="xsd:str">{utm_content}</item>
            <item xsi:type="xsd:str">{footer_usub_link}</item>
            <item xsi:type="xsd:str">{mirror_link}</item>
            <item xsi:type="xsd:str">{template_id}</item>"""

        drs_response = self._post_request('dsCampaignNew', data)

        try:
            campaign_id = int(drs_response.content)
        except ValueError as e:
            raise ValueError(f"Return id is not an integer: {drs_response.content}")
        except TypeError as e:
            raise DrsReturnError(f"Internal Doctorsender error. Code: {e}")

        return campaign_id

    def delete_campaign(self, campaign_id: int) -> bool:
        """Delete a campaign

        Warning: Will also return True if the campaign did not exist in the first place

        Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_campaign.html#a4a57c512898aab19aed88ac82c536c5e

        :param campaign_id: Id of the campaign to be deleted
        :return: Boolean if deletion was successful
        """

        data = f"""<item xsi:type="xsd:int">{campaign_id}</item>"""
        drs_response = self._post_request('dsCampaignDelete', data)

        # Response comes back as string 'true' or 'false', convert to boolean
        if drs_response.content == 'true':
            deleted = True
        elif drs_response.content == 'false':
            deleted = False
        else:
            raise DrsSegmentError(f"Error while trying to delete campaign {campaign_id}./n" /
                                  f"Response message: {drs_response.content}")

        return deleted

    def send_campaign_test(self, campaign_id: int, emails: list) -> bool:
        """Send test emails for a given campaign

        :param campaign_id: Int with the id of the campaign to be send
        :param emails: List of valid email addresses
        :return: Boolean, True if test send out was successful
        """

        assert type(emails) == list, "Param emails has to be a list of valid email addresses"

        receivers = ""
        for email in emails:
            receivers += f"""
                <item xsi:type="ns2:Map"><item>
                    <key xsi:type="xsd:string">email</key>
                    <value xsi:type="xsd:string">{email}</value>
                </item></item>"""

        data = f"""<item xsi:type="xsd:int">{campaign_id}</item>
            <item SOAP-ENC:arrayType="ns2:Map[1]" xsi:type="SOAP-ENC:Array">
               {receivers}
            </item>"""
        drs_response = self._post_request('dsCampaignSendEmailsTest', data, ur_type=2)

        # Response comes back as string 'true' or 'false', convert to boolean
        if drs_response.content == 'true':
            sent = True
        elif drs_response.content == 'false':
            sent = False
        else:
            raise DrsSegmentError(f"Error while trying to send campaign {campaign_id}./n" /
                                  f"Response message: {drs_response.content}")

        return sent

    def send_campaign_list(self, campaign_id: int, list_name: str, ip_group_name: str='', speed: int=5,
                           segment_id: int = 0, partition_id: int = 0, amount: int=0, auto_delete_list: bool=False,
                           programmed_date: dt.datetime = dt.datetime.now(), time_zone: str= 'Europe/Madrid',
                           need_confirm: int=0, multidate: list="", has_to_be_reprogrammed: int = 0,
                           create_accum: int=1) -> bool:
        """
        Send an existing campaign to a list or segment
        :param campaign_id: Int with the id of the campaign to be send
        :param list_name: Name of the list, the campaign will be send to
        :param ip_group_name: Name of the ipGroup where the campaign will be sent
        :param speed: Int, emails per second, default is 18k/hour
        :param segment_id: Int, id of the segment, must exist under the chosen list
        :param partition_id: Int, A partition of the list identifier. "0" if no partition is defined.
        :param amount: A max amount to be sent. If 0, campaign is sent to all users in list
        :param auto_delete_list: Boolean, Remove the list automatically when the campaign is sent.
        :param programmed_date:
        :param time_zone: Str, the time zone of the campaign. Defaults to Madrid time
        :param need_confirm: Int, 0 or 1, if 1, then campaign will be programmed but sendout start needs confirmation
        :param multidate: list of valid datetimes. If chosen, the sendout will be split evenly over the dates.
            In that case, programmed_date will be ignored
        :param has_to_be_reprogrammed: For a long scheduled campaign it force to recalculate the campaign amount before
            sent. 1: force, 0: do not recalculate the campaign amount
        :param create_accum: Int, 0 or 1, if 1 then create a accum campaign with all sub-campaigns to see statistics.
        :return: Boolean, is always true, errors get raised
        """

        if not ip_group_name:
            # Doctorsender doesn't really expose their IP groups, so client facing it should always be 'default.'
            # Just to be sure, we will still take ip groups returned during the init call
            ip_group_name = self.ips

        data = f"""
            <item xsi:type="xsd:int">{campaign_id}</item>
            <item xsi:type="xsd:str">{list_name}</item>
            <item xsi:type="xsd:str">{ip_group_name}</item>
            <item xsi:type="xsd:int">{speed}</item>
            <item xsi:type="xsd:int">{segment_id}</item>
            <item xsi:type="xsd:int">{partition_id}</item>
            <item xsi:type="xsd:int">{amount}</item>
            <item xsi:type="xsd:bool">{auto_delete_list}</item>
            <item xsi:type="xsd:str">{programmed_date.strftime('%Y-%m-%d %H:%M:%S')}</item>
            <item xsi:type="xsd:str">{time_zone}</item>
            <item xsi:type="xsd:int">{need_confirm}</item>
            <item xsi:type="xsd:str">{multidate}</item>
            <item xsi:type="xsd:int">{has_to_be_reprogrammed}</item>
            <item xsi:type="xsd:int">{create_accum}</item>"""

        drs_response = self._post_request('dsCampaignSendList', data)

        # Response comes is always 'true' or returns an error
        if drs_response.content == 'true':
            sent = True
        else:
            raise DrsSegmentError(f"Error while trying to send campaign {campaign_id}./n" /
                                  f"Response message: {drs_response.content}")

        return sent

    def list_campaigns(self, sql_where: str, fields: list, get_statistics: bool = False) -> list:
        available_fields = ["name", "amount", "subject", "from_name", "from_email", "sender", "html", "text",
                            "reply_to", "list_unsubscribe", "speed", "send_date", "status", "user_list",
                            "segment_id", "segment"]

        assert all([True if field in available_fields else False for field in fields])

        data = f"""
            <item xsi:type="xsd:str">{sql_where}</item>
            <item SOAP-ENC:arrayType="xsd:string[1]" xsi:type="SOAP-ENC:Array">
                {''.join(f'<item xsi:type="xsd:string">{field}</item>' for field in fields)}
            </item>
            <item xsi:type="xsd:int">{1 if get_statistics else 0}</item>
        """
        drs_response = self._post_request('dsCampaignGetAll', data)

        # The content does not follow the standard rules, so we parse it separatly
        # First check if there is an error by calling the response property
        _ = drs_response.content
        # If that works without an en error, retrieve the items and parse it
        try:
            items = drs_response.dict['Envelope']['Body']['{ns1}webserviceResponse']['webserviceReturn'][1]['item'][
                'value']

            campaigns = [{i['item']['key']: i['item']['value'] for i in c['item']} for c in items]
        except:
            raise DrsReturnError(drs_response.content)

        return campaigns

    def campaign_get_user_statistics(self, campaign_id: str, stats_type: str) -> list:

        assert stats_type in  ["sent","openers","clickers","soft_bounced","hard_bounced","complaint","unsubscribe"]

        data = f"""
            <item xsi:type="xsd:str">{campaign_id}</item>
            <item xsi:type="xsd:str">{stats_type}</item>
        """
        drs_response = self._post_request('dsCampaignGetUserStatistics', data)
        # Return is a json string with key 'email' and an array of emails as a value
        try:
            emails = json.loads(drs_response.content)['email']
        except KeyError:
            raise DrsReturnError("Returned JSON string does not contain key 'email'")
        except json.JSONDecodeError:
            raise DrsReturnError(f"Returned object is not a valid JSON string: {drs_response}")
        except TypeError:
            # Happens when there no users are returned
            emails = []

        return emails

    # ------------------------------ User Methods ------------------------------
    def campaign_get_user_statistics(self, campaign_id: str, stats_type: str) -> list:
            """
            Get a list of emails that did something with a campaign
            Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_campaign.html#a6867f4b627bd583c93568f520fe92625
            :param campaign_id: Id of the campaign
            :param stats_type: The type of email info you need to get. You must choose one of this
                type: ["sent","openers","clickers","soft_bounced","hard_bounced","complaint","unsubscribe"]

            :return:
            """
            assert stats_type in  ["sent","openers","clickers","soft_bounced","hard_bounced","complaint","unsubscribe"]

            data = f"""
            <item xsi:type="xsd:str">{campaign_id}</item>
            <item xsi:type="xsd:str">{stats_type}</item>
            """
            drs_response = self._post_request('dsCampaignGetUserStatistics', data)
            # Return is a json string with key 'email' and an array of emails as a value
            try:
                emails = json.loads(drs_response.content)['email']
            except KeyError:
                raise DrsReturnError("Returned JSON string does not contain key 'email'")
            except json.JSONDecodeError:
                raise DrsReturnError(f"Returned object is not a valid JSON string: {drs_response}")

            return emails

    def lists(self, test_lists=0):
            """Get all user lists in the account

            Doc: http://soapwebservice.doctorsender.com/doxy/html/classds_users.html#a3bd42970a9819091a5220cfed0b578c0

            :param test_lists: 1 to only get Testlists, 0 to get only get non-test lists and '' to get all available lists
            :return: DrsResponse object, .content returns a dict with segment_id as key and segment_name as value
            """

            assert test_lists in [0, 1, ''], "test_lists needs to be 0, 1 or ''"

            data = f'<item xsi:type="xsd:str">{test_lists}</item>'
            drs_response = self._post_request('dsUsersListGetAll', data)

            return drs_response.content

    # ------------------------------ Static Methods ------------------------------

    def _ip_groups(self) -> str:
        """Get all account ip-groups

        :return: List containing the name of all ip-groups
        """
        drs_response = self._post_request('dsIpGroupGetNames', None)
        return drs_response.content

    def languages(self) -> dict:
        """Get all languages
        Static function, should never change

        :return: Dict containing language id as key and language name as value
        """
        drs_response = self._post_request('dsLanguageGetAll', None)
        return drs_response.content

    def countries(self) -> dict:
        """Get all countries
        Static function, should never change

        :return: Dict containing country iso-3 code as key and country name as value
        """
        drs_response = self._post_request('dsCountryGetAll', None)
        return drs_response.content

    def categories(self) -> dict:
        """Get all categories
        Static function, should never change

        :return: Dict containing category id as key and category name as value
        """
        drs_response = self._post_request('dsCategoryGetAll', None)
        return drs_response.content

    def from_emails(self) -> list:
        """Get all account from-emails

        :return: List containing all available email addresses
        """
        drs_response = self._post_request('dsSettingsGetAllFromEmail', None)
        res = [drs_response.content] if type(drs_response.content) == str else list(drs_response.content.values())

        return res

    def ftp_data(self) -> dict:
        drs_response = self._post_request('dsFtpGetAccess', None)
        return drs_response.content

    def get_unsubscribers(self, list_name: str, start_date: dt.datetime, end_date: dt.datetime) -> list:
        """Download the unsubscribers of a given list, in a given time frame.
        :return: A List of user-unsubscribe objects. The objects have the keys 'timestamp', 'email', and 'list'
        """
        data = f"""
            <item xsi:type="xsd:str">{start_date.strftime('%Y-%m-%d %H:%M:%S')}</item>
            <item xsi:type="xsd:str">{end_date.strftime('%Y-%m-%d %H:%M:%S')}</item>
            <item xsi:type="xsd:str">{list_name}</item>
            <item xsi:type="xsd:bool">false</item>
            <item xsi:type="xsd:bool">false</item>"""

        drs_response = self._post_request('dsUsersListGetUnsubscribes', data)

        # The response content is a dict with an arbitrary int key and a string value that contains the date of the
        # unsubscribe event, the time, the user email and the list name. The values are separated by a semicolon.
        # So we reshape it into a list of those objects
        unsubscribers = list()
        for i, ele in drs_response.content.items():
            unsubscribe_data = ele.split(';')
            timestamp = dt.datetime.strptime(unsubscribe_data[0] + unsubscribe_data[1], '%Y%m%d%H:%M')
            unsubscribers.append({
                'timestamp': timestamp,
                'email': unsubscribe_data[2],
                'list': unsubscribe_data[3]

            })
        return unsubscribers

    def get_list_fields(self, list_name: str, is_testlist: bool = False) -> dict:
        """
        Retrieve the field names for a given list.
        :return: A dict with the field names as keys and the field types as value
        """
        data = f"""
            <item xsi:type="xsd:str">{list_name}</item>
            <item xsi:type="xsd:bool">{is_testlist}</item>
            <item xsi:type="xsd:bool">false</item>"""

        drs_response = self._post_request('dsUsersListGetFields', data)

        return drs_response.content

    def download_list(self, list_name: str, is_testlist: bool = False, field: str = 'all') -> str:
        """
        Create a download link for a csv file that contains all users in a given list.
        >>> link = client.download_list('list', field='all')
        >>> df = pd.read_csv(link)

        Only all fields can be downloaded, since adding the line for is_testlist always returns "List cound now be found."

        :return: A string containing the download link. This link can take a while to get active
        """
        data = f"""<item xsi:type="xsd:str">{list_name}</item>"""

        drs_response = self._post_request('dsUsersListDownload', data)

        return drs_response.content

    def download_hardbouncer(self, list_name: str, field: str = 'email') -> str:
        """
        Create a download link for a csv file that contains all hardbouncer in a given list.
        >>> link = client.download_hardbouncer('list', field='all')
        >>> df = pd.read_csv(link)

        :return: A string containing the download link. This link can take a while to get active
        """
        data = f"""
            <item xsi:type="xsd:str">{list_name}</item>
            <item xsi:type="xsd:str">{field}</item>"""

        drs_response = self._post_request('dsUsersListDownloadHard', data)

        return drs_response.content

    def download_events(self, from_date: dt.date, until_date: dt.date):
        """Requests a user event export
        """

        data = f"""
            <item xsi:type="xsd:str">{from_date}</item>
            <item xsi:type="xsd:str">{until_date}</item>
        """
        drs_response = self._post_request('dsUsersGetUserActivity', data, timeout=300)

        return drs_response.content
