from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

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
                    "canvasSpecific": {"type": "bool"}
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
                    "RRULE:FREQ=DAILY;COUNT=5"  # Repeat daily for 5 occurrences
                ],
                "extendedProperties": {{
                    "private": {{
                        "className": "course code here (N/A when this is not for a canvas assignment)",
                        "assignmentName": "assignment name here (N/A when this is not for a canvas assignment)",
                        "priortiy": "an int between 1 and 10, 10 being high priority (something like a final would be a 10) (extra credit assignments would be a 1)",
                        "canvasSpecific": "true if we are using this time to finish a canvas assignment"
                    }}
                }}
            }},
            # Add more events here...
        ]
    """),
    ("user", "{input}")
])

# Create the chain that guarantees JSON output
chain = prompt_template | llm | parser


def schedule_event(user_input: str) -> dict:
    result = chain.invoke({"input": user_input})
    print(json.dumps(result, indent=2))
    return result


# Example usage
user_input = input('What would you like to schedule? ')
schedule_event(user_input)
