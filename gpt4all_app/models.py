from django.db import models
from django.utils import timezone

# Create your models here.

class Chatlog(models.Model):
    id = models.CharField(primary_key=True)
    start_datetime = models.DateTimeField(default=timezone.now)
    duration = models.FloatField(default = 0)
    user_id = models.CharField()
    interaction_count = models.IntegerField(default = 0)
    user_typing_time = models.FloatField(default = 0)
    chatbot_inference_time = models.FloatField(default = 0)
    user_feedback = models.IntegerField(default = 0)
    escalation = models.IntegerField(default = 0)
    transcript = models.TextField(default = "")
    total_tokens = models.IntegerField(default = 0)
    prompt_tokens = models.IntegerField(default = 0)
    total_cost = models.FloatField(default = 0)

    # class Meta:
    #     managed = False
    #     db_table = 'chatlog_snow'
        
class ChatSession(models.Model):
    temp_id = models.CharField(max_length=125, unique=True)
    conversation_history = models.JSONField(default=list)

    # class Meta:
    #     managed = False
    #     db_table = 'chatsession_snow'