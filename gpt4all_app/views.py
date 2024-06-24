import re, psycopg2, json, random, time, subprocess as st, sys, os, time
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib import messages

from langchain_community.callbacks import get_openai_callback
from dashboard_func.intent_classification import predict_intent

from workflow_func.workflow import  *
from workflow_func.openai_model import model_response, model_chain
from workflow_func.authentication import generate_jwt, decode_and_validate_token
import requests
import os

# from django.utils import timezone
from .forms import DateFilterForm
from .models import ChatSession, Chatlog

from dotenv import load_dotenv, find_dotenv
from datetime import timedelta, timezone, datetime as dt
from dateutil import parser as date_parser

#for online offline status
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

#imports for Chatlog
import datetime
import uuid
import pandas as pd

#for api directory
api_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
api_directory = os.path.join(api_parent, 'api')
sys.path.append(api_directory)

#OPENAI API Connection
load_dotenv()

#PostgreSQL Database Connection
connection_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
def get_intent_dict(connection_uri):
    sql_query = f"SELECT * FROM general_flow.fixed_intents;" 
    with psycopg2.connect(connection_uri) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]  # Get column headers
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            # intent_list = [item['intent'] for item in results]

            unique_intents = [i['intent'] for i in results]
            unique_responses = [i['response'] for i in results]

            intent_dict = dict(zip(unique_intents, unique_responses))

    return intent_dict

qa_instances = {}


# Load chat history from json file
def chunk_chat_history(chat_history):
    chunked_chat_history = chat_history
    if len(chat_history) >= 100:
        in_length = len(chat_history) - 50
        chunked_chat_history = chat_history[in_length:len(chat_history)]
        
    return chunked_chat_history


def load_conversation():
    chat_history = []
    if os.path.exists("chat_history.json"):
        saved_history = json.load(open("chat_history.json", encoding='utf-8'))
        
        for i in range(len(saved_history)):
            chat_history.append((saved_history[i]['user'], saved_history[i]['bot']))

        chat_history = chunk_chat_history(chat_history)
    else:
        chat_history = []

    return chat_history


#Query all tables in DB public schema
def get_all_tables():
    with psycopg2.connect(connection_uri) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'gpt_data';")
            tables = cursor.fetchall()
    return [table[0] for table in tables]


#User Input Processing
def transform_sentence(input_sentence):
    patterns = {
        r'[^\w\s]': ''
    }

    for pattern, replacement in patterns.items():
        input_sentence = re.sub(re.compile(pattern, re.IGNORECASE), replacement, input_sentence)

    return input_sentence


#Chatbot Q&A response
@csrf_exempt
def q_and_a(request,input_message, temp_id):
    print(input_message)
    request.session['temp_id'] = temp_id
    data = json.loads(request.body)
    input_message = data.get('userMessage', '')
    user_message = transform_sentence(input_message)
    # Retrieve or initialize conversation history from the database using Temp ID
    chat_session, created = ChatSession.objects.get_or_create(temp_id=temp_id)
    chat_history = chat_session.conversation_history if not created else []
    response = model_response(request, user_message, chat_history, model_chain(request,temp_id))
    print(response)
    return HttpResponse(response.replace('\n', '<br>'))

@csrf_exempt
def q_and_a_kb(request, input_message, temp_id):
    user_message = transform_sentence(input_message)
    request.session['temp_id'] = temp_id
    # Retrieve or initialize conversation history from the database using Temp ID
    chat_session, created = ChatSession.objects.get_or_create(temp_id=temp_id)
    chat_history = chat_session.conversation_history if not created else []
    response = model_response(request, user_message, chat_history, model_chain(request, temp_id))
    return response
    
            
# Function to insert data into the database
def insert_to_database(user_message, response, start_time, connection_uri, cb):
    end_time = time.time()
    inference_time = end_time - start_time
    
    total_tokens = cb.total_tokens if cb.total_tokens is not None else 0
    prompt_tokens = cb.prompt_tokens if cb.prompt_tokens is not None else 0
    total_cost_usd = cb.total_cost if cb.total_cost is not None else 0
    
    sql_query = "INSERT INTO public.gpt4all_app_Chatlog (user_message, ai_response, inference_time, total_tokens, prompt_tokens, total_cost_usd) VALUES (%s, %s, %s, %s, %s, %s);"
    sql_params = [user_message, response, inference_time, total_tokens, prompt_tokens, total_cost_usd]
    
    with psycopg2.connect(connection_uri) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query, sql_params)


