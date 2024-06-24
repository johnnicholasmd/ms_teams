"""
URL configuration for gpt4all_chatbot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from . import views, views_snap



urlpatterns = [
    path('', views_snap.generate_temp_id, name='generate_id'),
    path('login/', views.login, name='login'),
    path('<str:temp_id>/', views_snap.chat, name='chat_with_temp_id'),
    path('ai-response/<str:temp_id>/', views_snap.final_ai_response, name='ai_response'),
    path('chatbot_display/<str:temp_id>/', views.chatbot_display, name='chatbot_display'),
    path('idle_response/<str:temp_id>/', views.idle_response, name='idle_response'),
    path('get_feedback/<str:temp_id>/', views.process_feedback, name="process_feedback"),
    # path('get_chatbox_status/', views.get_chatbox_status, name='get_chatbox_status'),
    path('live_agent/<str:temp_id>/', views.live_agent, name='live_agent'),
    path('create_ticket/<str:temp_id>/', views.create_ticket, name='create_ticket'),
    path('ticket_details/<str:temp_id>/<str:ticket_number>/', views.ticket_details, name='ticket_details'),
    path('ticket_followup/<str:temp_id>/', views_snap.ticket_followup, name='ticket_followup'),
    path('ticket_followup/<str:temp_id>/<str:ticket_number>', views_snap.ticket_followup, name='ticket_followup'),
    path('check_ticket_number/<str:temp_id>/', views.check_ticket_number, name='check_ticket_number'),
    path('ticket_count/<str:temp_id>/', views.ticket_count, name='ticket_count'),
    path('q_and_a/<str:temp_id>/<str:input_message>/', views.q_and_a, name='q_and_a'),
    path('api/messages', views_snap.bot_messages, name='bot_messages'),
]

#  path('ticket_details/<str:temp_id>/<str:ticket_number>/', views.ticket_details, name='ticket_details'),