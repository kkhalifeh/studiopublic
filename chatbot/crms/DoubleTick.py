import requests
import logging
from chatbot.models import Request
from time import sleep
logger = logging.getLogger(__name__)


class DoubleTick():
    # Double Tick BASE URL
    BASE_URL = "https://public.doubletick.io"

    # Authorization Headers
    HEADERS = {
        "Authorization": "key_gJr7EOOB7t",
        "accept": "application/json",
        "content-type": "application/json"
    }

    # Phone Number
    PHONE = "+97142461500"

    def api_request(self, endpoint, method, data):
        """Sends request to the desired api endpoint"""
        try:
            req = requests.request(
                method,
                f"{self.BASE_URL}/{endpoint}",
                json=data if method in ["POST", "PUT"] else None,
                headers=self.HEADERS,
                params=data if method == "GET" else None
            )
            Request.objects.create(params=str(req.json()))
            return req.json()
        except Exception as e:
            logger.error("Error occured while api_request to endpoint: "
                         + endpoint + " and method: " + method)
            logger.error(data)
            logger.error(str(e))
            return None

    def send_text_to_phone(self, message, to):
        '''Used to send text message to phone number'''
        return self.api_request("whatsapp/message/text", "POST", {
            "from": self.PHONE,
            "to": to,
            "content": {
                "text": message,
            }
        })

    def get_contact(self, phone, delay=0):
        if delay > 0:
            sleep(delay)
        '''Gets contact details from the provided phone number'''
        return self.api_request("customer/details", "GET", {
            "phoneNumber": phone
        })

    def assign_team_member(self, contact, agentPhone):
        '''For assigning a customer to an agent'''
        return self.api_request("team-member/assign", "POST", {
            "customerPhoneNumber": contact.phone,
            "assignedUserPhoneNumber": agentPhone,
            "reassign": True
        })

    def get_team(self):
        '''For getting team member list'''
        response = self.api_request("team", "GET", None)
        return response["data"] if response else []

    def update_contact(self, phone, name=None, custom_fields=None):
        '''Update contact details.'''
        data = {
            "phone": phone
        }
        if name:
            data["name"] = name
        if custom_fields:
            data["customFields"] = custom_fields
        self.api_request("customer/assign-tags-custom-fields", "POST", data)
