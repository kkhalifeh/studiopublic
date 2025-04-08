from chatbot.models import OAuth
import requests


class StudioRepublikApi():
    # Studio Republik API URL
    BASE_URL = "https://studiorepublikapi.azurewebsites.net/api/"

    # Authorization Headers
    HEADERS = {}

    # Timezone hours
    TIMEZONE_HOURS = 4

    def __init__(self):
        """Constructor for this class. Will validate access token
        and generate new one if required"""
        token = OAuth.objects.get(type="Studio Republik")
        self.HEADERS["Authorization"] = "Bearer " + token.access_token

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
            return req.json()
        except Exception:
            if req.status_code == 401:
                self.get_access_token()
                return self.api_request(endpoint, method, data)
            return None

    def get_access_token(self):
        """Generates a new access token."""
        try:
            token = OAuth.objects.get(type="Studio Republik")
            response = requests.post(
                f"{self.BASE_URL}/token/requestapitoken",
                json={"APIKey": token.refresh_token}
            ).json()
            token.access_token = response["token"]
            token.save()
            self.HEADERS["Authorization"] = f"Bearer {token.access_token}"
        except Exception as e:
            raise ValueError(f"Problem with getting access token: {e}")

    def get_classes(self, class_type=None):
        '''For fetching classes available for junior and adults'''
        response = self.api_request(
            "Specializations/GetSpecializationByUnitAndLevel", "GET",
            {"specializationId": 1, "slevel": 2,
             "isJunior": class_type == "junior"}
        )
        return response["ResponseObject"] \
            if "ResponseObject" in response else []

    def get_programs(self, class_id, is_junior):
        """Fetch programs for a class."""
        response = self.api_request(
            "Specializations/GetSpecializationByUnitAndLevel", "GET",
            {"specializationId": class_id, "slevel": 4, "isJunior": is_junior}
        )
        return response["ResponseObject"] \
            if "ResponseObject" in response else []

    def get_activity(self, program_id, is_junior):
        """Fetch programs for a class."""
        response = self.api_request(
            "Specializations/GetSpecializationByUnitAndLevel", "GET",
            {"specializationId": program_id, "slevel": 5,
             "isJunior": is_junior}
        )
        return response["ResponseObject"] \
            if "ResponseObject" in response else []

    def get_schedule(self, program_id, start_date, end_date, is_junior):
        '''For getting available schedule of a program'''
        return self.api_request(
            "Classes/GetClassesByFilters",
            "GET",
            {
                "specId": program_id,
                "staffId": 0,
                "locationId": 0,
                "startDate": start_date,
                "endDate": end_date,
                "isPT": False,
                "isTerm": is_junior
            })
