import pandas as pd
import joblib
import re
import json
from spellchecker import SpellChecker
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet
nltk.download('stopwords')
nltk.download('wordnet')
import os
import psycopg2
import boto3
from io import BytesIO
from dotenv import load_dotenv
import base64

load_dotenv()

connection_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
# sql_query = f"SELECT * FROM s3_bucket.s3_conn;"
sql_query = "select * from s3_bucket.s3_conn;"  

with psycopg2.connect(connection_uri) as conn:
    with conn.cursor() as cursor:
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]  # Get column headers
        new_results = [dict(zip(columns, row)) for row in cursor.fetchall()]

s3_creds = new_results[0]

encoded_secret_key = s3_creds["encoded_secret_key"]
encoded_access_key = s3_creds["encoded_access_key"]

#Function to decode encoded credentials
def decode_credentials(encoded_credential):
    if encoded_credential.startswith("ENCODED:"):
        base64_encoded = encoded_credential.split(":", 1)[1]
        return base64.b64decode(base64_encoded).decode('utf-8')
    else:
        return None

decoded_secret_key = decode_credentials(encoded_secret_key)
decoded_access_key = decode_credentials(encoded_access_key)


s3_client = boto3.client('s3')

s3 = boto3.resource(
    service_name='s3',
    region_name='ap-southeast-1',
    aws_access_key_id=decoded_access_key,
    aws_secret_access_key=decoded_secret_key
)

bucket_name = "alicia-chat-dev-png"
bucket = s3.Bucket(bucket_name)


# load objects for functions
obj = bucket.Object('intent_classification/intent_classification_config.json')
body = obj.get()['Body'].read().decode()
intent_classification_config = json.loads(body)

# list of intents
intents = intent_classification_config["intents"]
binary = intent_classification_config["binary"]
threshold = intent_classification_config["threshold"]
stopword_removal = intent_classification_config["stopword_removal"]
lemmatize = intent_classification_config["lemmatize"]
spellcheck = intent_classification_config["spellcheck"]
# print("Intent classification prediction binary?:", binary)

#checking for keywords to override classification
# load objects for functions
obj = bucket.Object('intent_classification/keywords.json')
body = obj.get()['Body'].read().decode()
keywords = json.loads(body)

if binary:
    files = dict()

    for intent in intents:

        with BytesIO() as data:
            s3.Bucket(bucket_name).download_fileobj(intent_classification_config[intent + "_vectorizer"], data)
            data.seek(0)    # move back to the beginning after writing
            files[intent + "_vectorizer"] = joblib.load(data)

            s3.Bucket(bucket_name).download_fileobj(intent_classification_config[intent + "_model"], data)
            data.seek(0)    # move back to the beginning after writing
            files[intent + "_model"] = joblib.load(data)


else:

    with BytesIO() as data:
        s3.Bucket(bucket_name).download_fileobj(intent_classification_config["multiclass_model"], data)
        data.seek(0)    # move back to the beginning after writing
        multiclass_model = joblib.load(data)

        s3.Bucket(bucket_name).download_fileobj(intent_classification_config["multiclass_vectorizer"], data)
        data.seek(0)    # move back to the beginning after writing
        multiclass_vectorizer = joblib.load(data)

#load objects for preprocessing
stopwords_eng = set(stopwords.words('english'))
negation_set = {'no', 'nor', 'not', 't', 'can', "don't", 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn',"mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"}
stopwords_eng = stopwords_eng - negation_set


def get_wordnet_pos(word):
    """Map POS tag to first character lemmatize() accepts"""
    try:
        tag = nltk.pos_tag([word])[0][1][0].upper()
        tag_dict = {"J": wordnet.ADJ,
                    "N": wordnet.NOUN,
                    "V": wordnet.VERB,
                    "R": wordnet.ADV}

        return tag_dict.get(tag, wordnet.NOUN)
    except:
        # print(type(word))
        return wordnet.NOUN


def preprocess_text(text):
    """
    Time in seconds for each step:
    {'cleaning': 0.12903165817260742, 'spelling': 117.63137936592102, 'stopwords': 0.0, 'lemmatization': 0.6576428413391113}
    """

    #to remove punctuations only
    text = text.lower()
    text = re.sub('[!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~]+', '', text)
    
    #to remove punctuations and special characters (other languages)
    text = re.sub(r'[^\w\s]+', '', text) 

    word_tokens = word_tokenize(text)

    #correct misspelled (english)   
    if spellcheck: 
        spell = SpellChecker()
        misspelled = spell.unknown(word_tokens)
        word_tokens = [w if w not in misspelled else spell.correction(w) for w in word_tokens]

    #removing stopwords
    if stopword_removal:
        word_tokens = [w for w in word_tokens if not w in stopwords_eng]

    #lemmatization
    if lemmatize:
        lemmatizer = WordNetLemmatizer()
        word_tokens = [lemmatizer.lemmatize(w, get_wordnet_pos(w)) if w is not None else "" for w in word_tokens]

    clean_text = ' '.join(word_tokens)
    return clean_text


def predict_intent(text):

    #CHECK FOR KEYWORDS FIRST
    text = text.lower()

    for i in range(len(keywords)):
        current_keyword_dict = keywords[str(i)]
        current_keyword_intent = list(current_keyword_dict.keys())[0]
        current_keyword_list = current_keyword_dict[current_keyword_intent]

        for keyword in current_keyword_list:
            pattern = "^"+keyword+"[^a-z]|[^a-z]"+keyword+"$|[^a-z]"+keyword+"[^a-z]|" + keyword
            if bool(re.search(pattern, text)):
                print("keyword used")
                return current_keyword_intent


    #INTENT CLASSIFICATION IF NO KEYWORDS FOUND

    text = preprocess_text(text)

    if binary:

        prediction_probabilites = dict()

        for intent in intents: 

            vectorizer = files[intent + "_vectorizer"]
            model = files[intent + "_model"]

            x_values_list = vectorizer.transform([text]).toarray()
            x_ = pd.DataFrame(x_values_list,columns = vectorizer.get_feature_names_out())
            prediction_probabilites[intent] = round(model.predict_proba(x_)[0][1], 4)

        print("prediction probabilities:", prediction_probabilites)

        #check for multiple maximums
        mx = max(prediction_probabilites.values())
        max_intent = [intent for intent, probability in prediction_probabilites.items() if probability == mx]

        if (len(max_intent) != 1) or (mx <= threshold):
            return "others"
        else:
            # single words keep getting assigned to coe (bandaid soln before model fix)
            if (max_intent[0] == "coe") and (len(text.split())==1) and (text!="coe"):
                return "others"
            else:
                return max_intent[0]
            
    else:
        x_values_list = multiclass_vectorizer.transform([text]).toarray()
        x_ = pd.DataFrame(x_values_list,columns = multiclass_vectorizer.get_feature_names_out())
        prediction = multiclass_model.predict(x_)
        # print("prediction probabilities:", multiclass_model.predict_proba(x_))
        return prediction[0]



