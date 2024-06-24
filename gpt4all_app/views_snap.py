import re, psycopg2, json, random, time, subprocess as st, sys, os, time
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib import messages

from langchain_community.callbacks import get_openai_callback
from dashboard_func.intent_classification import predict_intent

from gpt4all_app.views import *
from workflow_func.authentication import generate_jwt, decode_and_validate_token
import requests
import os

from django.http import JsonResponse
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from asgiref.sync import async_to_sync

adapter_settings = BotFrameworkAdapterSettings("12aeacc8-08e6-4549-ab53-ec47e2d3d1a6", "5ad96c7b-a059-451d-99e1-a5d9e9aa16da")
adapter = BotFrameworkAdapter(adapter_settings)


@csrf_exempt
def bot_messages(request):
    if request.method == "POST":
        body = json.loads(request.body)
        activity = Activity().deserialize(body)
        auth_header = request.headers.get("Authorization", "")

        async def turn_callback(turn_context: TurnContext):
            await turn_context.send_activity(f"You said: {turn_context.activity.text}")

        async def process_activity():
            await adapter.process_activity(activity, auth_header, turn_callback)

        async_to_sync(process_activity)()
        return JsonResponse({"status": "ok"})
    return JsonResponse({"error": "Invalid request method"}, status=405)


#Frontend Views
def chat(request, temp_id):
    if 'token' not in request.session:
        return redirect ('/login/')
    
    else:
        token = request.session['token']
        try:
            decode_token = decode_and_validate_token(token)
            # print(decode_token)
            name = decode_token['sub']
            return render(request, 'chat.html', {"temp_id": temp_id, "name": name})
            # return render(request, 'chat.html', {"temp_id": temp_id})
        except Exception as e:
            print(e)
            return redirect ('/login/')
        

