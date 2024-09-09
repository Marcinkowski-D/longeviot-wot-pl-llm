import json
from typing import List

from generated_dataclasses import ThingDescription, ActionElement, FormElementAction, EventElement, FormElementEvent, \
    PropertyElement, FormElementProperty, DataSchema, NoSecurityScheme
from openAI_functions import prompt, MODEL
from ioBroker import ioBroker, IOBrokerState

false = False
true = True


def create_tree_structure(flat_dict):
    tree = {}

    for key, value in flat_dict.items():
        parts = key.split('.')
        current = tree

        for part in parts[:-1]:
            # Navigate through or create new nested dictionary for each part
            if 'children' not in current:
                current['children'] = {}
            if part not in current['children']:
                current['children'][part] = {}
            current = current['children'][part]

        # Set the final part of the path to the value from flat_dict
        if 'children' not in current:
            current['children'] = {}
        current['children'][parts[-1]] = value

    return tree


def sanitizeObjects(objects):
    blacklist = ['admin', 'system', 'script', 'chromecast', 'backitup', 'discovery', 'history',
                 'hm_rega', 'info', 'iot', 'javascript', 'net-tools', 'ping', 'connected',
                 'simple-api', 'socketio', 'vis', 'web', 'ws', '0_userdata', '_design',
                 'yahka.meta._accessoryCategories', 'alias', 'enum', 'openweathermap',
                 'hm-rpc.0.updated', 'hm-rega', 'hm-rpc.0.HmIP-RCV-1', 'hm-rpc.0.BidCoS-RF',
                 'hue.0.lightScenes', 'hue.0.info'
                 ]
    keys = list(objects.keys())
    for key in keys:
        for b in blacklist:
            if key.startswith(b):
                del objects[key]
    return objects


def getIOBrokerObjects():
    objects = ioBroker.getObjects()
    objects = sanitizeObjects(objects)
    js = json.dumps(objects, indent=2)
    with open('serialized/ioBroker.json', 'w', encoding='utf-8') as f:
        f.write(js)
    # print(js)
    print(round(len(js) / 1024 / 1024, 2), 'MB')
    return objects


nameWhitelist = []
nameBlacklist = []
with open('serialized/whitelist.json', 'r') as f:
    nameWhitelist = json.load(f)
with open('serialized/blacklist.json', 'r') as f:
    nameBlacklist = json.load(f)


def getProperty(state):
    path = state.id
    property = None
    propertyTitle = path.split('.')[-1]

    readOnly = state.common.read and not state.common.write
    writeOnly = not state.common.read and state.common.write
    if not writeOnly and not readOnly:
        # print(' #######  IN #######')
        # print(state.toString())
        observable = state.common.read
        minimum = state.common.min if 'min' in state.common.__dict__ else None
        maximum = state.common.max if 'max' in state.common.__dict__ else None
        type = state.common.__dict__.get('role', None)
        unit = None
        if state.native:
            unit = state.native.get('UNIT', state.native.get('unit', None))

        property = PropertyElement(
            title=propertyTitle,
            readOnly=readOnly,
            writeOnly=writeOnly,
            minimum=minimum,
            maximum=maximum,
            type=type,
            unit=unit,
            observable=observable,
            forms=[
                FormElementProperty(href=path, contentType='application/json')
            ],
            description=type
        )
        # print(' ####### OUT #######')
        # print(property.toString())
        # input("continue")
    return property, propertyTitle


def getEvent(state):
    path = state.id
    eventTitle = path.split('.')[-1]

    event = None
    # ## must be read only
    if state.common.read and not state.common.write:
        # print(' #######  IN #######')
        # print(state.toString())
        type = state.common.__dict__.get('role', None)
        event = EventElement(
            title=eventTitle,
            description=type,
            type=type,
            data=DataSchema(
                type=state.common.type
            ),
            dataResponse=DataSchema(
                type="object"
            ),
            forms=[
                FormElementEvent(href=path, contentType='application/json', subprotocol="polling")
            ]
        )
        # print(' ####### OUT #######')
        # print(event.toString())
        # input("continue")

    return event, eventTitle


