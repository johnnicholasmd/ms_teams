import json, os, psycopg2, requests, re, ast
from dotenv import load_dotenv
from dateutil import parser as date_parser
from datetime import datetime as dt
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from workflow_func.authentication import decode_and_validate_token
from bs4 import BeautifulSoup

from openai import OpenAI


from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from django.shortcuts import  redirect,render
import requests
from django.conf import settings


#access env
load_dotenv()
gpt3_prompt = os.getenv('GPT3_PROMPT')
instance = os.getenv('INSTANCE')
headers= {"Content-Type": "application/json", "Accept": "application/json"}

#PostgreSQL Database Connection
connection_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

conversation_history = []  # Store conversation history
workflow_instances = {}

inc = 0
answers = []
questions = []
stage = 1

#tables
inc_table=f"https://{instance}.service-now.com/api/now/table/incident"
sys_user_tbl=f"https://{instance}.service-now.com/api/now/table/sys_user"
table_url=f"https://{instance}.service-now.com/api/now/table"
sys_journal_tbl = f"https://{instance}.service-now.com/api/now/table/sys_journal_field"



try:
    # Attempt to establish a connection
    conn = psycopg2.connect(connection_uri)
    conn.close()
    print("Connection successful")
except psycopg2.Error as e:
    # Handle connection errors
    print(f"Error connecting to the database: {e}")
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


"""New Refresh session variables"""
def refresh_workflow_variables(temp_id):
    #attempts to update the workflow instances if temp_id exists in the dictionary
    try:
        workflow_instances[temp_id].update(
            {'questions': [],
            'question_index': 0,
            'ai_response_index':1,
            'filing_data': {},
            'list_of_questions_asked':[]
            }
        )
    except:
        workflow_instances[temp_id] = None

@csrf_exempt
def get_snow_creds(request):
    # get creds
    user_token = request.session['user_token']
    pwd_token = request.session['pwd_token']
    
    if user_token and pwd_token:
        try:
            user = decode_and_validate_token(user_token)['sub']
            pwd = decode_and_validate_token(pwd_token)['sub']
            
            return user, pwd
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Tokens not found'}, status=400)


#Function that obtains token for secured email sending 
def get_email_token():
    token_url = os.getenv("token_url")
    credentials = {"email": os.getenv("email"), "password": os.getenv("password")}

    headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json'
    }

    response = requests.post(token_url, headers=headers, json=credentials).json()
    return response['token']


