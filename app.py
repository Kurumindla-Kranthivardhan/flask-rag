import os
from flask import Flask, request, render_template_string
import requests
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv
load_dotenv()
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)

# -----------------------------
# Load configuration from ENV
# -----------------------------
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-35-turbo")
OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

# Initialize OpenAI client
client = AzureOpenAI(
    api_version=OPENAI_API_VERSION,
    azure_endpoint=OPENAI_ENDPOINT,
    api_key=OPENAI_KEY,
)

# -----------------------------
# Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def home():
    answer = None
    question = None

    if request.method == "POST":
        question = request.form.get("question")

        if question:
            # --- Step 1: Retrieve documents from Azure Search ---
            search_client = SearchClient(
                endpoint=SEARCH_ENDPOINT,
                index_name=SEARCH_INDEX,
                credential=AzureKeyCredential(SEARCH_KEY)
            )

            # -----------------------------
            # Example query
            # -----------------------------
            # query = "What was the root cause of the incident?"

            # Retrieve top 5 documents
            search_results = search_client.search(
                search_text=question,
                top=5,
                select=["title", "chunk"]  # adjust based on your index fields
            )

            # Format sources for RAG
            sources_formatted = "=================\n".join(
                [f'TITLE: {doc["title"]}, CONTENT: {doc["chunk"]}'
                for doc in search_results]
            )

            print("Formatted sources:\n", sources_formatted)

            # --- Step 2: Build prompt ---
            prompt = f"""
            Role: You are a cybersecurity AI assistant responsible for supporting incident investigations.  
            Responsibilities: Review and analyze the provided documents to extract relevant information, identify potential security issues, and answer the user’s questions based on the available evidence. If the documents do not contain the required information, clearly state "I don't know."
            {sources_formatted}
            Answer:
            """

            # --- Step 3: Call Azure OpenAI ---
            resp = client.chat.completions.create(
                model=OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content":"Question: {question}" },
                ],
                max_tokens=400,
                temperature=0.2,
            )
            answer = resp.choices[0].message.content

    # Render the form + answer (if available)
    return render_template_string(
        """
        <h2>Ask a Question (RAG + Azure Search)</h2>
        <form method="post">
            <input type="text" name="question" placeholder="Enter your question" size="50">
            <input type="submit" value="Ask">
        </form>

        {% if question %}
            <h3>Question:</h3>
            <p>{{ question }}</p>
        {% endif %}

        {% if answer %}
            <h3>Answer:</h3>
            <p>{{ answer }}</p>
        {% endif %}
        """,
        question=question,
        answer=answer,
    )


if __name__ == "__main__":
    app.run(debug=True)
