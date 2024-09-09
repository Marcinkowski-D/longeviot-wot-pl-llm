import threading, json

from openai import OpenAI
import anthropic
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

organization = 'org-xyz'
project = 'proj_xyz'

anthropic_claude_key = "sk-ant-apixyz"
gemini_key = "xyz"

wotScheme = open('wotv1.1.json', 'r', encoding='utf-8').read()


class MODEL:
    GPT_3_5_turbo = ["OpenAI", "gpt-3.5-turbo", '#openai_key', threading.Lock(), 0, 5]
    GPT_4_turbo = ["OpenAI", "gpt-4-turbo", '#openai_key', threading.Lock(), 0, 5]
    GPT_4 = ["OpenAI", "gpt-4", '#openai_key', threading.Lock(), 0,
             5]
    GPT_4o = ["OpenAI", "gpt-4o", '#openai_key', threading.Lock(),
              0, 5]
    GPT_4o_mini = ["OpenAI", "gpt-4o-mini", '#openai_key', threading.Lock(), 0, 5]
    Claude_3_5_sonnet = ['Anthropic', "claude-3-5-sonnet-20240620", anthropic_claude_key, None, threading.Lock(), 0, 5]
    Claude_3_haiku = ['Anthropic', "claude-3-haiku-20240307", anthropic_claude_key, None, threading.Lock(), 0, 5]
    Claude_3_sonnet = ['Anthropic', "claude-3-sonnet-20240229", anthropic_claude_key, None, threading.Lock(), 0, 5]
    Claude_3_opus = ['Anthropic', "claude-3-opus-20240229", anthropic_claude_key, None, threading.Lock(), 0, 5]
    gemini_1_5_pro = ['Google', "gemini-1.5-pro-latest", gemini_key, None, threading.Lock(), 0, 5]
    gemini_1_5_flash = ['Google', "gemini-1.5-flash-latest", gemini_key, None, threading.Lock(), 0, 5]


def prompt(prompt: str = None, model=None, messages=None):
    if model is None:
        raise Exception("No model specified")
    if prompt is None and messages is None:
        raise Exception("Please specify prompt or message array")

    if model[0] == 'OpenAI':
        client = OpenAI(
            organization=organization,
            project=project,
            api_key=model[2]
        )
        file = model[3]
        # print(file)
        if messages is None:
            messages = []
            messages.append({"role": "system",
                             "content": "You are an expert in translating datastructures into WoT Things descriptions."})
            messages.append({"role": "user", "content": prompt +
                                                        '\nThis is the WoT JSON Schema: \n\n' + wotScheme,
                             # "attachments": [
                             #     {"file_id": file['id'], "tools": [{"type": "file_search"}]}
                             # ]
                             })

        completion = client.chat.completions.create(
            model=model[1],
            messages=messages,
            max_tokens=4096,
            stream=False
        )
        completion.choices[0].message.content = completion.choices[0].message.content.strip('\n')

        r = completion.choices[0].message.content.strip('\n')
        if 'TOKEN LIMIT REACHED' not in r:
            try:
                json.loads(r)
            except Exception as e:
                print(f'{model[0]} {model[1]} json invalid', e)
                # print(response)
                r += "TOKEN LIMIT REACHED"
        if '...' in r:
            print(f'{model[0]} {model[1]} found ellpisis ...')
            r = r.split('...')[0] + 'TOKEN LIMIT REACHED'

        messages.append({"role": "assistant", "content": r})
        return r, messages

    if model[0] == 'Anthropic':
        client = anthropic.Anthropic(api_key=model[2])

        if messages is None:
            messages = []
            messages.append({"role": "user",
                             "content": [{
                                 "type": "text",
                                 "text": "You are an expert in translating datastructures into WoT Things descriptions.\n" +
                                         prompt +
                                         '\nThis is the WoT JSON Schema: \n\n' + wotScheme}]
                             })
        response = client.messages.create(
            model=model[1],
            max_tokens=4096,
            messages=messages
        )

        r = response.content[0].text.strip('\n')
        if 'TOKEN LIMIT REACHED' not in r:
            try:
                json.loads(r)
            except Exception as e:
                print(f'{model[0]} {model[1]} json invalid', e)
                # print(response)
                r += "TOKEN LIMIT REACHED"
        if '...' in r:
            print(f'{model[0]} {model[1]} found ellpisis ...')
            r = r.split('...')[0] + 'TOKEN LIMIT REACHED'

        messages.append({"role": "assistant", "content": [{
            "type": "text", "text": r}]})
        return r, messages

    if model[0] == 'Google':
        genai.configure(api_key=model[2])
        m = genai.GenerativeModel('gemini-1.0-pro-latest')
        if messages is None:
            messages = []
            messages.append({"role": "user",
                             "parts": "You are an expert in translating datastructures into JSON WoT Things descriptions.\n" +
                                      prompt +
                                      '\nThis is the WoT JSON Schema: \n\n' + wotScheme})
        response = m.generate_content(messages,
                                      safety_settings={
                                          HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                                          HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                                          HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                                          HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE
                                      })
        r = response.text.strip('\n')

        if 'TOKEN LIMIT REACHED' not in r:
            try:
                json.loads(r)
            except Exception as e:
                print(f'{model[0]} {model[1]} json invalid', e)
                # print(response)
                r += "TOKEN LIMIT REACHED"
        if '...' in r:
            print(f'{model[0]} {model[1]} found ellpisis ...')
            r = r.split('...')[0] + 'TOKEN LIMIT REACHED'

        messages.append({
            "role": "model",
            "parts": {
                "text": r
            }
        })

        return r, messages