def getAction(state):
    path = state.id
    actionTitle = path.split('.')[-1]
    action = None
    # ## must be write only
    if not state.common.read and state.common.write:
        readOnly = False
        writeOnly = True
        unit = None
        if state.native:
            unit = state.native.get('UNIT', state.native.get('unit', None))
        type = state.common.__dict__.get('role', None)

        action = ActionElement(
            title=actionTitle,
            description=type,
            input=DataSchema(
                type="object",
                unit=unit,
                properties={
                    "value": PropertyElement(
                        title=state.common.name,
                        type=state.common.type,
                        minimum=state.common.min,
                        maximum=state.common.max,
                        readOnly=readOnly,
                        writeOnly=writeOnly,
                    )
                },
                required=["value"]
            ),
            output=DataSchema(
                type="object"
            ),
            forms=[
                FormElementAction(href=path, contentType='application/json')
            ]
        )
        # print(' #######  IN #######')
        # print(state.toString())
        # print(' ####### OUT #######')
        # print(action.toString())
        # input("continue")
    return action, actionTitle


def searchForDevices(objects):
    devices: List[ThingDescription] = []

    # if os.path.exists('serialized/wotDevices.json'):
    #     with open('serialized/wotDevices.json', 'r', encoding='utf-8') as f:
    #         devices = [IoTDevice.fromLDT(d) for d in json.loads(f.read())]
    #         return devices

    for id, state_data in objects.items():
        state = IOBrokerState.fromJson(state_data)
        skip = False
        for n in nameBlacklist:
            if state.common.name.endswith(n):
                skip = True
                break
            if id.endswith(n):
                skip = True
                break
        if skip:
            continue

        process = False

        elemName = state.common.name.split('.')[-1]
        # for n in nameWhitelist:
        if elemName in nameWhitelist:
            process = True

        if isinstance(state.common.name, dict):
            continue

        if process:
            spl = state.id.split('.')
            spl.pop(-1)
            while spl and spl[-1].isnumeric():
                spl.pop(-1)
            if len(spl) <= 1:
                continue
            devId = '.'.join(spl)
            device: ThingDescription
            try:
                device = next(d for d in devices if d.id == devId)
            except StopIteration:
                name = state.common.name.split(':')[0]
                # print(state)
                device = ThingDescription(id=devId, title=name)
                device.securityDefinitions = {
                    "nosec": NoSecurityScheme()
                }
                device.security = "nosec"
                device.properties = {}
                device.events = {}
                device.actions = {}
                device.description = ""
                devices.append(device)

            action, actionTitle = getAction(state)
            event, eventTitle = getEvent(state)
            property, propertyTitle = getProperty(state)

            if property is not None:
                device.properties[propertyTitle] = property
            if action is not None:
                device.actions[actionTitle] = action
            if event is not None:
                device.events[eventTitle] = event
        else:
            print('not', id)

    # with open('serialized/wotDevices.json', 'w') as f:
    #     f.write(json.dumps([d.toDict() for d in devices], indent=2))
    return devices


def generateDescription(device: dict):
    description = ""
    if device["description"] is None or len(device["description"]) == 0:
        description = prompt('Generate a human readable description of the IOT device, like '
                             '"Washing machine socket, actual temperature, current, energy counter, frequency, power, voltage", '
                             '"Bedroom light. Brightness, hue, saturation, color temperature, red, green, and blue levels" or '
                             '"Basement temperature humidity control". '
                             'Write as much information in the description as you can, but keep it short. '
                             'Do not print out the id as a part of the description. '
                             'Do not include the manufacturer or the model name. '
                             'Do not include any numbers or counters depending on the device\'s title. '
                             'Translate anything non-english into english. '
                             'Use short words and avoid abbreviations. Write more like an enumeration of keywords instead of a sentence. '
                             'Do not include line breaks or tabs. '
                             'Only output the description without additional text. Here comes the device object:\n\n' + json.dumps(
            device, indent=2), model=MODEL.GPT_3_5_turbo)
    return description
