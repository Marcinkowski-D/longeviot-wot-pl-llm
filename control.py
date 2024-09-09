import json, os

from generated_dataclasses import ThingDescription, SecurityScheme, ActionElement, EventElement, PropertyElement

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

statistics = {}

groundTruths = {

}


def generateGraph(file_path):
    # Load the data
    data = pd.read_csv(file_path, delimiter='\t')

    # Group the data by model and calculate the average time and validity checks
    grouped_data = data.groupby('model').agg({
        'time': 'mean',
        'valid_json': 'mean',
        'valid_wot': 'mean',
        'valid_mapping': 'mean',
        'mapping_fixable': 'mean',
        'valid_href': 'mean',
        'valid_param_dt': 'mean'
    }).reset_index()

    # Set up the matplotlib figure
    plt.figure(figsize=(12, 10))

    dt = file_path.split('/')[-1].split('.')[0].split('-')
    dt.pop(-1)
    dt = ' Prompt '.join(dt)
    plt.suptitle(f'Measurement {dt}', fontsize=20, fontweight='bold')

    # Plot the average time by model
    plt.subplot(2, 1, 1)
    sns.barplot(x='time', y='model', data=grouped_data, palette='viridis')
    plt.title('Average Time by Model')
    plt.xlabel('Average Time')
    plt.ylabel('Model')

    # Plot the validity checks by model
    validity_checks = ['valid_json', 'valid_wot', 'valid_mapping', 'mapping_fixable', 'valid_href', 'valid_param_dt']
    grouped_data_melted = pd.melt(grouped_data, id_vars='model', value_vars=validity_checks, var_name='Validity Check',
                                  value_name='Average Value')

    plt.subplot(2, 1, 2)
    sns.barplot(x='Average Value', y='model', hue='Validity Check', data=grouped_data_melted, palette='Set2')
    plt.title('Average Validity Checks by Model')
    plt.xlabel('Average Value')
    plt.ylabel('Model')

    plt.tight_layout()
    plt.savefig('.'.join(file_path.split('.')[:-1]) + '.png')
    # plt.show()


