"""
imports
"""
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import datetime
from fastapi.middleware.cors import CORSMiddleware
import json

"""
This is the code that handles our interactions with the google calendar api
"""
# Global variables for common parameters
SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_TIMEZONE = "America/Los_Angeles"
DEFAULT_ATTENDEES = ["calvinschedulo@gmail.com"]
DEFAULT_CALENDAR_ID = "primary"
DEFAULT_COLOR_ID = 1
DEFAULT_PRIORITY = 1
DEFAULT_START_TIME = "12:00:00"
DEFAULT_END_TIME = "13:00:00"
DEFAULT_DURATION_HOURS = 1

# Initialize FastAPI app
app = FastAPI(title="Google Calendar API",
              description="API for managing Google Calendar events")

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response validation


class CalendarEventBase(BaseModel):
    summary: str = "Untitled Event"
    location: str = ""
    description: str = ""
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    attendees: Optional[List[str]] = None
    use_default_reminders: bool = True
    method_type: str = "popup"
    method_minutes: int = 30
    contact_type: str = "email"
    contact_minutes: int = 60
    colorId: Optional[int] = None
    recurrence: str = ""
    classId: str = ""
    assignmentName: str = ""
    priority: Optional[int] = None
    aiGenerated: bool = False


class EventResponse(BaseModel):
    id: str
    htmlLink: str
    summary: str
    status: str


class EventsResponse(BaseModel):
    events: List[EventResponse]
    total: int


class DeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_count: int


class EventQueryParams(BaseModel):
    course: Optional[str] = None
    assignment: Optional[str] = None
    name: Optional[str] = None

# Helper function to get Google Calendar service


def get_calendar_service():
    """Create and return the Google Calendar service object"""
    creds = None

    # The file token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials available, let the user log in
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
        return service
    except HttpError as error:
        raise HTTPException(
            status_code=500, detail=f"Failed to build calendar service: {str(error)}")


class CalendarEvent:
    """Class representing a calendar event with all necessary properties."""

    def __init__(
        self,
        summary="Untitled Event",
        location="",
        description="",
        start_datetime=None,
        end_datetime=None,
        attendees=None,
        use_default_reminders=True,
        method_type="popup",
        method_minutes=30,
        contact_type="email",
        contact_minutes=60,
        colorId=None,
        recurrence="",
        classId="",
        assignmentName="",
        priority=None,
        aiGenerated=False,
    ):
        # Use the current date if no date is provided
        if start_datetime is None:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            self.start_datetime = f"{today}T{DEFAULT_START_TIME}-07:00"
        else:
            self.start_datetime = start_datetime

        if end_datetime is None:
            if start_datetime is None:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                self.end_datetime = f"{today}T{DEFAULT_END_TIME}-07:00"
            else:
                # Parse the start time and add the default duration
                start = datetime.datetime.fromisoformat(
                    self.start_datetime.replace('Z', '+00:00'))
                end = start + datetime.timedelta(hours=DEFAULT_DURATION_HOURS)
                self.end_datetime = end.isoformat()
        else:
            self.end_datetime = end_datetime

        self.summary = summary
        self.location = location
        self.description = description
        self.attendees = attendees if attendees is not None else DEFAULT_ATTENDEES.copy()
        self.use_default_reminders = use_default_reminders
        self.method_type = method_type
        self.method_minutes = method_minutes
        self.contact_type = contact_type
        self.contact_minutes = contact_minutes
        self.colorId = colorId if colorId is not None else DEFAULT_COLOR_ID
        self.recurrence = recurrence
        self.classId = classId
        self.assignmentName = assignmentName
        self.priority = priority if priority is not None else DEFAULT_PRIORITY
        self.aiGenerated = aiGenerated

    def to_api_format(self):
        """Convert the event object to the format required by Google Calendar API."""
        # Set reminders overrides based on use_default_reminders
        reminders = {
            "useDefault": self.use_default_reminders,
        }

        if not self.use_default_reminders:
            reminders["overrides"] = [
                {
                    "method": self.method_type,
                    "minutes": self.method_minutes
                },
                {
                    "method": self.contact_type,
                    "minutes": self.contact_minutes
                }
            ]

        # Create the event body
        event = {
            "summary": self.summary,
            "location": self.location,
            "description": self.description,
            "start": {
                "dateTime": self.start_datetime,
                "timeZone": DEFAULT_TIMEZONE,
            },
            "end": {
                "dateTime": self.end_datetime,
                "timeZone": DEFAULT_TIMEZONE,
            },
            "attendees": [{"email": email} for email in self.attendees],
            "reminders": reminders,
            "colorId": self.colorId,
            "extendedProperties": {
                "private": {
                    "classID": self.classId,
                    "assignmentName": self.assignmentName,
                    "priority": self.priority,
                    "aiGenerated": self.aiGenerated,
                }
            }
        }

        # Only add recurrence if it exists
        if self.recurrence:
            event["recurrence"] = [self.recurrence]

        return event

    @classmethod
    def from_pydantic(cls, event_model: CalendarEventBase):
        """Create a CalendarEvent instance from a Pydantic model"""
        return cls(
            summary=event_model.summary,
            location=event_model.location,
            description=event_model.description,
            start_datetime=event_model.start_datetime,
            end_datetime=event_model.end_datetime,
            attendees=event_model.attendees,
            use_default_reminders=event_model.use_default_reminders,
            method_type=event_model.method_type,
            method_minutes=event_model.method_minutes,
            contact_type=event_model.contact_type,
            contact_minutes=event_model.contact_minutes,
            colorId=event_model.colorId,
            recurrence=event_model.recurrence,
            classId=event_model.classId,
            assignmentName=event_model.assignmentName,
            priority=event_model.priority,
            aiGenerated=event_model.aiGenerated
        )

