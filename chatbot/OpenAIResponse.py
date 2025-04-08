from .crms.ZohoBooking import ZohoBooking


class OpenAIResponse():
    '''Class for handling OpenAI's response'''

    COMPLETION_STATUSES = [
        "completed",
        "cancelled",
        "expired",
        "failed",
        "incomplete"
    ]

    # FreshSales API Object
    CRM = None

    def __init__(self):
        self.CRM = ZohoBooking()

    def get_completion_statuses(self):
        '''Return completion statuses'''
        return self.COMPLETION_STATUSES

    def get_function_map(self, chat_request):
        '''Returns function defs'''
        return {
            "get_available_day_slots": lambda _:
            self.CRM.get_available_day_slots(chat_request),
            "update_contact": lambda params: self.CRM.update_contact(
                params["full_name"], chat_request),
            "update_appointment": lambda params: self.CRM.update_appointment(
                params["from_date"], params["end_date"],
                params["appointment_id"], chat_request
            ),
            "delete_appointment": lambda params: self.CRM.delete_appointment(
                params["appointment_id"], chat_request),
            "list_appointment_for_customer": lambda _:
                self.CRM.list_appointment_for_customer(chat_request),
            "get_available_time_slots": lambda params:
                self.CRM.get_available_time_slots(
                    params["appointment_date"], chat_request
                ),
            "handle_junior_assessment": lambda params:
                self.CRM.handle_junior_assessment(
                chat_request
            ),
            "create_appointment": lambda params: self.CRM.create_appointment(
                params["from_date"],
                params["end_date"],
                params["customer_name"],
                params["customer_email"],
                chat_request
            ),
            "assign_agent": lambda params:
                self.CRM.assign_agent(
                chat_request,
                params['query_type'] if "query_type" in params else None,
                params['agent_phones'] if "agent_phones" in params else None
            ),
            "booking_with_agent": lambda params:
                self.CRM.booking_with_agent(
                chat_request
            ),
            "schedule_of_program": lambda params:
                self.CRM.schedule_of_program(
                chat_request,
                params["program_id"] if "program_id" in params else None,
                params["class_type"] if "class_type" in params else None,
                params["start_date"] if "start_date" in params else None
            ),
            "close_conversation": lambda params:
                self.CRM.close_conversation(
                    chat_request,
                    params["customer_name"] if "customer_name" in params else
                    None,
                    params["declined_booking"] if "declined_booking" in params
                    else None,
                    params["type_of_booking"] if "type_of_booking" in
                    params else 'adult',
                )
        }

    def handle_tool_calls(self, tool_calls, chat_request):
        '''For handling tool calls through langchain'''
        results = []
        function_map = self.get_function_map(chat_request)
        if chat_request:
            self.CRM.CONTACT = chat_request.contact
        for tool_call in tool_calls:
            tool_name = tool_call['name']
            arguments = tool_call.get('args', '{}')
            if tool_name in function_map:
                results.append({
                    "content": function_map[tool_name](arguments),
                    "tool_call_id": tool_call["id"]
                })
        return results