@csrf_exempt
def generate_temp_id(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        authentication, user, pwd = authenticate_user(username, password)
        
        #if username == os.getenv('portal_user') and password == os.getenv('portal_password'):
        if authentication == True:
            # temp_id = str(uuid.uuid4())  # Use the first 6 characters of a UUID as the temporary ID
            
            name, temp_id  = user_info(username, password) # use sys_id as temp_id
            token = generate_jwt(name) # first_name
            user_token = generate_jwt(user)
            pwd_token = generate_jwt(pwd)  
            request.session['token'] = token
            request.session['user_token'] = user_token
            request.session['pwd_token'] = pwd_token 
            
            return redirect(f'/{temp_id}')
        else:
            messages.error(request, 'Invalid username or password.')
            #return render(request, 'loginarn.html', {'login_messages': messages})
        
    
    return render(request, 'login.html', {'login_messages': messages.get_messages(request)})


def authenticate_user(username, password):
    # Set up request headers
    headers = {"Content-Type":"application/json","Accept":"application/json"}
    
    # Access user table
    sys_user_tbl=f"https://{instance}.service-now.com/api/now/table/sys_user"
    
    user = username
    pwd = password
    
    # Send authentication request
    auth_response = requests.get(sys_user_tbl, auth=(user, pwd), headers=headers)

    # Check response status
    if auth_response.status_code == 200:
        # Authentication successful
        print("Authentication successful")
            # os.environ["USER"] = user
            # os.environ["PWD"] = pwd
            # with open(".env", "w") as f:
            #     for key, value in os.environ.items():
            #         f.write(f"{key}={value}\n")
            # load_dotenv(find_dotenv())
        return True, user, pwd
        
        
    else:
        # Authentication failed
        print("Authentication failed")
        return False, None, None

def user_info(username, password):
    sys_user_tbl=f"https://{instance}.service-now.com/api/now/table/sys_user"
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
    # username = os.getenv('USER')
    # password = os.getenv('PWD')
    
    
    params = {
    'sysparm_query': f"user_name={username}",
    'sysparm_fields': 'first_name, sys_id',
}
    response = requests.get(sys_user_tbl, auth=(username, password), headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        # print(data)
        if 'result' in data and len(data['result']) > 0:
        # Extract the first name and sys_id from the response
            first_name = data['result'][0]['first_name']
            sys_id = data['result'][0]['sys_id']
            return first_name, sys_id
        else:
            print("User not found.")
    else:
        print("Failed to retrieve user information.")

#Display Chatbot Response to UI
@csrf_exempt
def final_ai_response(request, temp_id):
    if request.method == "GET":
        return redirect('/login/')
    
    if '_refreshed' in request.session:
        chatlog_id = request.session['id']
        chatlog_last_logged_time = request.session['last_logged_time']
        request.session['_refreshed'] = True
        request.session['id'] = chatlog_id
        request.session['last_logged_time'] = chatlog_last_logged_time
    else:
        request.session['_refreshed'] = False

    # get intent dictionary from db
    intent_dict = get_intent_dict(connection_uri)

    #processes for chat logs
    id = request.session['id']
    datetime_now = dt.now().astimezone(tz=None)
    lapsed_time = datetime_now - date_parser.parse(request.session["last_logged_time"])
    request.session["last_logged_time"] = datetime_now.isoformat()

    log = Chatlog.objects.get(id=id)
    log.start_datetime = log.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz=None)
    log.duration += lapsed_time.total_seconds()
    log.user_typing_time += lapsed_time.total_seconds()
    log.interaction_count += 1
    
    try:
        data = json.loads(request.body)
        user_message = data.get('userMessage', '')
        log.transcript += "\n\nUser: {}".format(user_message)
        
    except json.JSONDecodeError:
        response = {'reply': 'Invalid JSON data'}
        return JsonResponse(response, status=400)
    
    # Retrieve or initialize conversation history from the database using Temp ID
    chat_session, created = ChatSession.objects.get_or_create(temp_id=temp_id)
    chat_history = chat_session.conversation_history if not created else []
    
    # Check if the session variable indicating a page refresh is present
    is_page_refreshed = request.session.pop('_page_refreshed', False)

    # Retrieve or initialize conversation history from the session
    chat_history = request.session.get('chat_history', [])
    
    # log.transcript += "\n\nUser: {}".format(user_message)
    intent = predict_intent(user_message)
    
    
    # Alternative for intent prediction
    # prompt = f""" You are a bot that can classify intents based from the user's message. You will give the intent in one word.
                  
    #             Choose from the following:
    #                 - create_ticket: Give this intent if the user's message seems to be requesting for you to create a ticket for him/her.
    #                 - greeting: Give this intent if the user's message seems to be a greeting
    #                 - count_ticket: Give this intent if the user's message seems to be requesting for you to count his/her ticket or wants to know how many tickets she/he has.
    #                 - ticket_details: Give this intent if the user's message seems to be asking about details of a ticket or wants to know the details about a ticket.
    #                 - acknowledgement: Give this intent if the user's message seems to validate your input, express gratitude, or signal that further action will be taken.
    #                 - ticket_followup: Give this intent if the user's message seems to refer to the process of checking on the status or progress of a support ticket or service request that has been submitted to a company or organization. 
    #                     This could involve inquiring about seeking resolution, or confirming that the issue has been addressed satisfactorily. 
    #                 - others: Give this intent if the user's message did not match with any of the intents listed above.
                    
    #         """
    # intent = generate_ai_response(user_message, prompt)

    with get_openai_callback() as cb:
        issue = ""
        print(f'intent: {intent}')
        # exit_word = "exit"
        if intent in intent_dict.keys():

            print(intent, intent_dict[intent])
            if intent == "others":
                response = eval(intent_dict[intent])
                # print(f" itooo, {response}")
                target_response = re.compile(r"I\'m sorry, I don\'t have information about this topic in my knowledge base\.", re.IGNORECASE)
                if target_response.search(response):
                    intent = 'create_ticket'
                    issue = user_message
                    workflow_instances[temp_id] = {"intent": intent}
                    response = {
                    "message" : f"I'm sorry, but I don't have information about this topic in my knowledge base. \n\n However, I can assist you in creating a new ticket for our team to address. \n\n What would you prefer to do?",
                    "innerIntent": False,
                    "intent" : intent.upper(),
                    "user_input": issue,
                    "real_intent" : intent.replace('_',' '),}
            else:
                response = eval(intent_dict[intent])
          
            print(cb)
            log.total_tokens += cb.total_tokens 
            log.prompt_tokens += cb.prompt_tokens
            log.total_cost += cb.total_cost 

        elif intent == 'create_ticket': 
                
                # intent = "clearance"
                # request.session['intent'] = intent
                workflow_instances[temp_id] = {"intent": intent}

                response = {
                    "message" : f"It seems you are asking about Ticket Creation. What do you want to do?",
                    "innerIntent": False,
                    "intent" : intent.upper(),
                    "user_input": "create ticket intent",
                    "real_intent" : intent.replace('_',' '),}
                
        elif intent == 'ticket_followup':
            
                ### For ticket follow ups
            
                workflow_instances[temp_id] = {"intent": intent}
                
                response = {
                    "message" : "It appears you're following up on a ticket. I'm on it! Let me check the status for you. ",
                    "innerIntent": False,
                    "intent" :  intent.upper(),
                    "real_intent" : intent.replace('_',' '),
                    "user_input": user_message,}
                
        elif intent == 'ticket_details': 
                # intent = "clearance"
                # request.session['intent'] = intent
                workflow_instances[temp_id] = {"intent": intent}

                # acr_dict = {
                #     "coe":"Certificate of Employment"
                # }
                # #old
                # response = {
                #     "message" : f"It seems you are asking about {acr_dict[intent]} ({intent.upper()}). What do you want to do?",
                #     "innerIntent": False,
                #     "intent" : intent,
                # }

                #proposal
                response = {
                    "message" : "I am accessing the records now. This will just take a few seconds.",
                    "innerIntent": False,
                    "intent" : intent.upper(),
                    "real_intent" : intent.replace('_',' '),
                    "user_input":user_message, }
                
        elif intent == 'count_ticket': 
                # intent = "clearance"
                # request.session['intent'] = intent
                workflow_instances[temp_id] = {"intent": intent}

                # acr_dict = {
                #     "coe":"Certificate of Employment"
                # }
                # #old
                # response = {
                #     "message" : f"It seems you are asking about {acr_dict[intent]} ({intent.upper()}). What do you want to do?",
                #     "innerIntent": False,
                #     "intent" : intent,
                # }

                #proposal
                response = {
                    "message" : "Got it! Let me check it for you.",
                    "innerIntent": False,
                    "intent" :  intent.upper(),
                    "real_intent" : intent.replace('_',' '),
                    "user_input":user_message,}
                
        
                
        elif intent == 'acknowledgement': 
            gpt3_prompt = " "
            gpt3_prompt += (
                    f"User Message: {user_message}\n"
                )
            
            gpt3_messages = [
                    {"role": "system", "content": "Create a short acknowledgement response based on the user input. "},
                    {"role": "user", "content": gpt3_prompt},
                ]

            chat_completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=gpt3_messages
                )

            message = chat_completion.choices[0].message.content.strip()
            if ":"  in message:
                message = message.split(':', 1)[1]
            else:
                message = message
               
            response = {
                    "message" :  message,
                    "innerIntent": False,
                    "intent" :  intent.upper(),
                    "real_intent" : intent.replace('_',' '),}
            
        elif intent == 'ticket_number':
            
                workflow_instances[temp_id] = {"intent": intent}
                
                response = {
                    "message" : "Do you want to make a follow up on the ticket or do you want to know the details of the ticket? ",
                    "innerIntent": False,
                    "intent" :  intent.upper(),
                    "real_intent" : intent.replace('_',' '),
                    "user_input": user_message,}
         
        else:
                # intent = "clearance"
                # request.session['intent'] = intent
                #print('pumasok sa else')
                workflow_instances[temp_id] = {"intent": intent}

                #proposal
                response = {
                    "message" : "If you have any additional inquiries or require assistance, please feel free to ask.",
                    "innerIntent": False,
                    "intent" :  intent.upper(),
                    "real_intent" : intent.replace('_',' '),}

    # Add the assistant's reply to the conversation history
    chat_history.append({"user": user_message, "content": response})

    # Update the conversation history in the session
    request.session['chat_history'] = chat_history
    chat_session.conversation_history.append(chat_history)
    chat_session.save()
    # Set the session variable to indicate a page refresh
    request.session['_page_refreshed'] = True if not is_page_refreshed else is_page_refreshed
    print("page_refreshed: ", request.session["_page_refreshed"])
    print('*'*100)
    # Print the conversation history with user and content separately
    for entry in chat_history:
        print(f"User: {entry['user']}")
        print(f"ALiCIA: {entry['content']}")
    
    # update chatlog record
    datetime_now = dt.now().astimezone(tz=None)
    lapsed_time = datetime_now - date_parser.parse(request.session["last_logged_time"])
    request.session["last_logged_time"] = datetime_now.isoformat()
    log.duration += lapsed_time.total_seconds()
    log.chatbot_inference_time += lapsed_time.total_seconds()
    
    if intent == "others":
        # log.transcript += "\n\nChatbot: {}".format(response)
        # log.save()
       
        # if response is "I'm sorry, I don't have information about this topic in my knowledge base.", save to file of unknown questions
        # if response == "I'm sorry, I don't have information about this topic in my knowledge base.":
        #     with open("./dashboard_files/unanswered_questions.txt", "a") as file:  
        #         file.write(user_message + "\n") 
        return HttpResponse(response.replace('\n', '<br>'))
        # return HttpResponse(response)
    
    else:
        transcript_response = response["message"]
        log.transcript += "\n\nChatbot: {}".format(transcript_response) 
        log.save()
        return JsonResponse(response)