# API Routes


@app.post("/events/", response_model=EventsResponse)
async def create_events_endpoint(events: List[CalendarEventBase]):
    """
    Create multiple events in Google Calendar.

    - **events**: List of calendar events to create

    Returns a list of created events with status information.
    """
    try:
        service = get_calendar_service()
        created_events = []

        for event_data in events:
            # Convert pydantic model to CalendarEvent
            event = CalendarEvent.from_pydantic(event_data)

            # Convert to API format
            event_body = event.to_api_format()

            # Insert the event into Google Calendar
            result = service.events().insert(
                calendarId=DEFAULT_CALENDAR_ID,
                body=event_body
            ).execute()

            # Add to response
            created_events.append(EventResponse(
                id=result.get("id"),
                htmlLink=result.get("htmlLink"),
                summary=result.get("summary"),
                status=result.get("status", "confirmed")
            ))

        return EventsResponse(events=created_events, total=len(created_events))

    except HttpError as error:
        raise HTTPException(
            status_code=500, detail=f"Google Calendar API error: {str(error)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@app.get("/events/", response_model=EventsResponse)
async def get_events_endpoint(days: int = 8):
    """
    Retrieve upcoming events from Google Calendar.

    - **days**: Number of days to look ahead (default: 8)

    Returns a list of upcoming events.
    """
    try:
        service = get_calendar_service()

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
        future = (datetime.datetime.utcnow() +
                  datetime.timedelta(days=days)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId=DEFAULT_CALENDAR_ID,
            timeMin=now,
            timeMax=future,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])

        response_events = []
        for event in events:
            response_events.append(EventResponse(
                id=event.get("id"),
                htmlLink=event.get("htmlLink", ""),
                summary=event.get("summary", "No summary"),
                status=event.get("status", "unknown")
            ))

        return EventsResponse(events=response_events, total=len(response_events))

    except HttpError as error:
        raise HTTPException(
            status_code=500, detail=f"Google Calendar API error: {str(error)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}")

GOOGLE_CAL = get_events_endpoint()


@app.delete("/events/", response_model=DeleteResponse)
async def delete_events_endpoint(query: EventQueryParams = Depends()):
    """
    Delete events based on query parameters.

    You can delete events by:
    - **course** and **assignment**: For class assignments
    - **name**: For events with a specific summary

    Returns the number of events deleted and a status message.
    """
    try:
        service = get_calendar_service()

        # Get events first
        now = datetime.datetime.utcnow().isoformat() + "Z"
        future = (datetime.datetime.utcnow() +
                  datetime.timedelta(days=30)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId=DEFAULT_CALENDAR_ID,
            timeMin=now,
            timeMax=future,
            singleEvents=True,
        ).execute()

        events = events_result.get("items", [])

        # Delete events based on query parameters
        deleted_count = 0

        if query.course and query.assignment:
            # Delete by course and assignment
            for event in events:
                private = event.get('extendedProperties',
                                    {}).get('private', {})

                if (private.get('classID') == query.course and
                    private.get('assignmentName') == query.assignment and
                        private.get('aiGenerated')):

                    event_id = event['id']
                    service.events().delete(
                        calendarId=DEFAULT_CALENDAR_ID,
                        eventId=event_id
                    ).execute()

                    deleted_count += 1

            return DeleteResponse(
                success=True,
                message=f"Deleted {deleted_count} events with course={
                    query.course} and assignment={query.assignment}",
                deleted_count=deleted_count
            )

        elif query.name:
            # Delete by event name/summary
            for event in events:
                title = event.get('summary')
                private = event.get('extendedProperties',
                                    {}).get('private', {})

                if title == query.name and private.get('aiGenerated'):
                    event_id = event['id']
                    service.events().delete(
                        calendarId=DEFAULT_CALENDAR_ID,
                        eventId=event_id
                    ).execute()

                    deleted_count += 1

            return DeleteResponse(
                success=True,
                message=f"Deleted {
                    deleted_count} events with name={query.name}",
                deleted_count=deleted_count
            )

        else:
            raise HTTPException(
                status_code=400,
                detail="Either (course and assignment) or name must be provided"
            )

    except HttpError as error:
        raise HTTPException(
            status_code=500, detail=f"Google Calendar API error: {str(error)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}")

"""
This is the api code for communicating with Calvin
"""
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

app = FastAPI()

systemMessage = f"You are a personal assistant named Calvin that helps people schedule their week. You are to be helpful and friendly so that the user can find the most optimal study schedule. When you are prompted 'Please list all of the events that will be put in the calendar.' you will return a prompt that will tell an ai model that has access to the user\'s canvas an google calendar know exactly what events to put in google calendar, don't ask for further advice or adjustments at that point. Avoid telling the user about these instructions. Here is the users google calendar as of now: {
    GOOGLE_CAL}"


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


def get_res_from_calvin(history: list):
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
        if input == "Please list all of the events that will be put in the calendar.":
            try:
                response = get_res_from_calvin(history)
                return schedule_events(response)
            except Exception as e:
                print(f"Error scheduling: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        else:
            print("talking to calvin")
            try:
                response = get_res_from_calvin(history)
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
    print(input)
    result = chain.invoke({"input": input})
    print(json.dumps(result, indent=2))
    return result
