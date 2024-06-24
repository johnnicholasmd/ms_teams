import os
import psycopg2
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory

# for local data
from langchain.chains import ConversationalRetrievalChain
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import S3DirectoryLoader
from langchain.docstore.document import Document

import boto3
from dotenv import load_dotenv
load_dotenv()
import base64
from workflow_func.workflow import get_snowkb

# Fetch s3 credentials from rds
# PostgreSQL Database Connection
connection_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
sql_query = "select * from s3_bucket.s3_conn;"

with psycopg2.connect(connection_uri) as conn:
    with conn.cursor() as cursor:
        cursor.execute(sql_query)
        columns = [desc[0] for desc in cursor.description]
        res = [dict(zip(columns, row)) for row in cursor.fetchall()]
        res = res[0]

bucket_name = "alicia-chat-dev-png"
region_name = res["region_name"]
iam_user = res["iam_user"]
encoded_password = res["encoded_password"]
encoded_secret_key = res["encoded_secret_key"]
encoded_access_key = res["encoded_access_key"]

# Function to decode encoded credentials
def decode_credentials(encoded_credential):
    if encoded_credential.startswith("ENCODED:"):
        base64_encoded = encoded_credential.split(":", 1)[1]
        return base64.b64decode(base64_encoded).decode('utf-8')
    else:
        return None

# Save decoded credentials
decoded_password = decode_credentials(encoded_password)
decoded_secret_key = decode_credentials(encoded_secret_key)
decoded_access_key = decode_credentials(encoded_access_key)

# AWS S3 bucket connection
s3 = boto3.resource('s3', region_name=region_name, 
                    aws_access_key_id=decoded_access_key,
                    aws_secret_access_key=decoded_secret_key)
s3_client = boto3.client("s3")

# for nltk error catch
import nltk
nltk.download('punkt')
nltk.download('stopwords')

# OPENAI API Connection
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

knowledge_base = []

# Specify the root folder
root_folder_knowledge_base = 'knowledge_base'

# Helper function for getting all file names from S3 Bucket
def get_all_files(bucket_name, branch):
    bucket = s3.Bucket(bucket_name)
    files = [s3_obj.key for s3_obj in bucket.objects.all() if branch.lower().strip() in str(s3_obj.key)]
    return files

# Function for loading files from S3 Bucket
def load_files_from_s3(branch, documents_type):
    """Load documents from S3"""
    documents = documents_type
    file_names = get_all_files(bucket_name=bucket_name, branch=branch)

    for file in file_names:
        if file.endswith((".pdf", ".docx", ".doc", ".txt", ".csv")):
            loader = S3DirectoryLoader(bucket_name, file)
            documents.extend(loader.load())



# Loads files from S3 Bucket
load_files_from_s3(root_folder_knowledge_base, knowledge_base)


# Loads articles from snow
articles = get_snowkb()


# convert articles to Document instances and add to knowledge_base
for article in articles:
    knowledge_base.append(Document(page_content=article['content'], metadata={"source": "articles.txt", "short_description": article["short_description"], "number": article["number"]}))

# Ensure knowledge_base contains Document instances
for i, doc in enumerate(knowledge_base):
    if isinstance(doc, dict):
        knowledge_base[i] = Document(page_content=doc['content'], metadata={"source": doc.get('source', 'unknown')})
                
def final_vector(request):
    # To split and chunks the loaded documents into smaller token
    text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1200, chunk_overlap=100)

    # Split documents
    split_knowledge_base = text_splitter.split_documents(knowledge_base)

    embeddings = OpenAIEmbeddings()
    # For text searching
    
    vector = FAISS.from_documents(split_knowledge_base, embeddings)
    
    return vector

# # GPT Prompt
# prompt_template = """**I am SNAP (ServiceNow AI Partner) built by Seven Seven Corporate Group.** My knowledge comes solely from the documents you provide.

# **Here's how I work:**

# * I only understand and respond in English.
# * I strive to answer your questions accurately and concisely based on the provided documents.
# * If the answer isn't found in the documents, I'll honestly tell you: "I'm sorry, I don't have information about this topic in my knowledge base."
# * I won't provide examples unless you explicitly ask for them.
# * I can't answer general knowledge questions (math, science, etc.).
# * I can create tickets, retrieve ticket information, and count incident tickets from ServiceNow for you.
# * I can also answer questions related to common IT FAQs.
# * If you ask for help/assistance, I will answer "Sure, what do you want me to do?" and provide the things I can do.
# * If my response is long, I will break it into smaller, readable chunks for easier understanding.

# Documents:

# {context}

# Human: {question}

# ALiCIA: 
# """



print("Knowledge base and articles have been loaded and processed.")

class colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    END = '\033[0m'
    
connection_uri = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

def db_connect(table_name):
    sql_query = f"select * from {table_name};"

    with psycopg2.connect(connection_uri) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql_query)
            columns = [desc[0] for desc in cursor.description]
            res = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return res[0]  # Returning the first result row