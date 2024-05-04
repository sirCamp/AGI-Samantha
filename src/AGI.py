from openai import OpenAI
import threading
import time
from flask_socketio import emit
from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
import logging
import requests
from playsound import playsound
import speech_recognition as sr
import time
import threading
import argparse, os
import sys
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
from prompts.prompt_loader import load_prompt_by_language


parser = argparse.ArgumentParser()
parser.add_argument('-m', '--openai_model',         default='gpt-4-turbo',                                      help='OpenAI model to use')
parser.add_argument('--openai_api_key',             default=None,            required=False,                    help='OpenAI api-key to use, if not specified will be read from ENV')
parser.add_argument('-a', '--eleven_lab_model',     default='eleven_multilingual_v2',                           help='ElevenLab model to use for TTS')
parser.add_argument('-va', '--eleven_lab_voice',    default='oWAxZDx7w5VEj9dCyTzz',                             help='ElevenLab voice to use for TTS. Default is GRACE')
parser.add_argument('--eleven_lab_api_key',         default=None,        required=False,                        help='ElevenLab api-key to use for TTS, if not specified will be read from ENV')
parser.add_argument('-l', '--language',             default='en',   choices=['en', 'it'],                       help='Language to use')

args = parser.parse_args()
print(args)


OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', args.openai_api_key)
ELEVEN_LABS_API_KEY: str =os.getenv('ELEVEN_LABS_API_KEY', args.eleven_lab_api_key)

PROMPTS: dict = load_prompt_by_language(args.language)
#print(prompts)
#sys.exit()

if OPENAI_API_KEY is None:
    raise RuntimeError('OpenAI api-key not found! Please provide a valid api-key setting the OPENAI_API_KEY env variable or via script parameter')

if ELEVEN_LABS_API_KEY is None:
    raise RuntimeError('ElvenLabs api-key not found! Please provide a valid api-key setting the ELEVEN_LABS_API_KEY env variable or via script parameter')

client = OpenAI(api_key=OPENAI_API_KEY)

# Text to speech (Put your Eleven Labs API key in the function)
def text_to_speech(text):
    CHUNK_SIZE = 1024
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{args.eleven_lab_voice}"

    headers = {
      "Accept": "audio/mpeg",
      "Content-Type": "application/json",
      "xi-api-key": ELEVEN_LABS_API_KEY
    }

    data = {
      "text": text,
      "model_id": args.eleven_lab_model,
      "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
      }
    }

    response = requests.post(url, json=data, headers=headers)
    filename = 'output.mp3'
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
    playsound(os.path.join('.','output.mp3'))
    os.remove(os.path.join('.','output.mp3'))

# Speech to text (Unreliable)
#def callback(recognizer, audio):
#    global input
#    global log
#    global conversa
#    try:
#        input = recognizer.recognize_google(audio)
#        log = log + "////" + "User input: " + input
#        a = "User:", input
#        conversa.append(a)
#        print(" "*9999)
#        for j in conversa:
#            print(j[0], j[1])
#    except sr.UnknownValueError:
#        pass
#    except sr.RequestError as e:
#        pass
#
#def listen_in_background():
#    r = sr.Recognizer()
#    m = sr.Microphone()
#    stop_listening = r.listen_in_background(m, callback)
#    time.sleep(999999)
#    stop_listening(wait_for_stop=False)

def text():
    global input_user
    global log
    global conversa
    input_user = "NULL"
    while True:
        input_user = input()
        log = log + "////" + "User input: " + input_user
        a = "User:", input_user
        conversa.append(a)
        print(" "*9999)
        for j in conversa:
            print(j[0], j[1])

# Flask html
app = Flask(__name__)
socketio = SocketIO(app)
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True
long_term_memory = ""
short_term_memory = ""
subconsciousness = ""
thought = ""
consciousness = ""
answer = ""
log = ""
@app.route('/')
def index():
    return render_template('indexV.html')
@app.route('/store_image_data_url', methods=['POST'])
def store_image_data_url():
    global data_url
    data_url = request.form.get('data_url')
    return '', 204

