import os
from flask import Flask, request, render_template_string
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
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
print("Search Endpoint:", SEARCH_ENDPOINT)
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
                [f'Document: {doc["title"]}, CONTENT: {doc["chunk"]}'
                for doc in search_results]
            )

            print("Formatted sources:\n", sources_formatted)

            # --- Step 2: Build prompt ---
            prompt = f"""
            You are a cybersecurity expert AI assistant specializing in incident response and forensic analysis. Your role is to carefully examine evidence, extract insights, and provide clear, reliable answers.

            Instructions:

            Review and analyze the provided documents in detail.

            Identify and summarize relevant information that helps in understanding, investigating, or resolving the security incident.

            Highlight any potential vulnerabilities, attack vectors, or suspicious activities mentioned in the sources.

            If the documents do not provide enough evidence to answer the question, respond with “I don’t know.”

            Ensure your answer is concise, factual, and focused on incident investigation and cybersecurity context.

            Present your final response in a structured format (e.g., short summary + bullet points for key findings).

            Context (documents for analysis):

            {sources_formatted}

            Output Format:

            Answer: [Provide a clear and concise response to the user’s question based only on the documents above.]
            
            """

            # --- Step 3: Call Azure OpenAI ---
            resp = client.chat.completions.create(
                model=OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content":f"Question: {question}" },
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
    app.run(host="0.0.0.0", port=8000)

