import requests
import json

# ollama run llama2
# ollama list
# pip install open-webui
# open-webui serve
# docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
# then check http://localhost:3000
corpus_of_documents = [
    "Take a leisurely walk in the park and enjoy the fresh air.",
    "Visit a local museum and discover something new.",
    "Attend a live music concert and feel the rhythm.",
    "Go for a hike and admire the natural scenery.",
    "Have a picnic with friends and share some laughs.",
    "Explore a new cuisine by dining at an ethnic restaurant.",
    "Take a yoga class and stretch your body and mind.",
    "Join a local sports league and enjoy some friendly competition.",
    "Attend a workshop or lecture on a topic you're interested in.",
    "Visit an amusement park and ride the roller coasters."
]
# user_input = "I love roller coasters and I am in France" # Visit Disneyland Paris
# user_input = "I like museums and I am in Zurich" # Visit the Kunsthaus art museum in Zurich.
user_input = "I am bored"

# https://github.com/jmorganca/ollama/blob/main/docs/api.md
full_response = []

prompt = """
You are a bot that makes recommendations for activities. You answer in very short sentences and do not include extra information.
This is the recommended activity: {relevant_document}
The user input is: {user_input}
Compile a recommendation to the user based on the recommended activity and the user input.
"""

def jaccard_similarity(query, document):
    query = query.lower().split(" ")
    document = document.lower().split(" ")
    intersection = set(query).intersection(set(document))
    union = set(query).union(set(document))
    return len(intersection)/len(union)

def return_response(query, corpus):
    similarities = []
    for doc in corpus:
        similarity = jaccard_similarity(query, doc)
        similarities.append(similarity)
    return corpus[similarities.index(max(similarities))]

relevant_document = return_response(user_input, corpus_of_documents)
headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
url = 'http://localhost:11434/api/generate' # if llama in general
# url = 'http://localhost:3000/api/v1/generate'  # Direct Open WebUI endpoint
data = {
    "model": "llama3.2",
    "prompt": prompt.format(user_input=user_input, relevant_document=relevant_document) # if llama in general
    # "messages": [
    #     {
    #         "role": "user",
    #         "content": prompt.format(user_input=user_input, relevant_document=relevant_document)# Open WebUI API 
    #     }
    # ],
    # "stream": True,
    # "temperature": 0.7,
    # "max_tokens": 500
}

try:
    response = requests.post(url, json=data, headers=headers, stream=True)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
    else:
        for line in response.iter_lines():
            if line:
                decoded_line = json.loads(line.decode('utf-8'))
                if 'response' in decoded_line:
                    full_response.append(decoded_line['response'])
                elif 'error' in decoded_line:
                    print(f"Error from Open WebUI: {decoded_line['error']}")
                else:
                    print(f"Unexpected response format: {decoded_line}")
        # for line in response.iter_lines():
        #     if line:
        #         try:
        #             decoded_line = json.loads(line.decode('utf-8'))
        #             if 'choices' in decoded_line and len(decoded_line['choices']) > 0:
        #                 if 'delta' in decoded_line['choices'][0] and 'content' in decoded_line['choices'][0]['delta']:
        #                     content = decoded_line['choices'][0]['delta']['content']
        #                     full_response.append(content)
        #             elif 'error' in decoded_line:
        #                 print(f"Error from Open WebUI: {decoded_line['error']}")
        #             else:
        #                 print(f"Unexpected response format: {decoded_line}")
        #         except json.JSONDecodeError:
        #             print(f"Failed to decode line: {line}")
finally:
    if 'response' in locals():
        response.close()

if full_response:
    print(''.join(full_response))
else:
    print("No response received from Open WebUI. Make sure the server is running at http://localhost:3000 and your model is properly loaded.")



