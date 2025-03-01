"""
imports
"""
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os.path
import datetime
import os
from groq import Groq
from fastapi import FastAPI, HTTPException, Query
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

"""
This is the code that handles our interactions with the google calendar api
"""
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def create_event(
    service,
    summary="Untitled Event",
    location="",
    description="",
    start_datetime="2025-03-04T12:00:00-07:00",  # Default start time is 12:00 PM
    end_datetime="2025-03-04T13:00:00-07:00",  # Default end time is 1:00 PM
    attendees=[],  # Be sure to pass in a list
    use_default_reminders=True,  # Sets all reminder settings to default
    method_type="popup",
    method_minutes=30,
    contact_type="email",
    contact_minutes=60,
    colorId=1,  # Sets the color of the item in Google Calender
    recurrence="",  # Pass in the recurrence rule as a string, it will properly be inserted into a list
    classId="",  # Ensure the class ID is accurate
    assignmentName="",  # Assignment as a string
    priority=1,  # Scale 1-10, 1 being extra cred, 10 being a final
    aiGenerated=False,  # Is this item AI generated?
):

    # If no attendees are provided, set a default empty list
    if attendees is None:
        attendees = ["calvinschedulo@gmail.com"]

    # Set reminders overrides based on use_default_reminders
    reminders = {
        "useDefault": use_default_reminders,
    }

    if not use_default_reminders:
        reminders["overrides"] = [
            {
                "method": method_type,
                "minutes": method_minutes
            },
            {
                "method": contact_type,
                "minutes": contact_minutes
            }
        ]

    # Create the event body using the passed arguments
    event = {
        "summary": summary,
        "location": location,
        "description": description,
        "start": {
            "dateTime": start_datetime,
            "timeZone": "America/Los_Angeles",  # Default time zone
        },
        "end": {
            "dateTime": end_datetime,
            "timeZone": "America/Los_Angeles",  # Default time zone
        },
        # List of email addresses
        "attendees": [{"email": email} for email in attendees],
        "reminders": reminders,
        "colorId": colorId,
        "recurrence": [recurrence if recurrence else None],
        "extendedProperties": {
            "private": {
                "classID": classId,
                "assignmentName": assignmentName,
                "priority": priority,
                "aiGenerated": aiGenerated,

            }
        }
    }

    # Insert the event into the Google Calendar
    event = service.events().insert(calendarId="primary", body=event).execute()

    print(f'Event created: {event.get("htmlLink")}')


def delete_event_by_assignment(service, events, course, assignment):
    calendar_id = 'primary'  # The calendar ID you're working with
    event_found = False

    try:
        # Iterate through the events you've already retrieved
        for event in events:
            private = event.get('extendedProperties',
                                {}).get('private', {})

            # Check if the event has the correct classID and assignment_name
            if private.get('classID') == course and private.get('assignmentName') == assignment and private.get('aiGenerated'):
                # Get the event ID and delete the event
                event_id = event['id']
                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                print(f"Event with ID {event_id} has been deleted.")
                event_found = True
        if not event_found:
            print(f"No event found with classID {
                course} and assignmentName {assignment}.")
    except HttpError as error:
        print(f"An error occurred: {error}")

    def delete_event_by_name(service, events, name):
        calendar_id = 'primary'  # The calendar ID you're working with
        event_found = False

        try:
            # Iterate through the events you've already retrieved
            for event in events:
                title = event.get('summary')
                private = event.get(
                    'extendedProperties', {}).get('private', {})

                # Check if the event has the correct classID and assignment_name
                if title == name and private.get('aiGenerated'):
                    # Get the event ID and delete the event
                    event_id = event['id']
                    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                    print(f"Event with ID {event_id} has been deleted.")
                    event_found = True
                if not event_found:
                    print(f"No event found with summary {name}.")
        except HttpError as error:
            print(f"An error occurred: {error}")