#Function of sending email via 77 email service
def send_email_to_all(token, user_email, user_name, assignee_email, email_content, assignee_name, ticket_number):
    bearer = f"Bearer {token}"
    print(f"bearer: {bearer}")
    if token is not None:
        secured_send_url = os.getenv("secured_send_url")
        headers = {
            'Accept':'*/*',
            'Content-Type': 'application/json',
            'Authorization': bearer}
    else:
        secured_send_url = os.getenv("unsec_endpoint")
        headers = {
        'Accept':'*/*',
        'Content-Type': 'application/json'
        }

    cc_email = "sacdalanpamela@gmail.com"

    
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; font-size: 14px;">
        Greetings {assignee_name}!<br><br>
        <p>This is an automated follow-up on behalf of {user_name}, regarding a recent ticket {ticket_number}.</p> <br>
        <p>{user_name} has reached out to us regarding an inquiry, and we want to ensure that their concern is being addressed promptly. 
            We kindly request your attention to this matter to provide the necessary assistance and resolution. Refer to the message below. </p> <br> 
            
            <pre>{email_content}</pre><br>

            <p>If you have any updates or require further information to proceed with resolving the ticket, 
                please don't hesitate to reach out to them directly or update the ticket accordingly. </p>
            <br>
             <p>Thank you for your attention to this matter and your commitment to providing excellent service to our customers.</p>
            Thank you.
            
        </body>
    </html>
    """

    data = {
    "emailBcc":"",
    "emailBody":html,
    "emailCc": f"{cc_email}; {user_email}",
    "emailFrom":"alicia-chatbot@77soft.com",
    "emailSubject":f"Follow-up on Ticket {ticket_number}",
    "emailTo":assignee_email}
    
    send_response = requests.post(secured_send_url, headers=headers, json=data)
    print("Here is the send_response : ", send_response)



"""NEW EXIT MESSAGE"""
def exit_workflow_message(intent):
	exit_message = f"{intent.replace('_',' ')} process has been canceled. \n\nIf you have any additional inquiries or require assistance, please feel free to ask."
	return exit_message




def add_example_in_question(question_type, question, header, choices_redirect, select_from_choices, question_index, intent):
    
    is_question_altered = False
    if question_type == 'date':
        is_question_altered = True
        question += f" Please type date in 'MM/DD/YYYY'. Ex. {dt.now().strftime('%m/%d/%Y')}"

    elif question_type == 'yes_no':
        is_question_altered = True
        question += f" \n\nType 'Yes' or 'No'. "

    #question not yet altered
    if not is_question_altered:

        #choices_redirect_to_section has value
        if choices_redirect != '' and choices_redirect != 'None' and choices_redirect != 'Null' and choices_redirect is not None:

            choices_redirect = ast.literal_eval(choices_redirect) #dictonary
            choices_redirect = [i for i in choices_redirect]

            if select_from_choices == 'True':
                #Limited choices
                question += "\n\nPlease only choose from"
                for index, element in enumerate(choices_redirect):
                    if index == len(choices_redirect)-1: #last element
                        question += f" or '{element}'."
                    else:
                        question += f" '{element}',"
            else:
                #You have the freedom to choose
                question += "\n\nYou can select either option"
                for index, element in enumerate(choices_redirect):
                    if index == len(choices_redirect)-1: #last element
                        question += f" or '{element}'."
                    else:
                        question += f" '{element}',"
                # question += "\nIf none of these options is suitable, please provide your own choice."
    if question_index == 0:
        question += f"\n\n[If at any point of the Ticket Creation you want to cancel, please type 'EXIT'.]"
    return question

#validator for user's answer
def validate_answer(question_type, user_message, question):
    if question_type == "emp_id":
        pattern = re.compile(r'^\d{2}-\d{4}$')
        if bool(pattern.match(user_message)):
            ai_message = None
        else:
            ai_message =f"'{user_message}' is invalid. Please Type Employee ID in right format. Ex. '19-1234'. "
    
    elif question_type == "date":
        accepted_format = ["%m/%d/%Y","%#m/%d/%Y","%#m/%#d/%Y","%m/%#d/%Y"]
        
        try:
            parsed_date = date_parser.parse(user_message)
            if any(parsed_date.strftime(format).lower() == user_message.strip().lower() for format in accepted_format):
                parsed_date = date_parser.parse(user_message)
                string_date = parsed_date.strftime("%B %d, %Y")
                user_message = string_date
                ai_message = None
            
            #date is not in the correct format
            else:
                raise ValueError
        except:
            ai_message =f"'{user_message}' is invalid date.\n\n {question} Please type date in 'MM/DD/YYYY'. Ex. {dt.now().strftime('%m/%d/%Y')}"
    
    elif question_type =="yes_no":
        if  user_message.lower() == "yes" or user_message.lower() == "no":
            ai_message = None
        else:
            ai_message =f"'{user_message}' is invalid. \n\n{question} \n\nPlease Type 'Yes' or 'No'."

    else:
        ai_message = None
    return user_message, ai_message

@csrf_exempt
def subcategory_select(request, user_selected_category):
    # user = os.getenv('USER')
    # pwd = os.getenv('PWD')
    
    user, pwd = get_snow_creds(request)
    
    #Fetch subcategory list based from the category selected by user
    sub_category_url = f"{table_url}/sys_choice?sysparm_query=name=incident^element=subcategory^dependent_value={user_selected_category}&sysparm_fields=label"
    subcategories= requests.get(sub_category_url, auth=(user, pwd), headers=headers, timeout=(5, 10) ).json()
    labels =  [item['label'] for item in subcategories['result']]
    subcategory_string_list =  json.dumps(labels)
    print(subcategory_string_list)
    
    # question += f"\n\nSelect from the following: \n {subcategory_string_list}"
    
    return subcategory_string_list

@csrf_exempt
def create_ticket(request, temp_id):  

    # user = os.getenv('USER')
    # pwd = os.getenv('PWD')
    user, pwd = get_snow_creds(request)

    # Fetch all categories from SNow    
    category_url = f"{table_url}/sys_choice?sysparm_query=name=incident^element=category&sysparm_fields=label"
    category_list = requests.get(category_url, auth=(user, pwd), headers=headers ).json()
    labels =  [item['label'] for item in category_list['result']]
    result_dict = {label: 'None' for label in labels}
    category_string_list =  json.dumps(result_dict)
    
    #requires intent ex. 'create_ticket', 'ticket_details', etc.
    intent = workflow_instances[temp_id]['intent']    
    try:
        data = json.loads(request.body)
        user_message = data.get('userMessage', '')
        # start_time = time.time()
        
    except json.JSONDecodeError:
        response = {'reply': 'Invalid JSON data'}
        return JsonResponse(response, status=400)
    
    if user_message.lower() == 'exit':
        # refresh_workflow_variables(temp_id)
        del workflow_instances[temp_id]
        exit_message = exit_workflow_message(intent)
        response = {"message" : exit_message,
                        "innerIntent" : False,
                        "intent" : "create_ticket_flow"}
        return JsonResponse(response)
    

    elif any(keyword in user_message.lower() for keyword in ["modify", "change"]):
        refresh_workflow_variables(temp_id)

    #create request.session coe variables if not yet created
    # if 'questions' not in request.session:
    #     refresh_workflow_variables(request)
    
    # Retrieve user input that was not answered by the bot
    chat_history = request.session['chat_history']
    most_recent_entry = chat_history[-1]
    ticket_issue = most_recent_entry['content']['user_input']
    # print(ticket_issue)
 
    
    
    #update or initialize the variables of the temp id workflow instance
    if 'questions' not in workflow_instances[temp_id]:
        refresh_workflow_variables(temp_id)

    #simplifies the variable names of session variables for easy reference inside this 'create ticket function'
    questions = workflow_instances[temp_id]['questions']            #list [] that will contain all the questions extracted from db on a specific 'purpose'
    question_index = workflow_instances[temp_id]['question_index']  #an index (starts with 0) that references/iterates through the questions, increments accordingly
    ai_response_index =  workflow_instances[temp_id]['ai_response_index']   #an index (starts with 1) that iterates through the ai response under coe intent used in if-elif-else statements, increments accordingly
    filing_data = workflow_instances[temp_id]['filing_data']        #dict {}, stores the 'header' and 'coe data content request' inputted by the user
    list_of_questions_asked = workflow_instances[temp_id]['list_of_questions_asked']

    #fetch all the section 1 questions
    if ai_response_index == 1:
        if len(questions) == 0:
            if ticket_issue == "create ticket intent":
                print("Entered create_ticket intent")
                sql_query = f"SELECT * FROM servicenow.snow_questions WHERE intent = 'create_ticket' AND section = (SELECT MIN(section) from servicenow.snow_questions where intent = 'create_ticket' ) ORDER BY question_sequence;" 
                with psycopg2.connect(connection_uri) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql_query)
                        columns = [desc[0] for desc in cursor.description]  # Get column headers
                        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                        questions = results #save the results to questions variable
            else:
                print("Entered create_ticket_w_desc intent")
                sql_query = f"SELECT * FROM servicenow.snow_questions WHERE intent = 'create_ticket_w_desc' AND section = (SELECT MIN(section) from servicenow.snow_questions where intent = 'create_ticket_w_desc' ) ORDER BY question_sequence;" 
                with psycopg2.connect(connection_uri) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql_query)
                        columns = [desc[0] for desc in cursor.description]  # Get column headers
                        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                        questions = results #save the results to questions variable
                        
        while True:

            #only executed if all questions including follow ups were asked
            if len(questions) == (question_index):
                ai_response_index +=1
                break
            
            question_id = questions[question_index]['id']                                       #'id': 1        
            question_type = questions[question_index]['question_type']                          #'question_type': 'text'
            header = questions[question_index]['header']                                        #'header': 'category'          
            question = questions[question_index]['question']                                    #'question': 'Provide short description'
            choices_redirect = questions[question_index]['choices_redirect_to_section']         
            select_from_choices = questions[question_index]['select_from_choices'].capitalize() #'select_from_choices': 'True'

            #The question was not asked yet, hence ask
            if question_id not in list_of_questions_asked:
                filing_data[header] = None
                list_of_questions_asked.append(question_id)
                
                if header.lower() == 'confirmation':
                    question += f"\n\n <i>{ticket_issue}</i>" # adds the issue to the question, to be confirmed by the user
                    

                #calls the function to add example of user input
                question = add_example_in_question(question_type, question, header, choices_redirect, select_from_choices, question_index, intent)
                        
                # Initialize subcategory_string_list
                subcategory_string_list = None
                
                # store user's selected category
                if header.lower() == 'subcategory':
                    user_selected_category = user_message
                    # print(user_selected_category)
                    
                    subcategory_string_list = subcategory_select(request, user_selected_category)
                    # print(subcategory_string_list)      
                
                #return the question with example inputs at the end
                response = {"message" : question,
                     "header": header,
                     "choices": choices_redirect,
                     "category": category_string_list,
                     "subcategory" : subcategory_string_list,     
                     "innerIntent" : True,
                     "intent" : "create_ticket_flow"}
                # print('Question Type: ', question_type)
                # print('Question: ', question)
                # print('Header: ', header)
                # print('Choices Redirect: ', choices_redirect)
                # print('Select From Choices: ', select_from_choices)
                # print('Question Index: ', question_index)
                # print('Intent: ', intent)
                
                break

            #Question is already asked. Validate the user's answer.
            else:
                
                if header.lower() == 'confirmation':
                    question += f"\n\n <i>{ticket_issue}</i>"
                    confirmation = user_message
                    print(f'confirmation: {confirmation}')
                    
                user_message, ai_message = validate_answer(question_type, user_message, question)
                
                if ai_message is not None:
                    response = { "message" : ai_message,
                                "innerIntent" : True,
                                "intent" : "create_ticket_flow"}
                    break

                #There is a redirect value (or follow up question) based on user's answer
                if choices_redirect != '' and choices_redirect != None:

                    #convert the string to python dictionary
                    choices_redirect = ast.literal_eval(choices_redirect) 
                    
                    last_element = [i for i in choices_redirect][-1]    #get the last element
                    break_both_loops = False
                    for key, value in choices_redirect.items():         #key = 'Travel     value = 'SECTION 2'
                        
                        #user answer matched with the available choice
                        if key.lower() == user_message.lower():

                            if (value !='None' and value is not None):  #The choice redirects to a known 'SECTION X'
                                #get the new question
                                sql_query = f"SELECT * FROM servicenow.snow_questions WHERE intent = 'create_ticket' AND section = '{value}' ORDER BY question_sequence;" 

                                with psycopg2.connect(connection_uri) as conn:
                                    with conn.cursor() as cursor:
                                        cursor.execute(sql_query)
                                        columns = [desc[0] for desc in cursor.description]  # Get column headers
                                        new_results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                                        
                                        questions[question_index+1:question_index+1] = new_results  #Insert the follow up questions to the next index
                                        filing_data[header] = user_message
                                        print(f" ---> header: {header}, filing_data[{header}]: {filing_data[header]}")
                                        question_index += 1
                                       
                                        break #break the for loop on key, value in choices_redirect.items()
            
                            else: #The choice doesnt redirect to a known section, hence record user's answer
                                filing_data[header] = user_message
                                question_index += 1
                       
                                break

                        #user's answer didnt match with the available choice
                        else:

                            #enters here if the question is not strict on the answer, and
                            #the for loop is on the last element
                            if select_from_choices == 'False' and key == last_element:
                                filing_data[header] = user_message
                                question_index += 1
                                break #break the for loop

                            else: #Not yet on the last element and/or not strict on the answer

                                #If question is strict (on the choices) and already in the last element
                                if select_from_choices == 'True' and key == last_element:
                                    choices_list = [i for i in choices_redirect]
                                    choices_string =""
                                    for index, element in enumerate(choices_list):
                                        if index == len(choices_list)-1:
                                            choices_string += f"or '{element}'."
                                        else:
                                            choices_string += f"'{element}', "
                                    response = { "message" : f"'{user_message}' is invalid. \n\n{question} Choices are only: {choices_string}",
                                                "innerIntent" : True,
                                                "intent" : "create_ticket_flow"}
                                    break_both_loops = True     #aims to break the while loop
                                    break   #breaks the for loop

                                #Enters the else: if strict on the choices (True) but not yet on the last element
                                #If not strict on the choices (False) and not yet on last element
                                else: 
                                    continue # the for loop

                    if break_both_loops:
                        break #break the while loop


                #There is no redirect value (or no follow up question), simply record the answer of the user
                else:
                    filing_data[header] = user_message
                    question_index += 1
                    continue
                        
                    
    #provide summary of the request
    if ai_response_index == 2:
        
        # Conditional check for confirmation, assigns ticket_issue as short_description
        if 'confirmation' in filing_data:
            if filing_data['confirmation'].lower() == 'yes':
                filing_data['short_description'] = ticket_issue
        
        #Gives Ticket Creation Summary
        summary = "Ticket Summary:\n*************************\n"
        if filing_data['openedby'] == 'Me':
         
            filing_data['openedby'] = user
            filing_data['updated_by'] = user
            print(filing_data['updated_by'])
            
            for key, value in filing_data.items():
                if key != 'confirmation':
                    summary += f"""{key.capitalize().replace("_"," ")}: {value}\n"""
            summary += "\nDo you want to proceed?"
            response = {"message" : summary,
                        "innerIntent" : True,
                        "intent" : "create_ticket_flow",
                        "index" : 4
                        }
            ai_response_index +=1
            filing_data['caller_id'] = user
        else:
            filing_data['updated_by'] = user
            items_list = list(filing_data.items())

            for key, value in items_list: 
                if key != 'confirmation' and key != 'openedby': # displays filing data except confirmation and openedby
                    summary += f"""{key.capitalize().replace("_"," ")}: {value}\n"""
            summary += "\nDo you want to proceed?"
            response = {"message" : summary,
                        "innerIntent" : True,
                        "intent" : "create_ticket_flow",
                        "index" : 4
                        }
            ai_response_index +=1

       
    #3, asks if proceed in saving, modify or back to intent classification
    elif ai_response_index == 3:

        if not any(keyword in user_message.lower() for keyword in ["yes", "no", "exit", "modify"]):
            response = {"message" : f"I didn't quite get that. Do you want to proceed with your {intent.upper()} request? [Kindly type in Yes/Modify/No]",
                         "innerIntent" : True,
                         "intent" : "create_ticket_flow",
                        "index" : 5
                        }
        else:
            if "yes" in user_message.lower():
                 #saves the request in db
                 with requests.Session() as session:
                    response = session.post(inc_table, json=filing_data, auth=(user, pwd), headers=headers)
                    print(filing_data)
                    if response.status_code == 201:
                        ticket_data = response.json().get("result", {})
                        ticket_number = ticket_data.get("number", "Unknown")
                        # response = f"\nTicket created successfully with number: {ticket_number}"
                        message = f"Your {intent.replace('_',' ')} request has been submitted! Kindly see ticket number {ticket_number} for reference.\n\n Thank you!"
                        response = {"message": message,
                                "innerIntent": False}
            
                    else:
                        message = f"Failed to {intent.replace('_',' ')}"
                        response = {"message": message,
                                "innerIntent": False}



            elif user_message.lower()=="no":
                #gets out of the workflow intent
                response = {"message":exit_workflow_message(intent),
                            "innerIntent": False
                            }
                
            ai_response_index = 1
            questions = []
            question_index = 0
            filing_data = {}
            list_of_questions_asked = []


    #convert back the simplified variables to its corresponding session coe variables
    workflow_instances[temp_id]['questions'] = questions
    workflow_instances[temp_id]['question_index'] = question_index
    workflow_instances[temp_id]['ai_response_index'] = ai_response_index
    workflow_instances[temp_id]['filing_data'] = filing_data
    workflow_instances[temp_id]['list_of_questions_asked'] = list_of_questions_asked
    return JsonResponse(response)

@csrf_exempt
def ticket_count(request,temp_id):
    
    #requires intent ex. 'create_ticket', 'ticket_details', etc.
    intent = workflow_instances[temp_id]['intent']  

    try:
        data = json.loads(request.body)
        user_message = data.get('userMessage', '')
        print(user_message)
        # start_time = time.time()
        
    except json.JSONDecodeError:
        response = {'reply': 'Invalid JSON data'}
        return JsonResponse(response, status=400)
    
    if user_message.lower() == 'exit':
        # refresh_workflow_variables(temp_id)
        del workflow_instances[temp_id]
        exit_message = exit_workflow_message(intent)
        response = {"message" : exit_message,
                        "innerIntent" : False,
                        "intent" : ""
                    }
        return JsonResponse(response)
    with requests.Session() as session:
        relevant_info = fetch_data_from_api(request, session)
        update_gpt3_prompt(relevant_info)
        user, pwd = get_snow_creds(request)
        sys_id = get_sys_id(request,session)
        inc_table1=f"https://{instance}.service-now.com/api/now/table/incident?sysparm_query=assigned_to={sys_id}^sysparm_fields=number%2Cshort_description"
        response = session.get(inc_table1, auth=(user, pwd), headers=headers)
        gpt3_prompt = " "  #reset prompt
        data = response.json()
       
         
        if 'result' in data and isinstance(data['result'], list):
            for incident in data['result']:
                incident_number = incident.get('number', '')
                short_description = incident.get('short_description', '')
                
                # assigned_to_value = ''
                # assigned_to = incident.get('assigned_to')
                # if assigned_to and isinstance(assigned_to, dict):
                #     assigned_to_value = assigned_to.get('value', '')
                        
                # if assigned_to is not None and assigned_to != "":
                #     link_parts = assigned_to['link'].split('/')
                #     assigned_to = link_parts[-1]
                #     assigned_to_details = get_user(request,session, assigned_to)
                # else:
                #     assigned_to_details = "not yet assigned to anyone"
                        
                gpt3_prompt += (
                    f"Incident Number: {incident_number},"
                    f"Short Description  : {short_description}\n "
                    
                )
            gpt3_messages = [
                    {"role": "system", "content": f"The user is {user}.Answer the user giving the total count of the ticket and  list of incident with short description that is currently assigned to him/her. "},
                    {"role": "user", "content": gpt3_prompt},
                ]

            chat_completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=gpt3_messages
                )

            message = chat_completion.choices[0].message.content.strip() 
                        
                    
    # with requests.Session() as session:
    #     relevant_info = fetch_data_from_api(session)
    #     update_gpt3_prompt(relevant_info)

    #     incident_count = len(relevant_info)
    #     message = f"The total number of incidents is {incident_count}."

    response = {"message": message,
                    "innerIntent": False}
    #     print(response)
    return JsonResponse(response)


first_question = "yes"

@csrf_exempt
def check_ticket_number(request, temp_id):
    intent = workflow_instances[temp_id]['intent']
    global first_question
    try:
        data = json.loads(request.body)
        user_message = data.get('userMessage', '')
       

    except json.JSONDecodeError:
        response = {'reply': 'Invalid JSON data'}
        return JsonResponse(response, status=400)
    
    

    if user_message.lower() == 'exit':
        del workflow_instances[temp_id]
        exit_message = exit_workflow_message(intent)
        response = {"message": exit_message, "innerIntent": False, "intent": "CHECK_TICKET_NUMBER"}
        return JsonResponse(response)
    
    user_input = generate_ai_response(user_message, "Analyze the intent of the user. Determine if the user has forgotten their ticket number. Strictly answer yes or no without a period. \
                                                                  Refer to this: \
                                                                 \
                                                                  - Sample statements indicating forgotten ticket number: 'I can't find my ticket number', 'I forgot my ticket number', 'Where can I find my ticket number?', 'I don't remember my ticket number', 'How do I retrieve my ticket number?', 'I lost my ticket number', 'Can you help me with my ticket number?', 'I need help with my ticket number'. \
                                                                     ")
    print(f"is_forgotten_ticket_number:{user_input}")
    print(f"is it first question:{first_question}")
    if user_input.lower() == "yes" and first_question == "no":
        with requests.Session() as session:
            user, pwd = get_snow_creds(request)
            inc_table1=f"https://{instance}.service-now.com/api/now/table/incident?sysparm_query=ORDERBYDESCsys_created_on&sysparm_fields=number%2Csys_created_on%2Ccaller_id&sysparm_limit=5"
            response = session.get(inc_table1, auth=(user, pwd), headers=headers)
            gpt3_prompt = " "  #reset prompt
            data = response.json()
            if 'result' in data and isinstance(data['result'], list):
                for incident in data['result']:
                    incident_number = incident.get('number', '')
                    caller_id_value = ''
                    caller_id = incident.get('caller_id')
                    if caller_id and isinstance(caller_id, dict):
                        caller_id_value = caller_id.get('value', '')
                        
                    if caller_id is not None and caller_id != "":
                        link_parts = caller_id['link'].split('/')
                        caller_id = link_parts[-1]
                        caller_id_details = get_user(request,session, caller_id)
                    else:
                        caller_id_details = "Admin"
                        
                    
                    gpt3_prompt += (
                    f"Incident Number: {incident_number},"
                    f"Opened By  : {caller_id_details}\n "
                    
                )
                gpt3_messages = [
                    {"role": "system", "content": "The user forgot the ticket number to query. As a helpful chatbot you will try or make a suggestion on all the ticket number and its corresponding ticket opener to the user "},
                    {"role": "user", "content": gpt3_prompt},
                ]

                chat_completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=gpt3_messages
                )

                message = chat_completion.choices[0].message.content.strip() 
                first_question = "yes"
                
            else:
                message = "Sorry I did not catch that, please try again"        
            #message ="Incident not found, please provide a valid and an existing incident ticket in this format INCXXXXXXX."
            response = {"message": message, "innerIntent": True, "intent": "CHECK_TICKET_NUMBER"}
            return JsonResponse(response)
    match = re.search(r'INC\d{7}', user_message.upper())
    if match:
        ticket_number = match.group()
        message = ticket_details(request, temp_id, ticket_number)
        first_question = "yes"
        #response = {"message": message, "innerIntent": True, "intent": "ticketdetailsflow"}
        return message
    elif re.search(r'\d+', user_message.upper()):
        message ="Incident not found, please provide a valid and an existing incident ticket in this format INCXXXXXXX."
        response = {"message": message, "innerIntent": True, "intent": "CHECK_TICKET_NUMBER"}
        first_question = "no"
        return JsonResponse(response)
         
    else:
        message = "To assist you promptly, please provide the incident number you want to retrieve: "
        response = {"message": message, "innerIntent": True, "intent": "CHECK_TICKET_NUMBER"}
        first_question = "no"
        return JsonResponse(response)
    

@csrf_exempt
def ticket_details(request, temp_id, ticket_number):

    details = []
    user, pwd = get_snow_creds(request)
    intent = workflow_instances[temp_id]['intent']

    try:
        data = json.loads(request.body)
        user_message = data.get('userMessage', '')

    except json.JSONDecodeError:
        response = {'reply': 'Invalid JSON data'}
        return JsonResponse(response, status=400)

    statement = generate_ai_response(user_message, "Analyze the intent of the user. Determine if it classifies as an ending statement of a conversation. Strictly answer yes or no without a period. \
                                                                  Refer to this: \
                                                                 \
                                                                  - Usual question before ending statements: 'Is there anything else you would like to inquire about regarding this ticket or any other concerns you may have?'. \
                                                                   - Sample ending statements:'exit', 'ok','I'm good', 'no questions', 'thanks', 'no', 'I think I'm good now', 'No, I don't have any more questions', 'Thanks, that's all I needed to know', 'No, I'm all set', 'I'm good, thank you', 'No more questions, thanks'. \
                                                                     ")
    print(f"is ending the statement:{statement}")
    if statement.lower() == 'yes':
        del workflow_instances[temp_id]
        exit_message = "Thank you for using SNAP.\n\n If you have any additional inquiries or require assistance, please feel free to ask."
        response = {"message": exit_message, "innerIntent": False, "intent": "ticketdetailsflow"}
        return JsonResponse(response)

    with requests.Session() as session:
        relevant_info = fetch_data_from_api(request, session)
        update_gpt3_prompt(relevant_info)
        gpt3_prompt = " "  #reset prompt
        params = {'sysparm_query': f'number={ticket_number}'}
        response = session.get(inc_table, params=params, auth=(user, pwd), headers=headers)
        data = response.json()
        

        if 'result' in data and isinstance(data['result'], list):
            for incident in data['result']:
                incident_number = incident.get('number', '')
                made_sla = incident.get('made_sla', '')
                caused_by = incident.get('caused_by', '')
                onhold_value = incident.get('hold_reason', '')
                resolved_at = incident.get('resolved_at', '')  
                resolution_notes = incident.get('comments', 'no resolution yet') 
                approval_history = incident.get('approval_history', '')
                sys_created_on = incident.get('sys_created_on', '')
                active = incident.get('active', '')
                short_description = incident.get('short_description', '')
                description = incident.get('description', '')
                state = incident.get('state', '')
                priority = incident.get('priority', '')
                assigned_to_value = ''
                assigned_to = incident.get('assigned_to')
                if assigned_to and isinstance(assigned_to, dict):
                    assigned_to_value = assigned_to.get('value', '')
                caller_id_value = ''
                caller_id = incident.get('caller_id')
                if caller_id and isinstance(caller_id, dict):
                    caller_id_value = caller_id.get('value', '')
                sla_due = incident.get(' sla_due', '')
                        
                # map_state_to_label function to convert the numeric state to a label
                state_label = map_state_to_label(int(state))
                #print(state_label)
                if state_label == 'On Hold':
                    hold_reason = map_hold_reason_to_label(int(onhold_value))
                else:
                    hold_reason = ''
                priority_label = map_priority_to_label(int(priority))
                # get_user function to get the first name of the assignee
                if assigned_to is not None and assigned_to != "":
                    link_parts = assigned_to['link'].split('/')
                    assigned_to = link_parts[-1]
                    assigned_to_details = get_user(request, session, assigned_to)
                else:
                    assigned_to_details = "not yet assigned to anyone"
                
                if caller_id is not None and caller_id != "":
                    link_parts = caller_id['link'].split('/')
                    caller_id = link_parts[-1]
                    caller_id_details = get_user(request, session,  caller_id)
                else:
                    caller_id_details = "Admin"
                
                
                #print(assigned_to_details)
                details.append({
                    'incident number': incident_number,
                    'state_label': state_label,
                    'resolved_at': resolved_at,
                    'resolution_notes': resolution_notes,
                    'assigned_to_details': assigned_to_details,
                    'hold_reason': hold_reason
                })
 
                gpt3_prompt += (
                    f"Incident Number: {incident_number}, "
                    f"Made SLA?: {made_sla}, "
                    f"Caused by: {caused_by}, "
                    f"Hold Reason: {hold_reason}, "
                    f"Hold Reason: { approval_history}, "
                    f"Creation Date: { sys_created_on}, "
                    f"active: {active}, \n"
                    f"Short Description: {short_description}, "
                    f"Description: {description}, "
                    f"Status: {state_label}, "
                    f"Priority: {priority_label}, "
                    f"SLA_Due: {sla_due}, "
                    f"Opened By  : {caller_id_details}, "
                    f"Assigned to : {assigned_to_details}\n"
                ) 
                
            while True:
                data = json.loads(request.body)
                user_question = data.get('userMessage', '')
                conversation_history.append({"role": "user", "content": user_question})
                
                    
                prompt_details = f""" 
                            You are a helpful chatbot that shares the short_description of the ticket and who it is assigned to.
                            Based your details form {gpt3_prompt}.
                            Then ask the user if they have other questions about the ticket.
                        """
                        
                gpt3_messages = [
                    {"role": "system", "content": prompt_details},
                    {"role": "user", "content": "give me the short description and assignee"},
                ] + conversation_history

                chat_completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=gpt3_messages
                )

                message = chat_completion.choices[0].message.content.strip()
                conversation_history.append({"role": "assistant", "content": message})
                
                response = {"message": message, "innerIntent": True, 
                        "intent": "ticketdetailsflow", 
                        "ticket_number": ticket_number
                    }
                
                user_intent = generate_ai_response(user_question, "Analyze the intent of the user. Choose if it classifies as follow-up, asking for ticket details, or others. Just reply ticket_details, ticket_followup, or others. \
                                                    Refer from this: \
                                                    \
                                                    - ticket_details: Give this intent if the user's message seems to be asking about details of a ticket or wants to know the details about a ticket. \
                                                    - ticket_followup: Give this intent if the user's message seems to refer to the process of checking on the status or progress of a support ticket or service request that has been submitted to a company or organization. \
                                                                    This could involve inquiring about seeking resolution, or confirming that the issue has been addressed satisfactorily. \
                                                    - others: If the user's message is not alligned with either ticket_details or ticket_followup.")

                print(f"user_intent: {user_intent}")
                    
                if user_intent.lower() == 'ticket_followup':
                    intent = 'ticketdetailsflow'
                    # intent = 'follow-up-flow'
                    response = get_status_updates(request, intent, ticket_number, user, pwd)
                    
                return JsonResponse(response)

        else:
            message = "I'm sorry, but I couldn't find any information for the ticket number you provided. \n\nPlease input an existing ticket number:"
            conversation_history.append({"role": "assistant", "content": message})
            response = {"message": message, "innerIntent": True}
            return JsonResponse(response)

        
        

# Do the HTTP request to ServiceNow API
def fetch_data_from_api(request, session): 
    
    inc_table=f"https://{instance}.service-now.com/api/now/table/incident"
    user, pwd = get_snow_creds(request)
    
    response = session.get(inc_table, auth=(user, pwd), headers=headers)
    response.raise_for_status()
    data_from_api = response.json()
    return data_from_api.get('result', [])

def map_state_to_label(state_value):
    state_mapping = {
        1: "New",
        2: "In Progress",
        3: "On Hold",
        6: "Resolved",
        7: "Closed",
        8: "Cancelled",
        # Add more mappings as needed
    }
    return state_mapping.get(state_value, f"Unknown State ({state_value})")

def map_priority_to_label(priority_value):
    priority_mapping = {
        1: "Critical",
        2: "High",
        3: "Moderate",
        4: "Low",
        5: "Planning",
    
    }
    return priority_mapping.get(priority_value, f"Unknown State ({priority_value})")


def get_user(request, session, user_id):
    
    user, pwd = get_snow_creds(request)
    
    params = {'sysparm_query': f'sys_id={user_id}'}
    response = session.get(sys_user_tbl, params=params, auth=(user, pwd), headers=headers)
    user_info = response.json().get('result', [])

    if user_info:
        user_details = user_info[0]  
        first_name = user_details.get('first_name', '')
        email = user_details.get('email', '')
        
        return f"Name: {first_name}, Email: {email}"

    return None

def get_sys_id(request, session):
    
    user, pwd = get_snow_creds(request)
    
    params = {'sysparm_query': f'user_name={user}'}
    response = session.get(sys_user_tbl, params=params, auth=(user, pwd), headers=headers)
    user_info = response.json().get('result', [])

    if user_info:
        user_details = user_info[0]  
        sys_id= user_details.get('sys_id', '')
        
        
        return sys_id

    return None


              

def update_gpt3_prompt(data_from_api):
    global gpt3_prompt
    
    gpt3_prompt = ""  # Reset the prompt

    for incident in data_from_api:
        incident_number = incident.get('number', '')
               
        gpt3_prompt += (
        f"Incident Number: {incident_number}\n"
                            )
    return gpt3_prompt



def clean_html(raw_html):
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator="\n")
    lines = text.splitlines()
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    cleaned_text = "\n".join(cleaned_lines)
    return cleaned_text

def get_snowkb():
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # Access knowledge base table
    kb_tbl = f"https://{instance}.service-now.com/api/now/table/kb_knowledge"
    user = os.getenv('SN_USER')
    pwd = os.getenv('SN_PWD')
    response = requests.get(kb_tbl, auth=(user, pwd), headers=headers)
    data = response.json()
    articles = []

    if 'result' in data and isinstance(data['result'], list):
        for item in data['result']:
            article = {
            "short_description": item["short_description"],
            "number": item["number"],
            "content": clean_html(item["text"])
        }
            articles.append(article)
    return articles


def fetch_power_bi_data(access_token):
    headers = {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json'
    }

    # Example endpoint to fetch datasets
    endpoint = 'https://api.powerbi.com/v1.0/myorg/datasets'

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        datasets = response.json()
        # Process datasets as needed
        return datasets
    else:
        # Handle error
        return None


def authenticate(request):
    # Redirect users to Azure AD for authentication
    azure_auth_url = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/authorize" \
                     f"?client_id={settings.AZURE_CLIENT_ID}" \
                     "&response_type=code" \
                     "&redirect_uri=http://localhost:8000/auth/callback" \
                     "&response_mode=query" \
                     "&scope=openid%20https://analysis.windows.net/powerbi/api/.default"  # Adjust scope as needed
    print(settings.AZURE_CLIENT_ID)
    return redirect(azure_auth_url)

def callback(request):
  # Handle callback from Azure AD
    auth_code = request.GET.get('code')
    token_endpoint = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}/oauth2/v2.0/token"
    token_payload = {
        'grant_type': 'authorization_code',
        'client_id': settings.AZURE_CLIENT_ID,
        'code': auth_code,
        'redirect_uri': 'http://localhost:8000/auth/callback',
        'client_secret': settings.AZURE_CLIENT_SECRET,
    }
    response = requests.post(token_endpoint, data=token_payload)
    if response.status_code == 200:
        # Access token obtained successfully, handle accordingly
        access_token = response.json()['access_token']
        # Store or use the access token as needed
        return ('tama')  # Redirect to home page or another view
    else:
        # Handle token retrieval failure
        return ('error')  # Redirect to an error page

def sharepoint_files(request):
    # Define SharePoint API endpoint
    sharepoint_url = "https://77soft0.sharepoint.com/_api/web/lists/getbytitle('Documents')/items"

    # Define headers with OAuth token
    headers = {
        "Authorization": f"Bearer {get_sharepoint_token()}",  # Function to retrieve OAuth token
        "Accept": "application/json;odata=verbose"
    }

    # Make GET request to SharePoint API
    response = requests.get(sharepoint_url, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        # Parse JSON response
        data = response.json()

        # Extract relevant information from response
        files = []
        for item in data['d']['results']:
            file_data = {
                'title': item['Title'],
                'url': item['FileRef']
            }
            files.append(file_data)

        # Render template with data
        return render(request, 'sharepoint_files.html', {'files': files})
    else:
        # Handle error - return error page or message
        return render(request, 'error.html', {'error_message': 'Failed to fetch SharePoint files'})


def get_sharepoint_token():
    # URL of the Azure Active Directory token endpoint
    token_endpoint = settings.AAD_TOKEN_ENDPOINT  # Update this with your AAD token endpoint URL

    # Parameters required for token request
    token_data = {
        'grant_type': 'client_credentials',
        'client_id': settings.CLIENT_ID,  # Update this with your application/client ID
        'client_secret': settings.CLIENT_SECRET,  # Update this with your application/client secret
        'resource': settings.SHAREPOINT_RESOURCE  # Update this with your SharePoint resource URL
    }

    try:
        # Make POST request to AAD token endpoint
        response = requests.post(token_endpoint, data=token_data)

        # Check if request was successful
        if response.status_code == 200:
            # Parse JSON response and extract access token
            token_json = response.json()
            access_token = token_json['access_token']
            return access_token
        else:
            # Handle error - return None or raise an exception
            return None
    except Exception as e:
        # Handle exception - return None or raise an exception
        return None



# Example usage
# tenant_id = 'd15d6348-bf2b-4e12-a6cb-39c223b9f3d2'
# client_id = 'b621b8d3-27cb-47b9-949c-bd83a00e9e35'
# client_secret = 'vHs8Q~Bii~1wNeiXq1J2gKzt1dUsuuEAB2lVCaEo'
# workspace_id = 'f3088e36-8405-4559-be92-4a0b17dc4427'

#new
tenant_id = 'd15d6348-bf2b-4e12-a6cb-39c223b9f3d2'
client_id = 'e01fe287-9a87-4593-a21e-5ab21a86e66f'
client_secret = 'xU88Q~O3_JspmBUIGcg5dxPM7lDg-B.ds9i0DcW1'
workspace_id = '0f320a9b-11db-4851-9e45-e5efe69e9d10'
username = 'jdato@77globalresources.com'
password = 'Makiboi04!'


def get_access_token(tenant_id, client_id, client_secret,username, password):
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
   
    token_data = {
        #'grant_type': 'client_credentials',
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'https://analysis.windows.net/powerbi/api/.default',
        'username': username,
        'password': password
 
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(token_url, data=token_data,headers=headers)
    if response.status_code == 200:
       
        access_token = response.json()['access_token']
        return access_token
   
    else:
        # Handle error
        print(response.status_code)
        print(response.content)
       
 
def get_datasets(access_token, workspace_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets",headers=headers)
    if response.status_code == 200:
        datasets = response.json().get('value', [])
        return datasets
    else:
        print(f"Failed to retrieve datasets. Status code: {response.status_code}")
        print("Error:", response.text)
        return None
 
def get_dataset_tables(access_token, dataset_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset_id}/tables", headers=headers)
    if response.status_code == 200:
        tables = [table['name'] for table in response.json().get('value', [])]
        return tables
    else:
        print(f"Failed to retrieve dataset tables. Status code: {response.status_code}")
        print("Error:", response.text)
        return None


access_token = get_access_token(tenant_id, client_id, client_secret,username, password)
# dataset_id = '800acfac-10d2-4c52-87ad-a0ba552ff636'
dataset_id = 'e2a6597e-30d6-456b-8d17-01f24ecbd18e'

def get_dashboards_in_group(access_token, workspace_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/dashboards", headers=headers)
    if response.status_code == 200:
        dashboards = response.json().get('value', [])
        return dashboards
    else:
        print(f"Failed to retrieve dashboards in group. Status code: {response.status_code}")
        print("Error:", response.text)
        return None

 
def get_reports_in_workspace(access_token, workspace_id):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports", headers=headers)
    if response.status_code == 200:
        return response.json().get('value', [])
    else:
        print(f"Failed to retrieve reports in workspace. Status code: {response.status_code}")
        return None

def extract_dataset_id_from_report(report):
    dataset_id = None
    if 'datasetId' in report:
        dataset_id = report['datasetId']
    return dataset_id

if access_token:
    reports = get_reports_in_workspace(access_token, workspace_id)
    if reports:
        dataset_ids = [extract_dataset_id_from_report(report) for report in reports]
        print("Dataset IDs in the workspace:")
        print(dataset_ids)
    else:
        print("Failed to retrieve reports in the workspace.")
else:
    print("Failed to obtain access token.")

# For ticket follow-up

def map_hold_reason_to_label(onhold_value):
    hold_reason_mapping = {
        1: "Awaiting Caller",
        2: "Awaiting Change",
        3: "Awaiting Problem",
        4: "Awaiting Vendor",

    }
    return hold_reason_mapping.get(onhold_value, f"Unknown State ({onhold_value})")

@csrf_exempt
def ticket_followup(request,temp_id, ticket_number):
    print(" Entered function for follow-up email intent")
    # user, pwd = get_snow_creds(request)
    intent = workflow_instances[temp_id]['intent']
    
    try:
        data = json.loads(request.body)
        user_message = data.get('userMessage', '')

    except json.JSONDecodeError:
        response = {'reply': 'Invalid JSON data'}
        return JsonResponse(response, status=400)

    

    if user_message.lower() == 'exit':
        del workflow_instances[temp_id]
        exit_message = exit_workflow_message(intent)
        response = {"message": exit_message, "innerIntent": False, "intent": "follow-up-flow"}
        return JsonResponse(response)

    elif user_message.lower() == 'yes':
        # message = generate_ai_response(ticket_number, "You are tasked to send a follow up email on the ticket given by the user. Ask the user what issue or concern she/he would like you to mention")
        print(ticket_number)
        message = f"""I'm here to assist you. You are requesting to send a follow up email for ticket {ticket_number}.\n
        Please input below a brief summary of the issue or concern you'd like me to mention when following up with the ticket assignee.
        
        [If you want to cancel, please type 'EXIT'.]
        """
        response = {"message": message, "innerIntent": True, "intent": "follow-up-flow", "ticket_number": ticket_number}
        return JsonResponse(response)

    response = {"message": "Follow up email has been sent", "innerIntent": False, "intent": "follow-up-flow"}
    return JsonResponse(response)
    
@csrf_exempt
def get_status_updates(request, intent, ticket_number, user, pwd):
    
    ### Retrieving status updates (status, resolution, work notes)
    
    session = requests.Session()
    details = []
    # journal_data = {}
    
    params = {'sysparm_query': f'number={ticket_number}'}
    ticket_response = session.get(inc_table, params=params, auth=(user, pwd), headers=headers)
    incident_data = ticket_response.json()
    
    if incident_data.get('result'):  # Check if the ticket exists in the database
        if 'result' in incident_data and isinstance(incident_data['result'], list):
            for incident in incident_data['result']:
                state = incident.get('state', '')
                incident_sys_id = incident.get('sys_id')
                state_label = map_state_to_label(int(state))
                onhold_value = incident.get('hold_reason', '')
                resolved_at = incident.get('resolved_at', "")
                resolution_notes = incident.get('close_notes', None)
                resolution_code = incident.get('close_code', None)   
                if state_label == 'On Hold':
                    hold_reason = map_hold_reason_to_label(int(onhold_value))
                else:
                    hold_reason = ''
                        
                assigned_to = incident.get('assigned_to')
                # get_user function to get the first name of the assignee
                if assigned_to is not None and assigned_to != "":
                    link_parts = assigned_to['link'].split('/')
                    assigned_to = link_parts[-1]
                    assigned_to_details = get_user(request, session, assigned_to)
                    # name = assigned_to_details.split(',')[0].split(': ')[1].strip()
                else:
                    assigned_to_details = "not yet assigned to anyone"
                    # name = ""
        
                # Check for resolution notes
                params = {'sysparm_query': f'number={ticket_number}'}
                reso_response = session.get(inc_table,params=params, auth=(user, pwd), headers=headers)
                resolution_data = reso_response.json()

                if 'result' in resolution_data and isinstance(resolution_data['result'], list):
                    for entry in resolution_data['result']:
                        resolution_notes = entry.get('close_notes', None)  
                        resolution_code = entry.get('close_code', None)  
                
                # Check for work notes
                #sys_journal table
                tbl = f"https://{instance}.service-now.com/api/now/table/sys_journal_field?element_id={incident_sys_id}&sysparm_query=ORDERBYDESCsys_created_on"
                jrn_response = session.get(tbl, auth=(user, pwd), headers=headers)
                journal_entries = jrn_response.json()
                # print(f" Journal: {journal_entries}")
                
        
            details.append({
            'state_label': state_label,
            'resolved_at': resolved_at,
            'Resolution_notes': resolution_notes,
            'Resolution_code': resolution_code,
            'assigned_to_details': assigned_to_details,
            'hold_reason': hold_reason,
            })

        prompt = ""            
        # print(details)
        
        prompt = f"""
                    You are a helpful chatbot that provides the status of the ticket and who is it assigned to.
                    Thank the user for waiting and introduce your findings.
                    Get the details from {details} and give them to the user in a bullet form.
                    
                    - If a key from {details[0]} is empty or none, skip it.
                    - Share all comments and work notes from {journal_entries} with author and date posted. If {journal_entries} is empty, tell the user.
                    
                    As an ending message, ask: "Would you like me to send a follow up email to the assignee or administrator?". 
                    
                    """              

        message = generate_ai_response("ticket status update", prompt)
        # get ending message based from ticket status
        # end_message = status_end_message(details,name)
        # message += f" \n\n {end_message}"
        response = {"message": message, 'innerIntent': True, "intent": intent, 'ticket_number': ticket_number, "header": "email_confirmation"}
        
            
    else:
        message = "I'm sorry, but I couldn't find any information for the ticket number you provided. \n\nPlease input an existing ticket number:"
        response = {"message": message, 'innerIntent': True, "intent": intent}
    
    return response

def confirm_send_email(request):
    pass

def generate_ai_response(user_message, gpt_prompt):
    # Use GPT-3 with the gpt-3.5-turbo-0613 engine to get a response

    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": gpt_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    gpt3_response = chat_completion.choices[0].message.content.strip()

    # Print the GPT-3 response
    message =  gpt3_response
    
    # return response
    return message