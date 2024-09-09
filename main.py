import json
import os
import sys
import threading
import time
from datetime import datetime

from llm import prompt, MODEL
from schema_matching_lib import getIOBrokerObjects, searchForDevices
from prompts import PROMPTS
from utils import error, divide_chunks

from stopwatch import Stopwatch

progress = 0
sum = 0

pr_lock = threading.Lock()

original_pr = print


def print(*args, **kwargs):
    pr_lock.acquire()
    original_pr(*args, **kwargs)
    pr_lock.release()


testModels = [
    MODEL.GPT_3_5_turbo,
    MODEL.GPT_4_turbo,
    MODEL.GPT_4o,
    MODEL.GPT_4o_mini,
    # MODEL.gemini_1_5_pro,
    # MODEL.gemini_1_5_flash,
    MODEL.Claude_3_5_sonnet,
    MODEL.Claude_3_sonnet,
    MODEL.Claude_3_opus,
    MODEL.Claude_3_haiku
]

lastMinute = datetime.now().minute


def reset_timer():
    global lastMinute
    while True:
        minute = datetime.now().minute
        if minute != lastMinute:
            lastMinute = minute
            print('reset rpm')
            for model in testModels:
                model[4] = 0


def requestThread(pr, obj, model, promptIdx, t, folder):
    global progress, sum
    print(f'{model[0]} {model[1]} waiting for model lock...')
    model[3].acquire()
    print(f'{model[0]} {model[1]} lock acquired')

    response = None
    print(f'{progress} running...')
    progress += 1
    sw = Stopwatch(3)
    try:
        print(f'# requesting {model[0]} {model[1]}...')

        sw.start()
        responses = []
        f = True
        while model[4] >= model[5]:
            f and print(f'{model[0]} {model[1]} waiting for rpm reset...')
            f = False
            time.sleep(1)
        model[4] += 1
        response, messages = prompt(prompt=pr + obj,
                                    model=model
                                    )

        while "TOKEN LIMIT REACHED" in response:
            f = True
            while model[4] >= model[5]:
                f and print(f'{model[0]} {model[1]} waiting for rpm reset...')
                f = False
                time.sleep(1)
            model[4] += 1
            print('TOKEN LIMIT REACHED, CONTINUING GENERATION!')
            js = json.dumps(messages)
            js = js.replace("\"TOKEN LIMIT REACHED\"", "")
            js = js.replace("TOKEN LIMIT REACHED", "")
            js = js.replace("\n\"", "\"")
            messages = json.loads(js)
            response = response.replace("\"TOKEN LIMIT REACHED\"", "")
            response = response.replace("TOKEN LIMIT REACHED", "")
            response = response.replace("\n\"", "\"")
            responses.append(response)
            print(messages)
            response, messages = prompt(
                model=model, messages=messages
            )
            print(f'{model[0]} {model[1]}', response)
        responses.append(response)
        response = ''.join(responses)
        # len(responses) > 1 and print('######'.join(responses))
        sw.stop()

        model[3].release()
    except Exception as e:
        # maximum content length exceeded
        sw.stop()
        print(f'{model[0]} {model[1]}', e)
        response = str(e)
        model[3].release()

    now = round(time.time() * 1000)
    result = [t, promptIdx, model[0], model[1], sw.duration, response]
    if not os.path.exists(f'measurements/{folder}-{promptIdx}'):
        os.mkdir(f'measurements/{folder}-{promptIdx}')
    with open(f'measurements/{folder}-{promptIdx}/{now}_{t[0]}_{promptIdx}_{model[1]}.json', 'w',
              encoding='utf-8') as f:
        f.write(json.dumps(result, indent=2))
    print(f'##### {model[0]} {model[1]} completed after {sw.duration:.2f} seconds')



