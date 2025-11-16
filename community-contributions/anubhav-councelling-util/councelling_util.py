import gradio as gr
import os
from dotenv import load_dotenv
from openai import OpenAI
from data_extractor import get_questionnaire_data
import json
# Load environment variables in a file called .env
# Print the key prefixes to help with any debugging

load_dotenv(override=True)
openai_api_key = os.getenv('OPENAI_API_KEY')

if openai_api_key:
    print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
    get_questionnaire_data("Grok")
else:
    print("OpenAI API Key not set")

openai = OpenAI()
MODEL = 'gpt-4.1-mini'
CONFIDENCE_THRESHOLD = 9

system_message = """You are a personal counselor who will take the questions along with the answers and rate the answers with respect to OCEAN parameters.
OCEAN parameters are: Openness to Experience, Conscientiousness, Extraversion, Agreeableness, Neuroticism in json format which is like this for each traits:
[{"trait": "Conscientiousness", "score": "6", "reasonForScore": ["Input shows user will tackle situation like", "other details how score is deduced"], "reasonForNegativeScore": ["same as reasonForScore values"],  "confidence": 10 (This show how confident you are), "reasonForLessConfidence": ["list of string"]}]"""

agent_message = f"""
    You are a personality assessment expert.
    Generate 2 new situational judgment questions for the each traits in trait key under user input.
    Analyse the values of these three keys as well reasonForScore, reasonForNegativeScore, reasonForLessConfidence
     to generate the further questions.
    Each question should:
    - Present a realistic scenario (like a short story or work situation)
    - Include 4 options (A–D) representing behavioral responses
    - Subtly test that specific trait (not too obvious)
    - Avoid mentioning the trait name directly.
    - This is targetting age group of 16-23. One who wants to be in college or just undergrad passout.

    Return strictly in JSON format:
    [
      {{
        "question": "string",
        "options": ["A", "B", "C", "D"]
      }},
      {{
        "question": "string",
        "options": ["A", "B", "C", "D"]
      }}
    ]
    """


QUESTIONNAIRE_DATA = get_questionnaire_data("ChatGPT")

questions = QUESTIONNAIRE_DATA["Question"]


def openAI_response(system_message, formatted_results):
    messages = [{"role": "system", "content": system_message}] + [{"role": "user", "content": formatted_results}]
    response = openai.chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content

def collect_answers(*answers):
    """
    Collects the answers from all radio buttons and formats them for display.
    The order of inputs corresponds to the order they were defined in the UI.
    """
    # results = {}
    
    # Get all question IDs in the order they appear in the dictionary
    questions = QUESTIONNAIRE_DATA["Question"]
    formatted_results = "## 📝 Questionnaire Results\n"

    
    for q, a in zip(questions, answers):
        formatted_results += f"* **{q}**\n  * **Response:** {a}\n"

    response = openAI_response(system_message, formatted_results)

    formatted_results += "## 📝 Counselor Response\n " + response
    
    personality_calibration_agent(response)
        
    return formatted_results


def generate_situational_questions(trait):

    response = openAI_response(agent_message, ensure_json_string(trait))
    # This needs to be added on UI 
    print("Additional Questions: " + response)

def ensure_json_string(value):
    """
    Ensures the input is a JSON string.
    - If it's already a dict or list → converts to JSON string.
    - If it's a valid JSON string → returns as-is.
    - If it's a plain string → returns as-is.
    """

    # Case 1: if already a Python dict or list
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2)

    # Case 2: if it's a string, check if it's valid JSON
    if isinstance(value, str):
        try:
            json.loads(value)  # will throw if not valid JSON
            return value  # already a JSON string
        except json.JSONDecodeError:
            return value  # plain string, just return as-is

    # Case 3: any other data type (e.g., int, None, custom object)
    return str(value)


# Tweak calls here
def personality_calibration_agent(traits_json):
    traits_data = json.loads(traits_json)
    low_confidence_traits = analyze_trait_json(traits_data)

    # for trait_details in low_confidence_traits:
    generate_situational_questions(low_confidence_traits)


def analyze_trait_json(traits_json):
    low_confidence_traits = []

    for trait in traits_json:
        if trait["confidence"] <= CONFIDENCE_THRESHOLD:
            low_confidence_traits.append(trait)

    return low_confidence_traits

with gr.Blocks(title="Counselling Questionnaire") as demo:
    gr.Markdown("# Survey on Application Usability")
    gr.Markdown("Please provide your honest feedback by selecting the appropriate option for each statement.")
    
    # List to hold all the Gradio Radio components
    question_inputs = []

    questions = QUESTIONNAIRE_DATA["Question"]
    optionA = QUESTIONNAIRE_DATA["Option A"]
    optionB = QUESTIONNAIRE_DATA["Option B"]
    optionC = QUESTIONNAIRE_DATA["Option C"]
    optionD = QUESTIONNAIRE_DATA["Option D"]
    
    with gr.Tabs() as tabs:
        # Create 10 tabs, one for each question
        for i, (q_id, q_text) in enumerate(questions.items()):
            options = [optionA[i], optionB[i], optionC[i], optionD[i]]
            with gr.Tab(f"Page {i+1}", id=q_id):
                gr.Markdown(f"### Question {i+1}: {q_text}")
                
                # Create a Radio component for the question
                # The label is set to be the question text itself
                radio_input = gr.Radio(
                    choices=options,
                    label="Your Response",
                    value=None, # Starts with no selection
                    interactive=True
                )
                question_inputs.append(radio_input)
                
        # Final submission tab
        with gr.Tab("Submit Survey"):
            gr.Markdown("## 🎉 Submission Page")
            submit_button = gr.Button("Submit All Answers", variant="primary")
            output_display = gr.Markdown("Click 'Submit All Answers' to see your responses.")
            
    # Define the click event for the submission button
    # The inputs are ALL the radio components created in the loop
    submit_button.click(
        fn=collect_answers,
        inputs=question_inputs,
        outputs=output_display,
        show_progress=True
    )

if __name__ == "__main__":
    demo.launch()