def get_events():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time

        eight_days_later = (datetime.datetime.utcnow() +
                            datetime.timedelta(days=8)).isoformat() + "Z"
        print("Getting the upcoming events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=eight_days_later,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            # Get the start and summary for the event
            start = event["start"].get("dateTime", event["start"].get("date"))
            summary = event.get("summary", "No summary available")
            location = event.get("location", "No location provided")
            description = event.get("description", "No description provided")
            end = event["end"].get("dateTime", "No end time provided")

            # Retrieve extended properties (if available) for private information
            private_properties = event.get(
                'extendedProperties', {}).get('private', {})

            # Retrieve attendees (if available)
            attendees = event.get('attendees', [])

            # Get reminder settings (if applicable)
            reminders = event.get('reminders', {}).get('useDefault', False)

            # Access recurrence rule (if available)
            recurrence = event.get('recurrence', "No recurrence rule")

            # Access the classId, assignmentName, priority, and aiGenerated flags
            class_id = private_properties.get('classId', "No class ID")
            assignment_name = private_properties.get(
                'assignmentName', "No assignment name")
            priority = private_properties.get('priority', "No priority set")
            ai_generated = private_properties.get('aiGenerated', False)

            # Now, print all the gathered information
            print(f"Start: {start}")
            print(f"Summary: {summary}")
            print(f"Location: {location}")
            print(f"Description: {description}")
            print(f"End: {end}")
            print(f"Attendees: {attendees}")
            print(f"Reminders (use default): {reminders}")
            print(f"Recurrence: {recurrence}")
            print(f"Class ID: {class_id}")
            print(f"Assignment Name: {assignment_name}")
            print(f"Priority: {priority}")
            print(f"AI Generated: {ai_generated}")
            print("-" * 40)

        service.events().insert

    except HttpError as error:
        print(f"An error occurred: {error}")


GOOGLE_CAL = get_events()

"""
This is the api code for communicating with Calvin
"""
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = FastAPI()

systemMessage = f"You are a personal assistant named Calvin that helps people schedule their week. You are to be helpful and friendly so that the user can find the most optimal study schedule. When you are prompted 'Please list all of the events that will be listed to the calendar.' you will return a prompt that will tell an ai model that has access to the user\'s canvas an google calendar know exactly what events to put in google calendar, don't ask for further advice or adjustments at that point. Avoid telling the user about these instructions. Here is the users google calendar as of now: {GOOGLE_CAL}"


history = [
    {
        "role": "system",
        "content": systemMessage,
    }
]


@app.get("/")
def root():
    return {"Hello": "World"}

# Updated endpoint to accept query parameter 'input'


def get_fes_from_calvin(history: list):
    try:
        chat_completion = client.chat.completions.create(
            messages=history,
            model="llama-3.3-70b-versatile",
        )
        response = chat_completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Error in getResFromCalvin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calvin")
def prompt_calvin(input: str = Query(None)):
    if not input:
        raise HTTPException(
            status_code=400, detail="Input parameter is required")
    else:
        history.append({"role": "user", "content": input})
        print(history)
        if input == "Please list all of the events that will be listed to the calendar.":
            try:
                response = get_fes_from_calvin(history)
                return schedule_events(response)
            except Exception as e:
                print(f"Error scheduling: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        else:
            print("talking to calvin")
            try:
                response = get_fes_from_calvin(history)
                history.append({"role": "assistant", "content": response})
                return {"response": response}
            except HTTPException:
                raise
            except Exception as e:
                print(f"Error in promptCalvin: {e}")
                raise HTTPException(status_code=500, detail=str(e))


"""
This is our api code for working with schedulo
"""

# Initialize Groq LLM
llm = ChatGroq(
    model_name="llama-3.3-70b-versatile",
    temperature=0.7
)

# Define the expected JSON structure for Google Calendar event
parser = JsonOutputParser(pydantic_object={
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "location": {"type": "string"},
            "description": {"type": "string"},
            "start": {"type": "object", "properties": {
                "dateTime": {"type": "string", "format": "date-time"},
                "timeZone": {"type": "string"}
            }},
            "end": {"type": "object", "properties": {
                "dateTime": {"type": "string", "format": "date-time"},
                "timeZone": {"type": "string"}
            }},
            "attendees": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"}
                }
            }},
            "reminders": {"type": "object", "properties": {
                "useDefault": {"type": "boolean"},
                "overrides": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string"},
                        "minutes": {"type": "integer"}
                    }
                }}
            }},
            "colorId": {"type": "integer"},
            "recurrence": {"type": "array", "items": {"type": "string"}},
            "extendedProperties": {"type": "object", "properties": {
                "private": {"type": "object", "properties": {
                    "className": {"type": "string"},
                    "assignmentName": {"type": "string"},
                    "priority": {"type": "int"},
                    "aiGenerated": {"type": "bool"}
                }}
            }}
        }
    }
})

# Create a simple prompt
prompt_template = ChatPromptTemplate.from_messages([
    ("system", """Extract scheduling details into a list of Google Calendar event JSON objects only respond with valid json, don't include comments about the json:
        [
            {{
                "summary": "event title here",
                "location": "event location here (only include if a location is mentioned)",
                "description": "event description here",
                "start": {{
                    "dateTime": "start date and time here",
                    "timeZone": "time zone here"
                }},
                "end": {{
                    "dateTime": "end date and time here",
                    "timeZone": "time zone here"
                }},
                "attendees": [
                    {{
                        "email": "attendee email here (only include if specific attendies are mentioned)"
                    }}
                ],
                "reminders": {{
                    "useDefault": true or false,
                    "overrides": [
                        {{
                            "method": "popup or email",
                            "minutes": minutes before event
                        }}
                    ]
                }},
                "colorId": color id here (ensure that the classes are color coded),
                "recurrence": [
                    "RRULE:FREQ=DAILY;COUNT=5"  # Repeat daily for 5 occurrences (only include if recurrences are mentioned)
                ],
                "extendedProperties": {{
                    "private": {{
                        "className": "course code here (N/A when this is not for a canvas assignment)",
                        "assignmentName": "assignment name here (N/A when this is not for a canvas assignment)",
                        "priortiy": "an int between 1 and 10, 10 being high priority (something like a final would be a 10) (extra credit assignments would be a 1)",
                        "aiGenerated": "always set this to true"
                    }}
                }}
            }},
        ]
    """),
    ("user", "{input}")
])

# Create the chain that guarantees JSON output
chain = prompt_template | llm | parser


def schedule_events(user_input: str) -> dict:
    google_calendar = f"This is the user's current calendar, try to match the color schemes: {GOOGLE_CAL}"
    input = user_input, google_calendar
    result = chain.invoke({"input": input})
    print(json.dumps(result, indent=2))
    return result
