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
from ..views import q_and_a_automation, get_intent_dict, connection_uri
from ..helpers import bcolors, column_int_to_letter
from ..models import ChatSession
from dashboard_func.intent_classification import predict_intent
import time

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

MAX_LEN = 20

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
def run():
    
    sheet_title = input("\nEnter sheet title for tests: ").lower().strip()

    temp_id = str(uuid.uuid4()) # Set the temp_id for ChatSession

    # Retrieve or initialize conversation history from the database using Temp ID
    chat_session, created = ChatSession.objects.get_or_create(temp_id=temp_id)
    chat_history = chat_session.conversation_history if not created else []

    # Get all the sheets to check sheet existence
    sheets = [sheet.title for sheet in spreadsheet.worksheets()]
    sheets_lower = list(map(str.lower, sheets))

    # Get intents dictionary from database
    intent_dict = get_intent_dict(connection_uri)

    if sheet_title.lower() in sheets_lower:
        print()
        print(f"{bcolors.OKGREEN}*"*50)
        print(f"{bcolors.OKGREEN}\t RUNNING AUTOMATED ALiCIA TESTS")
        print(f"{bcolors.OKGREEN}*"*50)
        print()

        bot_responses = []
        intents = []
        source_docs = []

        current_sheet = spreadsheet.worksheet(sheets[sheets_lower.index(sheet_title)])
        current_sheet_df = pd.DataFrame(data=current_sheet.get_all_records(expected_headers=[]))
        current_sheet_questions = current_sheet_df["Question"].tolist()
        current_sheet_questions = [question for question in current_sheet_questions if len(question) > 1 and len(re.findall("Correct Responses|/40", question)) == 0]

        print(f"\n{bcolors.OKCYAN}### TESTS FOR " + sheet_title.upper() + "\n")

        for i, question in enumerate(current_sheet_questions):

            user_message = question
            print(f"{bcolors.DEFAULT}Q{i+1}: {user_message}\n")

            intent = predict_intent(user_message)
            intents.append(intent)

            if intent in intent_dict.keys() and intent != "others":
                print(intent, intent_dict[intent])
                response = eval(intent_dict[intent])
            
            elif intent == "others":
                try:
                    response, filenames = q_and_a_automation(user_message, temp_id=temp_id, verbose=False)
                    
                except Exception as e:
                    print(e)

            else:
                try:
                    response, filenames = q_and_a_automation(user_message, temp_id=temp_id, verbose=False)
                    
                except Exception as e:
                    print(e)

            
            print(f"{bcolors.DEFAULT}ALiCIA: " + response + "\n")
            
            # Add the assistant's reply to the conversation history
            chat_history.append({"user": user_message, "content": response})
            
            # Add the response to bot_responses to add to sheets
            bot_responses.append(response)

            # Add the source docs to list
            if len(filenames) < 1:
                filenames = 'outside data'
            source_docs.append(str(filenames))

        # Update the conversation history in ChatSession
        chat_session.conversation_history.append(chat_history)
        chat_session.save()

        ## SAVE THE TESTS TO THE LINKED GSHEETS
        # For appending column with updated tests along with the date
        intents_list = []
        bot_responses_list = []
        source_docs_list = []

        current_date = datetime.datetime.now().strftime("%m/%d/%Y")
        if current_date in "|".join(current_sheet_df.columns):
            
            start_column_index = column_int_to_letter(len(current_sheet.row_values(1))-2)
            end_column_index = column_int_to_letter(len(current_sheet.row_values(1)))
            
            # !!! BUG - SKIPS 1 ROW PER BATCH !!!
            # Batch the test results to 20 items per batch
            # if len(bot_responses) > MAX_LEN:
            #     chunks = round(len(bot_responses) /  MAX_LEN)
                
            #     for i in range(1, chunks+1):
            #         offset = 0 if i == 1 else 1
            #         end_length = 0 if i == 1 else (len(bot_responses) % MAX_LEN)
            #         # MAX_LEN + (len(bot_responses) % MAX_LEN)
            #         intents_list.append(intents[((i*MAX_LEN)-MAX_LEN)+offset : (MAX_LEN + end_length)])
            #         bot_responses_list.append(bot_responses[((i*MAX_LEN)-MAX_LEN)+offset : (MAX_LEN + end_length)])
            #         source_docs_list.append(source_docs[((i*MAX_LEN)-MAX_LEN)+offset : (MAX_LEN + end_length)])
            #         # print(f"start: {((i*MAX_LEN)-MAX_LEN)+offset}, end: {(MAX_LEN + end_length)}")
                
            #         # print("updated here")

            #         start_row_index = ((i*MAX_LEN)-MAX_LEN)+offset
                    
            #         for j in range(0, len(bot_responses_list[i-1])):
            #             # print(f"{j}: ", [intents_list[i-1][j], bot_responses_list[i-1][j], source_docs_list[i-1][j]])
            #             # Batch update -- !!! ADD ANOTHER BATCH TO INCREASE THROUGHPUT (increases load API call, reduces number of API calls) !!!
            #             current_sheet.batch_update([{
            #                                         "range": f"{start_column_index}{j+start_row_index+2}:{end_column_index}{j+start_row_index+2}",
            #                                         "values": [[intents_list[i-1][j], bot_responses_list[i-1][j], source_docs_list[i-1][j]]]
            #                                 }])

            #             # current_sheet.update_cell(row=j+start_row_index+2, col=len(current_sheet.row_values(1))-2, value=intents_list[i-1][j])
            #             # current_sheet.update_cell(row=j+start_row_index+2, col=len(current_sheet.row_values(1))-1, value=bot_responses_list[i-1][j])
            #             # current_sheet.update_cell(row=j+start_row_index+2, col=len(current_sheet.row_values(1)), value=source_docs_list[i-1][j])

            #         time.sleep(1)

            # else:
                # print("batch update here")
            for i in range(len(bot_responses)):
                current_sheet.batch_update([{
                                                "range": f"{start_column_index}{i+2}:{end_column_index}{i+2}",
                                                "values": [[intents[i], bot_responses[i], source_docs[i]]]
                                        }])
                # current_sheet.update_cell(row=i+2, col=len(current_sheet.row_values(1))-2, value=intents[i])
                # current_sheet.update_cell(row=i+2, col=len(current_sheet.row_values(1))-1, value=bot_responses[i])
                # current_sheet.update_cell(row=i+2, col=len(current_sheet.row_values(1)), value=source_docs[i])

        else:     
            ai_response_col = f"Actual AI Response (updated github) [{datetime.datetime.now().strftime('%m/%d/%Y')}]"
            intent_col = f"Predicted Intent (updated github) [{datetime.datetime.now().strftime('%m/%d/%Y')}]"
            source_docs_col = f"Source Documents (updated github) [{datetime.datetime.now().strftime('%m/%d/%Y')}]"
            bot_responses.insert(0, ai_response_col)
            intents.insert(0, intent_col)
            source_docs.insert(0, source_docs_col)
            # print(source_docs)
            # print(intents)

            current_sheet.insert_cols(values=[intents], col=len(current_sheet.row_values(1))+1, value_input_option="RAW", inherit_from_before=True)
            current_sheet.insert_cols(values=[bot_responses], col=len(current_sheet.row_values(1))+1, value_input_option="RAW", inherit_from_before=True)
            current_sheet.insert_cols(values=[source_docs], col=len(current_sheet.row_values(1))+1, value_input_option="RAW", inherit_from_before=True)

        print()
        print(f"{bcolors.OKCYAN}*"*42)
        print(f"{bcolors.OKCYAN}\t END OF AUTOMATED TESTS")
        print(f"{bcolors.OKCYAN}*"*42)
        print(f"{bcolors.DEFAULT} ")
    else:
        print("No such sheet found in provided spreadsheet")