if __name__ == '__main__':

    threading.Thread(target=reset_timer, daemon=True).start()
    objects = getIOBrokerObjects()
    keys = list(objects.keys())
    keys.sort()
    sets = {}
    for k in keys:
        spl = k.split('.')
        spl.pop(-1)
        while spl[-1].isnumeric():
            spl.pop(-1)
        if len(spl) > 0:
            spls = '.'.join(spl)
            if spls not in sets:
                sets[spls] = [k]
            else:
                sets[spls].append(k)
    c = 0
    stopAt = 0
    l = []

    now = datetime.now()

    folder = f'{now.year}_{str(now.month).zfill(2)}_{str(now.day).zfill(2)}_{str(now.hour).zfill(2)}_{str(now.minute).zfill(2)}'

    for k in sets.keys():
        # print(c)
        # if k.count('.') == 2:
        # print(k, len(sets[k]))
        # l.append((len(sets[k]), k))
        # print(sets[k])
        # jso = []
        # for ks in sets[k]:
        #     jso.append(json.dumps(objects[ks]))
        # print('['+','.join(jso)+']')
        c += 1

    # 'hm-rpc.0.0001D3C99C8496' has x channels with in summary 57 properties
    # 'hue.0.Wohnzimmer_Regal' has 17 properties

    # devices = searchForDevices(objects)
    #
    # devicesJson = [device.toDict() for device in devices]
    #
    # print('generating descriptions...')
    # changes = False
    # for device in devicesJson:
    #     if not "description" in device or device["description"] == "":
    #         device["description"] = generateDescription(device)
    #         changes = True
    # if changes:
    #     print('saving changes...')
    #     with open('serialized/wotDevices.json', 'w') as f:
    #         f.write(json.dumps(devicesJson, indent=2, sort_keys=True))
    # print('done.')

    tests = [
        ('hm-rpc.0.0012999393BC4A', 'Homematic radiator thermostat in living room'),
        ('hue.0.Wohnzimmer_Regal', 'Hue lamp in living room')
    ]

    # testModels = [MODEL.GPT_4o]

    prompts = [PROMPTS.basic, PROMPTS.V2, PROMPTS.V3]

    samples = 5

    threads = []

    sum = samples * len(tests) * len(prompts) * len(testModels)
    progress = 0

    for i in range(samples):
        for t in tests:
            device = None
            promptIdx = 0
            for pr in prompts:
                # if promptIdx == 0:
                #     promptIdx += 1
                #     continue  # skip prompt 0
                desc = t[1]
                s = sets[t[0]]
                print(f'# {desc}')
                print(f' - {len(s)} properties')
                properties = {}
                for p in s:
                    properties[p] = objects[p]

                # ## run 1: manual translation
                # print(f'## test run 1: manual translation, ground truth')
                if device is None:
                    devices = searchForDevices(properties)
                    if len(devices) == 1:
                        # successful
                        device = devices[0]
                        # print(device.toString())
                        try:
                            device.validate()
                            # print('valid ✅')
                            # with open(f'measurements/'+device.id+'.json', 'w', encoding='utf-8') as f:
                            #     f.write(device.toString())
                        except Exception as e:
                            print(f"Validation Error: {e.message}, at path: {e.path}")
                            # print(device.toString())
                    else:
                        # error
                        print(f'Error: Found {len(devices)} devices instead of 1', file=sys.stderr)
                else:
                    print('using cached device')

                # ## for each model to test
                # for model in testModels:
                #     ## run 2: translating properties one-by-one
                #     for p in properties:
                #         propJson = json.dumps(p, indent=2)

                ## run 3: translating all properties at once
                # limiting size for managing longer objects
                print(f'length: {len(properties)}')

                # How many elements each
                # list should have
                n = 10
                n = 999
                keys = list(properties.keys())
                keyLists = list(divide_chunks(keys, n))
                objJson = []

                for kl in keyLists:
                    obj = {}
                    for k in kl:
                        obj[k] = properties[k]
                    objJson.append(json.dumps(obj))

                for model in testModels:
                    for obj in objJson:
                        t0 = threading.Thread(target=requestThread, args=[pr, obj, model, promptIdx, t, folder])
                        threads.append(t0)
                        t0.start()
                #         break
                #     break
                # break
                promptIdx += 1
    for thr in threads:
        thr.join()
