from django.test import TestCase

# Import for test automation
from google.oauth2 import service_account
import gspread
import ast
import os
import datetime
import uuid
import pandas as pd
import random
import re

from dotenv import load_dotenv

# Imports for views and helpers
from .views import q_and_a_noncoe
from .helpers import bcolors
from .models import ChatSession
from dashboard_func.intent_classification import predict_intent

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

## Necessary steps for connecting to Google Sheets API
# Set the Google Service credentials for GSheets API
gservice_creds = service_account.Credentials.from_service_account_info(ast.literal_eval(os.getenv("GOOGLE_SERVICE_CREDS")))

# Assign the right "API Scope" to the credentials so that it has the right permissions to interface with GSheet spreadsheet
scope = ['https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive']
creds_with_scope = gservice_creds.with_scopes(scope)

# Create GSheet client with these scoped credentials
gsheet_client = gspread.authorize(creds_with_scope)

# Get the sheet you want to work on
spreadsheet = gsheet_client.open_by_url("https://docs.google.com/spreadsheets/d/1CHBV7NEz8VFCz26QOxXDWpGg2wNlstr7cF6OSSOoCyE/edit?usp=sharing")

# Function for running tests for ALiCIA using provided spreadsheet
def run_alicia_tests(request):
    
    sheet_title = input("\nEnter sheet title for tests: ").lower().strip()

    temp_id = str(uuid.uuid4()) # Set the temp_id for ChatSession

    # Retrieve or initialize conversation history from the database using Temp ID
    chat_session, created = ChatSession.objects.get_or_create(temp_id=temp_id)
    chat_history = chat_session.conversation_history if not created else []

    # Get all the sheets to check sheet existence
    sheets = [sheet.title for sheet in spreadsheet.worksheets()]
    sheets_lower = list(map(str.lower, sheets))

    if sheet_title.lower() in sheets_lower:
        print()
        print(f"{bcolors.OKGREEN}*"*50)
        print(f"{bcolors.OKGREEN}\t RUNNING AUTOMATED ALiCIA TESTS")
        print(f"{bcolors.OKGREEN}*"*50)
        print()

        bot_responses = []
        intents = []

        current_sheet = spreadsheet.worksheet(sheets[sheets_lower.index(sheet_title)])
        current_sheet_df = pd.DataFrame(data=current_sheet.get_all_records(expected_headers=[]))
        current_sheet_questions = current_sheet_df["Question"].tolist()
        current_sheet_questions = [question for question in current_sheet_questions if len(question) > 1 and len(re.findall("Correct Responses|/40", question)) == 0]

        print(f"\n{bcolors.OKCYAN}### TESTS FOR " + sheet_title.upper() + "\n")

        for i, question in enumerate(current_sheet_questions):

            user_input = question
            print(f"{bcolors.DEFAULT}Q{i+1}: {user_input}\n")

            intent = predict_intent(user_input)
            intents.append(intent)

            if intent == 'greeting':
                responses = ["Hi! How may I help you?",
                            "Hello! Please let me know how I can assist you.",
                            "Greetings! Is there anything I can help you with? Please send a message below."]
                response = random.choice(responses)

            elif intent == 'coe':
                # Use the agent to generate a response
                try:
                    response = q_and_a_noncoe(request, user_input, temp_id=temp_id, verbose=False)
                    
                except Exception as e:
                    print(e)

            elif intent == "live_agent":
                if any(keyword in user_input.lower() for keyword in ["live agent availabe", "talk live agent", "live agent"]):
                    response = "We have a live agent available, should I contact the live agent for you?"
                else:
                    response = "I'm sorry but I am unable to respond to your query, may I interest you into talking with a live agent?"

            elif intent == "servicenow":
                response = "Do you want to access ServiceNow tickets?"

            elif intent == "others":
                # Use the agent to generate a response
                try:
                    response = q_and_a_noncoe(request, user_input, temp_id=temp_id, verbose=False)
                    
                except Exception as e:
                    print(e)
            
            print(f"{bcolors.DEFAULT}ALiCIA: " + response + "\n")
            
            # Add the assistant's reply to the conversation history
            chat_history.append({"user": user_input, "content": response})
            
            # Add the response to bot_responses to add to sheets
            bot_responses.append(response)

        # Update the conversation history in ChatSession
        chat_session.conversation_history.append(chat_history)
        chat_session.save()

        ## SAVE THE TESTS TO THE LINKED GSHEETS
        # For appending column with updated tests along with the date
        current_date = datetime.datetime.now().strftime("%b %d")
        if current_date in "|".join(current_sheet_df.columns):

            for i in range(len(bot_responses)):
                current_sheet.update_cell(row=i+2, col=len(current_sheet.row_values(1))-1, value=intents[i])
                current_sheet.update_cell(row=i+2, col=len(current_sheet.row_values(1)), value=bot_responses[i])
        else:
            ai_response_col = f"Actual AI Response ({datetime.datetime.now().strftime('%b %d')})"
            intent_col = f"Predicted Intent ({datetime.datetime.now().strftime('%b %d')})"
            bot_responses.insert(0, ai_response_col)
            intents.insert(0, intent_col)

            current_sheet.insert_cols(values=[intents], col=len(current_sheet.row_values(1))+1, value_input_option="RAW", inherit_from_before=True)
            current_sheet.insert_cols(values=[bot_responses], col=len(current_sheet.row_values(1))+1, value_input_option="RAW", inherit_from_before=True)


        # # For checking column existence to perform explicit update on that column
        # # Check existence of Intent and AI Response columns
        # if "Intent" not in "|".join(current_sheet_df.columns) and "AI Response" in "|".join(current_sheet_df.columns):
        #     intents.insert(0, "Predicted Intent")
        #     current_sheet.insert_cols([intents], col=4, value_input_option="user_entered", inherit_from_before=True)

        #     for i in range(len(bot_responses)):
        #         current_sheet.update(range_name=f"E{i+2}", values=[[bot_responses[i]]])
        
        # elif len(re.findall("(Intent|AI Response)", "|".join(current_sheet_df.columns.tolist()))) > 1:
            
        #     for i in range(len(bot_responses)):
        #         current_sheet.update(range_name=f"D{i+2}:E{i+2}", values=[[intents[i], bot_responses[i]]])

        # else:
        #     print("start here")
        #     bot_responses.insert(0, "Actual AI Response")
        #     intents.insert(0, "Predicted Intent")
        #     current_sheet.insert_cols([intents], col=4, value_input_option="user_entered", inherit_from_before=True)
        #     current_sheet.insert_cols([bot_responses], col=5, value_input_option="user_entered", inherit_from_before=True)
        
        print()
        print(f"{bcolors.OKCYAN}*"*42)
        print(f"{bcolors.OKCYAN}\t END OF AUTOMATED TESTS")
        print(f"{bcolors.OKCYAN}*"*42)
        print(f"{bcolors.DEFAULT} ")
    else:
        print("No such sheet found in provided spreadsheet")
