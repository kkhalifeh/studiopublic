import requests
import random
from datetime import datetime, timedelta
from chatbot.models import OAuth, CacheResponse
from .DoubleTick import DoubleTick
from chatbot.StudioRepublikApi import StudioRepublikApi
from chatbot.helper import convert_lead_to_DT
import json


class ZohoBooking():
    # Zoho Base API URL
    BASE_URL = "https://www.zohoapis.com/bookings/v1/json"

    # Zoho Auth URL
    BASE_AUTH_URL = "https://accounts.zoho.com/oauth/v2/token"

    # Client Id
    CLIENT_ID = "1000.YMPBXD86JDMB9V5BEPYXUKKMP8CTYE"

    # Client Secret
    CLIENT_SECRET = "6a4a96a1c1b6b966a7fa8a08ef03f62110b2852502"

    # Service ID
    SERVICE_ID = "4750007000000064042"

    # Staff ID
    STAFF_ID = "4750007000000041012"

    # Authorization Headers
    HEADERS = {}

    # Error Msg
    ERROR_MSG = (
        "There are currently no slots available for booking. "
        + "Please try again after few days"
    )

    # Duration
    DURATION = 30

    # Contact for the appointments
    CONTACT = None

    # Available Dates for Booking
    DAYS_AVAILABLE = 7

    # Timezone
    TIMEZONE = "Asia/Dubai"

    # Timezone Hours
    TIMEZONE_HOURS = 4

    # DoubleTick
    DOUBLETICK = DoubleTick()

    # StudioRepublik API
    STUDIO_REPUBLIK_API = StudioRepublikApi()

    # Junior Agent
    JUNIOR_AGENT = ["971504994681", "971504994601"]

    CRM_AGENT = ['971542172356', '971551330783', '971551330783']

    ADULT_AGENT = ["971545795448", "971501040294", "971565397998"]

    # Assign Agent MSG
    ASSIGN_AGENT_MSG = """I've connected you with an agent who will
        provide you with all needed information and better assistance."""

    def __init__(self):
        """Constructor for this class. Will validate access token
        and generate new one if required"""
        token = OAuth.objects.get(type="Zoho Booking")
        self.HEADERS["Authorization"] = "Zoho-oauthtoken " + token.access_token

    def api_request(self, endpoint, method, data, isFormData=False):
        """Sends request to the desired api endpoint"""
        try:
            req = requests.request(
                method,
                f"{self.BASE_URL}/{endpoint}",
                json=data if method in ["POST", "PUT"] and
                isFormData is False else None,
                data=data if method in ["POST", "PUT"] and
                isFormData else None,
                headers=self.HEADERS,
                params=data if method == "GET" else None
            )
            return req.json()
        except Exception:
            if req.status_code == 401:
                self.get_access_token()
                return self.api_request(endpoint, method, data)
            return None

    def booking_with_agent(self, chat_request):
        '''For booking a class/program'''
        try:
            return self.assign_agent(
                chat_request,
                agent_phones=['971542172356', '971551330783', '971551330783']
            )
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Booking With Agent. " + str(e)
            )
            return "Currently no agent is available for handling." + \
                "this query. Please try again later"

    def assign_agent(
            self,
            chat_request,
            query_type=None,
            agent_phones=None):
        """Assigns an agent to the current chat"""
        try:
            if agent_phones:
                agent_phone = self.assign_agent_from_list(agent_phones)
            elif query_type is not None:
                team = self.JUNIOR_AGENT if query_type in [
                    "junior", "junior_camp"] \
                    else self.ADULT_AGENT
                agent_phone = self.assign_agent_from_list(team)
            else:
                team = self.JUNIOR_AGENT + self.ADULT_AGENT
                agent_phone = self.assign_agent_from_list(team)
            self.DOUBLETICK.assign_team_member(self.CONTACT, agent_phone)
            return self.ASSIGN_AGENT_MSG
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Assign Agent Assessment. " + str(e)
            )
            return "Currently no agent is available for handling." + \
                "this query. Please try again later"

    def get_access_token(self):
        """Generates a new access token from the provided refresh token"""
        token = OAuth.objects.get(type="Zoho Booking")
        data = {
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token
        }
        req = requests.request("POST", self.BASE_AUTH_URL, data=data)
        response = req.json()
        if "error" in response:
            raise ValueError(response["error"])
        token.access_token = response["access_token"]
        token.save()
        self.HEADERS["Authorization"] = "Zoho-oauthtoken " + token.access_token

    def save_error_message(self, chat_request, error_message):
        """Saves error message inside the chat response"""
        chat_request.error_message = error_message
        chat_request.status = "error"
        chat_request.save()

    def update_contact(self, full_name, chat_request):
        """Updates a contact in the CRM with new full name"""
        try:
            if self.CONTACT:
                self.DOUBLETICK.update_contact(
                    self.CONTACT.phone,
                    full_name,
                    None
                )
            else:
                self.save_error_message(
                    chat_request,
                    "Update Contact No contact found"
                )
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Update Contact. " + str(e)
            )
        return "Contact is updated"

    def get_free_slots_for_appointment(self, date_obj):
        """Gets free slots for an appointment on a particular date."""
        free_time_slots = self.api_request(
            "availableslots",
            "GET",
            {
                "service_id": self.SERVICE_ID,
                "selected_date": date_obj.strftime('%d-%b-%Y')
            }
        )
        return free_time_slots.get("response", {}).get("returnvalue", {})\
            .get("data")

    def get_available_time_slots(self, appointment_date, chat_request):
        """Gets available slots for the appointment on the provided date"""
        try:
            date_obj = datetime.strptime(appointment_date, "%b %d, %Y")
            time_slots = self.get_free_slots_for_appointment(date_obj)
            if not time_slots or time_slots == "Slots Not Available":
                return (
                    "No slot is available on your provided date. "
                    + self.get_available_day_slots(chat_request)
                )
            message = (
                "Please select your time of visit from the available"
                + "time slots:\n"
            )
            for time_str in time_slots:
                start_time = datetime.strptime(time_str, "%H:%M")
                end_time = start_time + timedelta(minutes=self.DURATION)
                message += f"{start_time.strftime('%H:%M')} - " + \
                    end_time.strftime('%H:%M')
            return message
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Get Available Time Slots. " + str(e)
            )
            return self.ERROR_MSG

    def get_available_day_slots(self, chat_request, refresh=False):
        """Gets available day slots for the appointment on the provided date"""
        try:
            if not refresh:
                cache_response = CacheResponse.objects.filter(
                    type="get_available_day_slots"
                )
                if cache_response:
                    return cache_response[0].message

            start_date = datetime.now() + timedelta(days=1)
            message, count = (
                "Please select your visit from the available dates:\n",
                0,
            )
            # Loop until we have maximum available dates
            while count < self.DAYS_AVAILABLE:
                # Check if the current date has free time slots
                time_slots = self.get_free_slots_for_appointment(start_date)
                if time_slots and time_slots != "Slots Not Available":
                    message += (
                        f"{count + 1}. {start_date.strftime('%b %d, %Y')}\n"
                    )
                    count += 1
                # Move to the next day
                start_date += timedelta(days=1)
            return message
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Get Available Day Slots. " + str(e)
            )
            return self.ERROR_MSG

    def list_appointment_for_customer(self, chat_request):
        """Lists all open appointments for the current user"""
        error_message = "You currently have no appointments booked"
        try:
            if not self.CONTACT:
                return error_message
            start_date = datetime.now()
            end_date = start_date + timedelta(days=365*5)
            appointment_list = self.api_request("fetchappointment", "POST", {
                "data": json.dumps({
                    "customer_phone_number": "971585389581",
                    "from_time": start_date.strftime("%d-%b-%Y"),
                    "to_time": end_date.strftime("%d-%b-%Y"),
                    "service_id": self.SERVICE_ID
                })
            }, True)
            booked_appointments = appointment_list.get("response", {})\
                .get("returnvalue", {}).get("response")
            if not booked_appointments or "No Match Found" in \
                    booked_appointments:
                return error_message
            message = "You have the following appointments due: \n"
            for appointment in booked_appointments:
                if appointment["status"] == "cancel":
                    continue
                from_date = datetime.fromisoformat(
                    appointment["iso_start_time"]
                )
                end_date = datetime.fromisoformat(
                    appointment["iso_end_time"]
                )
                if from_date.date() >= datetime.now().date():
                    message += f"{from_date.strftime('%b %d, %Y %H:%M')} " + \
                        f"- {end_date.strftime('%b %d, %Y %H:%M')}" + \
                        " (# Dont show this id: " + \
                        str(appointment["booking_id"]) + ")"
            return message
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.save_error_message(
                    chat_request,
                    "Function: List Appointment for customer: " + str(e)
            )
            return error_message

    def delete_appointment(self, appointment_id, chat_request):
        """Deletes an appointment from the provided Id"""
        try:
            self.api_request("updateappointment", "POST", {
                "booking_id": appointment_id,
                "action": "cancel"
            }, True)
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Delete Appointment. " + str(e)
            )
        return "Deleted your appointment"

    def update_appointment(
        self, start_time, end_date, appointment_id, chat_request
    ):
        """Updates existing appointment for the user"""
        try:
            self.api_request("rescheduleappointment", "POST", {
                "booking_id": appointment_id,
                "start_time": start_time
            }, True)
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Update Appointment. " + str(e)
            )
        return "Updated your appointment. Would be waiting for you"

    def assign_agent_from_list(self, agent_list):
        '''For assigning an agent from the provided list'''
        return random.choice(agent_list)

    def handle_junior_assessment(self, chat_request):
        '''For handling junior assessment assignment'''
        try:
            self.DOUBLETICK.assign_team_member(
                self.CONTACT,
                self.assign_agent_from_list(self.JUNIOR_AGENT)
            )
            return "Assigning you to an Agent who will help with " + \
                "junior assessment first"
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Handle Junior Assessment. " + str(e)
            )
            return self.assign_agent(chat_request)

    def create_appointment(
            self,
            from_date,
            end_date,
            customer_name,
            customer_email,
            chat_request):
        """Creates an appointment"""
        booking_id = ""
        try:
            if self.CONTACT:
                self.DOUBLETICK.update_contact(
                    self.CONTACT.phone,
                    customer_name,
                    [
                        {
                            "name": "Appointment Date",
                            "value": from_date
                        }
                    ]
                )
                appointment = self.api_request("appointment", "POST", {
                    "service_id": self.SERVICE_ID,
                    "from_time": from_date,
                    "to_time": end_date,
                    "time_zone": self.TIMEZONE,
                    "workspace_id": 4750007000000072002,
                    "customer_details": json.dumps({
                        "name": customer_name,
                        "email": customer_email,
                        "phone_number": self.CONTACT.phone
                    })
                }, True)
                booking_id = appointment.get("response", {})\
                    .get("returnvalue", {}).get("booking_id")
                booking_id = "(# Dont show this id " + booking_id + ")"
                convert_lead_to_DT(self.CONTACT, self.DOUBLETICK, None, True)
            else:
                self.save_error_message(
                    chat_request,
                    "Function: Create Appointment. No contact found"
                )
        except Exception as e:
            self.save_error_message(
                chat_request, "Function: Create Appointment. " + str(e)
            )
        return "Created your appointment. Would be waiting for you." + \
            booking_id