#Function to create log (if chatbox was opened: create log)
@csrf_exempt
def chatbot_display(request, temp_id):
    start_time = time.time()
    try:
        temp_token = request.session['token']
    except:
        temp_token = ''
        
    if request.method == "GET":
        return redirect('/login/')

    elif request.method == 'POST':

        #try to delete the instance of workflow when user reloads the browser at the middle of workflow filing
        if temp_id in workflow_instances:
            del workflow_instances[temp_id]

        data = json.loads(request.body)
        chatbotDisplay = data.get('chatbotDisplay', '')

        empName = data.get('empName', 'Juan de la Cruz')
        empEmail = data.get('empEmail', 'juan.cho345677@gmail.com')
        emp_ID = data.get('empID', 'XX-XXXX')
        empType = data.get('empType', 'PH')
        job_title = data.get('jobTitle', 'Dummy_jobtitle')
        project_dept =  data.get('projectDept', 'Dummy_proj_dept')
        dept = data.get('dept', 'dummy_dep')
        manager_name = data.get('managerName', 'dummy_man_name')
        manager_email =  data.get('managerEmail', 'defaultmanagerdm@gmail.com')
        token = data.get('token', temp_token)
        # US EMPLOYEE
        # emp_type = data.get("EngagementType__c", "W2-FTE")
        # PH EMPLOYEE
        emp_type = data.get("EngagementType__c", "")
        

        # if not (empName and empEmail and emp_ID and job_title and project_dept and dept and manager_email and manager_name):
        #     return HttpResponse("Fail")

        # user_id = request.user

        if chatbotDisplay == 1:
            try:
                decode_token = decode_and_validate_token(token)
            except Exception as e:
                print(e)
                return HttpResponse('Fail')
            id = temp_id

            # generate new unique id if it already exists
            while Chatlog.objects.filter(id = id).exists():
                id = uuid.uuid4()
            # print('id here')
            request.session['id'] = str(id)
            request.session['empName'] = str(empName)
            request.session['empEmail'] = str(empEmail)
            request.session['emp_ID'] = str(emp_ID)
            request.session['empType'] = str(empType)
            request.session['job_title'] = str(job_title)
            request.session['project_dept'] = str(project_dept)
            request.session['dept'] = str(dept)
            request.session['manager_name'] = str(manager_name)
            request.session['manager_email'] = str(manager_email)
            # emp type
            request.session['empType'] = str(emp_type)
            

            start_datetime = dt.now().astimezone(tz=None)
            transcript= "Start datetime: {}\n".format(start_datetime.strftime("%d %b %Y %H:%M:%S %Z"))
            
            log = Chatlog(id = request.session['id'], user_id=request.session['emp_ID'], transcript=transcript, start_datetime=start_datetime)
            log.save()
            print("done saving initial row with id", id)

            request.session["last_logged_time"] = start_datetime.isoformat()

            stop_time = time.time()
            print(f"Chatlog creation: {stop_time - start_time}s")

        else:
            id = request.session['id']
            datetime_now = dt.now().astimezone(tz=None)
            lapsed_time = datetime_now - date_parser.parse(request.session["last_logged_time"])

            log = Chatlog.objects.get(id=id)
            log.duration += lapsed_time.total_seconds()
            log.transcript += "\n\nEND OF CONVERSATION\n\n\nEnd datetime: {}".format(datetime_now.strftime("%d %b %Y, %H:%M:%S %Z"))
            log.start_datetime = log.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz=None)
            log.save()

            return render(request, "chat.html")

        return HttpResponse('success')

    return HttpResponse('Fail')


#Function to create log (if chatbox was opened: create log)
@csrf_exempt
def idle_response(request, temp_id):
    print("triggered idle_response view")
    if request.method == 'POST':
        data = json.loads(request.body)
        idle_response = data.get('idle_response', '')
        print("idle response:",idle_response)
        
        id = request.session['id']
        print("querying for this id:", id)

        log = Chatlog.objects.get(id=id)
        log.transcript += "\n\nChatbot: {}".format(idle_response)
        log.start_datetime = log.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz=None)
        log.save()

        return HttpResponse('success')

    return HttpResponse('Fail')

@csrf_exempt
def process_feedback(request, temp_id):
    print("triggered process_feedback view")
    if request.method == "POST":
        data = json.loads(request.body)
        user_feedback = data.get('feedbackInputs', '')
        print("user_feedback: ", user_feedback)

        id = request.session['id']
        log = Chatlog.objects.get(id=id)
        log.user_feedback = user_feedback
        log.start_datetime = log.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz=None)
        log.save()
        print("feedback saved")

        return HttpResponse('success')

    return HttpResponse('Fail')

#function for handling live agent interactions
def live_agent(request, temp_id):
    """
    @chris @ember - live_agent function
    """
    process_end_flag = False #flag for FE, continue using this function for responses

    id = request.session['id']
    log = Chatlog.objects.get(id=id)
    log.escalation = 1
    log.start_datetime = log.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz=None)
    # log.start_datetime = log.start_datetime.astimezone()
    # log.start_datetime = timezone.make_aware(log.start_datetime, timezone.get_current_timezone(), True)
    log.save()
    response = "- - - PROCESS FOR LIVE AGENT CONNECTION - - -"

    process_end_flag = True #flag for FE, switch to /ai-response/<str:temp_id>/ for responses

    return HttpResponse(response.replace('\n', '<br>'))


@csrf_exempt
def login(request):
    if request.method == "GET":
        return render (request, "login.html")
    
load_dotenv(find_dotenv())
instance = os.getenv('INSTANCE')