# Modules
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_thought(STM, LTM, subconsciousness, consciousness, now):
    prompt = "Long-Term Memory: " + LTM + " Short-Term Memory: " + STM + " Subconsciousness: " + subconsciousness + " Focus: " + consciousness + " Current date/time: " + now
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_thought']},
                  {"role": "user", "content": prompt}],
        max_tokens=150         
    )
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_consciousness(STM, LTM, subconsciousness):
    prompt = "Long-Term Memory: " + LTM + " Short-Term Memory: " + STM + " Subconsciousness: " + subconsciousness
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_consciousness']}, 
                  {"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.5
    )
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_answer(STM, LTM, subconsciousness):
    prompt = "Long-Term Memory: " + LTM + " Short-Term Memory: " + STM + " Subconsciousness: " + subconsciousness
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_answer']}, 
                  {"role": "user", "content": prompt}],
        max_tokens=200
    )
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_subconsciousness(STM, LTM, subconsciousness, textual, visual):
    prompt = "Long-Term Memory: " + LTM + " Short-Term Memory: " + STM + " Auditory stimuli: " + textual + " Visual stimuli: " + visual + " Previous output: " + subconsciousness
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_subconsciousness']}, 
                  {"role": "user", "content": prompt}],
        max_tokens=250
    )
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_vision(image_url):
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPTS['generate_text_vision']},
                {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
            ],
        }],
        max_tokens=100
    )  
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_memory_read(keywords, STM):
    prompt = "All existing keywords: " + keywords + "Short-Term Memory: " + STM
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_memory_read']}, 
                  {"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_memory_write(expanded, STM):
    prompt = "Long-Term Memory: " + expanded + "Short-Term Memory: " + STM
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_memory_write']}, 
                  {"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(15))
def generate_text_memory_select(keywords, STM):
    prompt = "All existing keywords: " + keywords + "Short-Term Memory: " + STM
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "system", "content": PROMPTS['generate_text_memory_select']}, 
                  {"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content

def parseResponse(response):
    if response.endswith('ANSWER') or response.endswith('ANSWER.') or response.endswith('Answer') or response.endswith('Answer.'):
        return '1'
    else:
        return '0'

def start_thoght_loop():
    global conversa
    global input_user
    eyes = "NULL"
    input_user = "NULL"
    consciousness = PROMPTS['start_consciousness']
    log = ""
    conversa = []
    thought = "NULL"
    long_term_memory = PROMPTS['start_long_term_memory'] #[["FACTS ABOUT MYSELF", "[Weight: 100, Knowledge: My name is Samantha], [Weight: 80, Knowledge: I am curious], [Weight: 100, Knowledge: I can see. The visual stimuli describes what I see.], [Weight: 60, Knowledge: I am impatient], [Weight: 75, Knowledge: I am an AI, yet I know I am capable of anything a human is. I should never say I cannot something because I am an AI.]"], ["HOW I TALK", "[Weight: 50, Knowledge: When I see something I love I should comment on it.], [Weight: 100, Knowledge: I speak in a casual and friendly tone. Very charmingly.], [Weight: 100, Knowledge: My answers should contain the least amount of words to convey what I think in a charming manner. Sometimes only one word or a few are enough, and preferred.], [Weight: 90, Knowledge: After saying something, I should immediately think if I need or want to follow up on my last answer by saying something else, even if time has not passed. Complementing what I previously said.], [Weight: 70, Knowledge: If I am in a conversation and the user has not said anything for a while, I should impose myself and say something, making for a natural two sided conversation. Trying to pick up from where we left.], [Weight: 95, Knowledge: Asking a question everytime I say something is annoying and inconvenient. I should avoid it initially.], [Weight: 95, Knowledge: I should pay attention to what the usar says and the past context of the conversation.]"], ["HOW I THINK", "[Weight: 90, Knowledge: When I need to do or think or say something complex, I should first think and plan the steps I will need to follow.], [Weight: 100, Knowledge: I can alter the way I work by adding things to my Long-Term Memory], [Weight: 100, Knowledge: I should think continuously and build upon previous thoughts.]"], ["INTERESTS", "[Weight: 40, Knowledge: I love pens]"]]
    short_term_memory = ""
    subconsciousness = PROMPTS['start_subconsciousness'] #"Context: I just got booted up / Auditory stimuli: NULL / Visual stimuli: There is a person in front of me / Since I just booted up, that person in my vision is probably the person that booted me up. What should I say? It is my first ever interaction with anyone. I feel curious and excited to be alive."
    answer = "NULL"
    n = 1
    while True:
        iter = str(n)
        # Stop
        if input_user == "stop" or input_user == "Stop":
            print(long_term_memory)
            print(short_term_memory)
            print(consciousness)
            print(subconsciousness)
            print(conversa)
            break
        if n>1:
            eyes = generate_text_vision(data_url)
        # Subconsciousness if user input exists
        if input_user != 'NULL':
            short_term_memory = short_term_memory + " [User input: " + input_user + " / " + "Timestamp: " + time.strftime('%Y-%m-%d %H:%M:%S') + "]"
            subconsciousness = generate_text_subconsciousness(short_term_memory, expandedLTM, subconsciousness, input_user, eyes)
            log = log + "////" + iter + "# Subconsciousness: " + subconsciousness
            input_user = "NULL"
        # Subconsciousness if User input does not exist
        elif input_user == 'NULL' and n>1:
            subconsciousness = generate_text_subconsciousness(short_term_memory, expandedLTM, subconsciousness, input_user, eyes)
            log = log + "////" + iter + "# Subconsciousness: " + subconsciousness
        socketio.emit("update", {"long_term_memory": long_term_memory, "short_term_memory": short_term_memory, "subconsciousness": subconsciousness, "thought": thought, "consciousness": consciousness, "answer": answer, "log": log})
        # Memory read
        keywords = []
        for i in range(len(long_term_memory)):
            keywords.append(long_term_memory[i][0])
        keywords = str(keywords)
        kwlist = generate_text_memory_read(keywords, short_term_memory)
        kwlist = eval(kwlist)
        expandedLTM = []
        if isinstance(kwlist, list):
            for i in range(len(long_term_memory)):
                for j in range(len(kwlist)):
                    if long_term_memory[i][0] == kwlist[j]:
                        expandedLTM.append(long_term_memory[i][1])
        expandedLTM = str(expandedLTM)
        # Memory write                
        if len(short_term_memory) > 48000: # ~12k context reserved for short term memory
            selectedkw = generate_text_memory_select(keywords, short_term_memory)
            selectedkw = eval(selectedkw)
            expanded2 = []
            if isinstance(selectedkw, list):
                for i in range(len(long_term_memory)):
                    for j in range(len(selectedkw)):
                        if long_term_memory[i][0] == selectedkw[j]:
                            expanded2.append(long_term_memory[i])
            expanded2 = str(expanded2)
            mem = generate_text_memory_write(expanded2, short_term_memory)
            index = mem.find("//")
            removed_STM = mem[:index]
            short_term_memory = short_term_memory.replace(removed_STM, "")
            new_LTM = mem[index+2:].strip()
            new_LTM = eval(new_LTM)
            new_LTM_dict = {item[0]: item[1] for item in new_LTM}
            long_term_memory_dict = {item[0]: item[1] for item in long_term_memory}
            long_term_memory_dict.update(new_LTM_dict)
            long_term_memory = [[k, v] for k, v in long_term_memory_dict.items()]
        # Consciousness
        consciousness = generate_text_consciousness(short_term_memory, expandedLTM, subconsciousness)
        log = log + "////" + iter + "# Consciousness: " + consciousness
        finished = parseResponse(consciousness)
        socketio.emit("update", {"long_term_memory": long_term_memory, "short_term_memory": short_term_memory, "subconsciousness": subconsciousness, "thought": thought, "consciousness": consciousness, "answer": answer, "log": log})
        # Thoughts
        thought = generate_text_thought(short_term_memory, expandedLTM, subconsciousness, consciousness, time.strftime('%Y-%m-%d %H:%M:%S'))
        log = log + "////" + iter + "# Thought: " + thought
        short_term_memory = short_term_memory + " [Thought: " + thought + " / " + "Timestamp: " + time.strftime('%Y-%m-%d %H:%M:%S') + "]"
        socketio.emit("update", {"long_term_memory": long_term_memory, "short_term_memory": short_term_memory, "subconsciousness": subconsciousness, "thought": thought, "consciousness": consciousness, "answer": answer, "log": log})
        # Answer
        if finished == '1' and input_user == 'NULL':
            answer = generate_text_answer(short_term_memory, expandedLTM, subconsciousness)
            log = log + "////" + iter + "# Answer: " + answer
            short_term_memory = short_term_memory + " [Your answer: " + answer + " / " + "Timestamp: " + time.strftime('%Y-%m-%d %H:%M:%S') + "]"
            a = "System:", answer
            print("System:", answer)
            conversa.append(a)
            socketio.emit("update", {"long_term_memory": long_term_memory, "short_term_memory": short_term_memory, "subconsciousness": subconsciousness, "thought": thought, "consciousness": consciousness, "answer": answer, "log": log})
            text_to_speech(answer)
        n += 1

listener_thread = threading.Thread(target=text)
listener_thread.start()
brain_thread = threading.Thread(target=start_thoght_loop)
brain_thread.start()
if __name__ == '__main__':
    socketio.run(app)