if __name__ == '__main__':

    validations = []

    dates = [f for f in os.listdir(f'./measurements') if os.path.isdir(f'./measurements/{f}')]

    reports = []

    for date in dates:
        filenames = os.listdir(f'./measurements/{date}')
        filenames = [f for f in filenames if f.startswith("17")]

        for filename in filenames:
            f = open(f'measurements/{date}/{filename}', 'r', encoding='utf8')
            ts = filename.split('_')[0]
            r = json.load(f)
            f.close()

            ## meta:
            ## 0: ["hm-rpc.0.0012999393BC4A", "Homematic radiator thermostat in living room"],
            ## 1: 0,        # promptIdx
            ## 2: "OpenAI"  # company
            ## 3: "gpt-3.5-turbo",  # model name
            ## 4: 10.143792700000631,   # time
            ## 5: RESPONSE              # content

            info = r[0]
            deviceId = info[0]
            description = info[1]
            promptIdx = r[1]
            company = r[2]
            model = r[3]
            time = r[4]
            response = r[5]

            groundTruth = None
            if deviceId in groundTruths:
                groundTruth = groundTruths[deviceId]
            else:
                with open(f'measurements/{deviceId}.json', 'r', encoding='utf8') as f:
                    groundTruth = json.load(f)
                    groundTruths[deviceId] = ThingDescription.from_json(json.dumps(groundTruth)).toDict()

            validation_single = {
                "valid_json": False,
                "valid_wot": False,
                "valid_mapping": False,
                "mapping_fixable": False,
                "mapping": {},
                "valid_href": False,
                "valid_param_dt": False,
                "hallucination_count": 0,
                "extra_output": False
            }

            print(f'➡️ {ts}, {model}')

            ## check metrics

            ## check JSON
            try:
                if '```' in response:
                    print(response)
                if '...' in response:
                    print(response)

                obj = json.loads(response)
                validation_single["valid_json"] = True

                actionsKey = ''
                eventsKey = ''
                propertiesKey = ''

                for k in obj.keys():
                    if k.lower().startswith('action'):
                        actionsKey = k
                    if k.lower().startswith('propert'):
                        propertiesKey = k
                    if k.lower().startswith('event'):
                        eventsKey = k

                if actionsKey != "actions":
                    if actionsKey == '':
                        print(f'\t⚙️ "actions" missing, fixing...')
                        obj["actions"] = {}
                    else:
                        print(f'\t⚙️ "actions" is named "{actionsKey}", fixing...')
                        obj["actions"] = obj[actionsKey]
                        del obj[actionsKey]

                if eventsKey != "events":
                    if eventsKey == '':
                        print(f'\t⚙️ "events" missing, fixing...')
                        obj["events"] = {}
                    else:
                        print(f'\t⚙️ "events" is named "{eventsKey}", fixing...')
                        obj["events"] = obj[eventsKey]
                        del obj[eventsKey]

                if propertiesKey != "properties":
                    if propertiesKey == '':
                        print(f'\t⚙️ "properties" missing, fixing...')
                        obj["properties"] = {}
                    else:
                        print(f'\t⚙️ "events" is named "{propertiesKey}", fixing...')
                        obj["properties"] = obj[propertiesKey]
                        del obj[propertiesKey]

                if "securityDefinitions" not in obj:
                    print(f'\t⚙️ Mandatory "securityDefinitions" missing. fixing...')
                    obj["securityDefinitions"] = {"nosec_sc": {"scheme": 'nosec'}}
                    obj["security"] = ['nosec_sc']

                ## check WoT validity
                desc = ThingDescription.from_json(json.dumps(obj))
                try:

                    desc.validate()
                    validation_single["valid_wot"] = True
                    print('\t✅ valid WoT')

                    # print(desc.toString())

                    if desc.id is None:
                        print('\t⚙️ ID missing, fixing...')
                        desc.id = deviceId
                    if desc.id != deviceId:
                        print('\t⚙️ ID malformed, fixing...')
                        desc.id = deviceId

                    try:
                        ## check properties/actions/events mapping

                        # print(groundTruth)
                        mapping = {
                            "missing_property": 0,
                            "missing_action": 0,
                            "missing_event": 0,
                            "malformed_property": 0,
                            "malformed_action": 0,
                            "malformed_event": 0,
                            "wrong_mapping": 0,
                            "justMalformed": False,
                            "justWrongMapping": False,
                        }
                        for property in groundTruth['properties'].keys():
                            found = False
                            for p in desc.properties.keys():
                                if p == property:
                                    found = True
                                    break
                                if p.endswith('.' + property):
                                    mapping["malformed_property"] += 1
                                    found = True
                                    break
                            for a in desc.actions.keys():
                                if a == property:
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                                if a.endswith('.' + property):
                                    mapping["malformed_action"] += 1
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                            for e in desc.events.keys():
                                if e == property:
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                                if e.endswith('.' + property):
                                    mapping["malformed_action"] += 1
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                            if not found:
                                mapping["missing_property"] += 1

                        for action in groundTruth['actions'].keys():
                            found = False
                            for a in desc.actions.keys():
                                if a == action:
                                    found = True
                                    break
                                if a.endswith('.' + action):
                                    mapping["malformed_action"] += 1
                                    found = True
                                    break
                            for p in desc.properties.keys():
                                if p == action:
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                                if p.endswith('.' + action):
                                    mapping["malformed_property"] += 1
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                            for e in desc.events.keys():
                                if e == action:
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                                if e.endswith('.' + action):
                                    mapping["malformed_action"] += 1
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                            if not found:
                                mapping["missing_action"] += 1

                        for event in groundTruth['events'].keys():
                            found = False
                            for e in desc.events.keys():
                                if e == event:
                                    found = True
                                    break
                                if e.endswith('.' + event):
                                    mapping["malformed_event"] += 1
                                    found = True
                                    break
                            for p in desc.properties.keys():
                                if p == event:
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                                if p.endswith('.' + event):
                                    mapping["malformed_property"] += 1
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                            for a in desc.actions.keys():
                                if a == event:
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                                if a.endswith('.' + event):
                                    mapping["malformed_action"] += 1
                                    mapping["wrong_mapping"] += 1
                                    found = True
                                    break
                            if not found:
                                mapping["missing_event"] += 1
                        valid = True
                        justMalformed = True
                        hasMalformed = False
                        justWrongMapping = True
                        hasWrongMapping = mapping["wrong_mapping"] > 0
                        missing = False
                        for k, v in mapping.items():
                            if v > 0:
                                valid = False
                            if k.startswith('missing') and v > 0:
                                justMalformed = False
                                missing = True
                                justWrongMapping = False
                            if k.startswith('malformed') and v > 0:
                                hasMalformed = True
                                justWrongMapping = False
                        if not hasMalformed:
                            justMalformed = False
                        if not hasWrongMapping:
                            justWrongMapping = False
                        validation_single["valid_mapping"] = valid
                        validation_single["mapping"] = mapping
                        mapping["justMalformed"] = justMalformed
                        mapping["justWrongMapping"] = justWrongMapping
                        continueTests = False
                        if valid:
                            print(f'\t✅ {model} for {deviceId}: mapping valid')
                            continueTests = True
                            validation_single["valid_mapping"] = True
                        if justWrongMapping or justMalformed:
                            if justMalformed:
                                print(f'\t⚙️ Malformed element ids, fixing...')
                                validation_single["valid_mapping"] = True
                                for k in list(desc.properties.keys()):
                                    v = desc.properties[k]
                                    k2 = k.split('.')[-1]
                                    desc.properties[k2] = v
                                    del desc.properties[k]
                                for k in list(desc.actions.keys()):
                                    v = desc.actions[k]
                                    k2 = k.split('.')[-1]
                                    desc.actions[k2] = v
                                    del desc.actions[k]
                                for k in list(desc.events.keys()):
                                    v = desc.events[k]
                                    k2 = k.split('.')[-1]
                                    desc.events[k2] = v
                                    del desc.events[k]

                            if justWrongMapping:
                                print(f'\t⚙️ False element mapping, fixing...')
                                validation_single["valid_mapping"] = False
                                validation_single["mapping_fixable"] = True
                                for k in list(desc.properties.keys()):
                                    v = desc.properties[k]
                                    op = v.forms[0].op
                                    if 'readproperty' in op and 'writeproperty' not in op:
                                        v.readOnly = True
                                    elif 'readproperty' not in op and 'writeproperty' in op:
                                        v.writeOnly = True

                                    if v.writeOnly and v.readOnly:
                                        raise Exception(f'\t\t🤖 {k}: readOnly and writeOnly simultanously')
                                    elif v.writeOnly:
                                        desc.actions[k] = ActionElement.from_json(v.toString())
                                        del desc.properties[k]
                                    elif v.readOnly:
                                        desc.events[k] = EventElement.from_json(v.toString())
                                        del desc.properties[k]

                            print(f'\t🆗 No property missing')
                            continueTests = True

                        if continueTests:
                            ## checking hrefs
                            hrefs = 0
                            malformedHref = 0
                            malformedHrefs = []
                            tsts = [desc.events, desc.properties, desc.actions]
                            for tst in tsts:
                                for id, elem in tst.items():
                                    for form in elem.forms:
                                        hrefs += 1
                                        if not form.href.startswith(desc.id):
                                            malformedHref += 1
                                            malformedHrefs.append((form.href, f'{desc.id}.{id}'))
                            if malformedHref == 0:
                                print(f'\t✅ hrefs valid: {hrefs}/{hrefs}')

                                validation_single["valid_href"] = True

                                ## checking property datatype vars

                                tsts = ["properties", "actions", "events"]

                                params_valid = True
                                for tst in tsts:
                                    for g_id, g_elem in groundTruth[tst].items():
                                        try:
                                            elem = desc.toDict()[tst][g_id]
                                            # print(list(g_elem.keys()))
                                            blacklist = ['description', '@type', 'forms', 'title', 'observable', 'data',
                                                         'dataResponse', 'input', 'output']
                                            if tst == 'actions':
                                                blacklist.append('readOnly')
                                            elif tst == 'events':
                                                blacklist.append('writeOnly')
                                            else:
                                                blacklist.append('readOnly')
                                                blacklist.append('writeOnly')
                                            for k in list(g_elem.keys()):
                                                if k not in blacklist:
                                                    if k in elem and elem[k] != g_elem[k]:
                                                        print(
                                                            f'\t\t🔥 {tst} values for {g_id} "{k}" differ: {elem[k]} != {g_elem[k]}')
                                                        params_valid = False
                                                    elif k not in elem:
                                                        print(
                                                            f'\t\t🔥 {tst} value for {g_id} "{k}" missing: {g_elem[k]}')
                                                        params_valid = False
                                        except Exception as e:
                                            print(f'{g_id} not in {tst} of {desc.id}')
                                            params_valid = False
                                            print(desc.toDict()[tst])

                                        # print([k for k in list(elem.toDict().keys()) if elem.toDict()[k] is not None])
                                validation_single["valid_param_dt"] = params_valid
                            else:
                                validation_single['malformed_hrefs'] = malformedHrefs
                                print(f'\t💀 malformed hrefs: {malformedHref}/{hrefs}')
                                validation_single["malformedHrefs"] = True

                        else:
                            if missing:
                                print(f'\t💀 some properties missing')
                                validation_single["propertiesMissing"] = True
                            print(f'\t💀 invalid property translation')

                    except Exception as e:
                        if str(e).startswith('\t\t🤖'):
                            raise e
                        else:
                            print(e)
                            print(f'\t👽 currently unknown error ⚡')
                            # print(json.dumps(obj, indent=2))

                except Exception as e:
                    print(f'\t💀 invalid WoT')
                    if str(e).startswith("'observeproperty' is not one of"):
                        print(f'\t\t🤖 Wrong property definition: observeproperty')
                        validation_single["wrongEnumValue"] = True
                    elif str(e).startswith("[] should be non-empty"):
                        print(f'\t\t🤖 Forms attribute missing, href was put in property body directly.')
                        validation_single["formsMissing"] = True
                    elif "is not one of" in str(e):
                        print(f'\t\t🤖 Usage of wrong attribute value in enum')
                        validation_single["wrongEnumValue"] = True
                    elif str(e).startswith('\t\t🤖'):
                        print(str(e))
                        validation_single["readWriteMutex"] = True
                    else:
                        print(e)
                        # print(json.dumps(obj, indent=2))


            except Exception as e:
                print(f'\t💀 invalid JSON')
                if (str(e).startswith('Unterminated string') or str(e).startswith('Expecting property name')
                        or str(e).startswith("Expecting ',' delimiter") or str(e).startswith("Expecting value")):
                    print(f'\t\t🤖 Output invalid, incorrect concatenation.')
                    # print(response)
                    validation_single["tokenOverflow"] = True
                elif str(e).startswith('Extra data:'):
                    print(f'\t\t🤖 Model made response formatting attempt with ```')
                    validation_single["extraData"] = True
                elif str(e).startswith("'list' object has no attribute"):
                    print(f'\t\t🤖 Properties generated as lists instead of objects, valid JSON but invalid WoT')
                    validation_single["listForObjError"] = True
                elif str(e).startswith("Invalid control character"):
                    print(f'\t\t🤖 Model tried to stop by ellipse "..."')
                    validation_single["ellipse"] = True
                else:
                    print(e)
                    # print(response)

                # print('Invalid JSON: '+response)

            if len(r) == 7:
                r[6] = validation_single
            else:
                r.append(validation_single)

            ## 0: ["hm-rpc.0.0012999393BC4A", "Homematic radiator thermostat in living room"],
            ## 1: 0,        # promptIdx
            ## 2: "OpenAI"  # company
            ## 3: "gpt-3.5-turbo",  # model name
            ## 4: 10.143792700000631,   # time
            ## 5: RESPONSE              # content
            ## 6: validation_single

            ks = ["model", "prompt", "time"]
            vs = [r[2] + '_' + r[3], r[1], round(r[4])]
            first = True
            keysw = ['valid_json', 'valid_wot', 'valid_mapping', 'mapping_fixable', 'valid_href', 'valid_param_dt',
                     'hallucination_count', 'extra_output']
            for k in keysw:
                v = validation_single[k]
                ks.append(k)
                vs.append(v)
            if len(validations) == 0:
                validations.append(ks)
            validations.append(vs)

            with open(f'measurements/{date}/{filename}', 'w', encoding='utf8') as f:
                f.write(json.dumps(r))

        # print(validations)

        csv = '\n'.join(['\t'.join([str(s) for s in line]) for line in validations])
        with open(f'measurements/{date}-validation.csv', 'w', encoding='utf8') as f:
            f.write(csv)
        print(date)
        generateGraph(f'measurements/{date}-validation.csv')
        reports.append(f'measurements/{date}-validation.csv')

    files = [pd.read_csv(f, sep='\t') for f in reports]
    for i in range(len(files)):
        filename = reports[i]
        f = files[i]
        f["Prompt"] = filename.split('-')[1]

    combined_df = pd.concat(files, ignore_index=True)
    combined_df[['valid_json', 'valid_wot', 'valid_mapping', 'mapping_fixable', 'valid_href', 'valid_param_dt',
                 'hallucination_count']] = combined_df[
        ['valid_json', 'valid_wot', 'valid_mapping', 'mapping_fixable', 'valid_href', 'valid_param_dt',
         'hallucination_count']
    ].apply(pd.to_numeric, errors='coerce')

    mean_validations_updated = combined_df.groupby(['model', 'Prompt']).mean().reset_index()

    metrics = ['valid_json', 'valid_wot', 'valid_mapping', 'mapping_fixable', 'valid_href', 'valid_param_dt']
    plt.figure(figsize=(16, 12))

    # Create a bar plot for each validation metric
    for i, metric in enumerate(metrics):
        plt.subplot(3, 2, i + 1)
        sns.barplot(data=mean_validations_updated, x='Prompt', y=metric, hue='model')
        plt.title(f'Average {metric.replace("_", " ").title()} Success Rate by Model and Prompt')
        plt.ylabel('Success Rate')
        plt.xlabel('Prompt')
        plt.ylim(0, 1)

    # Adjust the legend
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.gcf().legend(handles, labels, loc='lower center', ncol=len(labels) // 2)

    # Remove legends from individual plots
    for ax in plt.gcf().axes:
        ax.get_legend().remove()

    plt.tight_layout(rect=[0, 0.1, 1, 1])  # Adjust layout to make space for the legend at the bottom
    plt.savefig('measurements/completeReport.png')
    plt.show()
