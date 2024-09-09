schema = open('wotv1.1.json', 'r').read()


class PROMPTS:
    basic = ('Translate this object properties of a IOT device '
             'into a valid Web of Things "Thing Description". '
             'Intelligently select the title of the Thing from the data. '
             'Do not output any other text. '
             'Do not format the JSON output with indents or line breaks. '
             'Do not prepend "```json" at the beginning or "```" at the end of the JSON. '
             'Just use Information you find in the following json object. '
             'Do not invent or assume any other information than the given. '
             'Do not format the JSON output with indents or line breaks. '
             'When you need to build a "href" property, use the object\'s key '
             'or _id as the url for the corresponding event, action or property. '
             'Sort the elements into properties, events and action lists like: '
             '"properties" for read/write elements, '
             '"events" for read only elements, '
             '"actions" for write only elements.'
             'It is mandatory to sort the elements like this. '
             'Usage of tabs, \\t, line breaks, carriage returns, \\r and \\n are strictly prohibited! '
             '\n\nThis is the JSON object you need to translate into things description:\n\n')

    V2 = (
        'Translate the provided JSON object properties of an IoT device into a valid Web of Things "Thing Description".\n'
        'Instructions:\n'
        '- Select an appropriate title for the Thing based on the data.\n'
        '- Output only JSON without any additional text, indents, line breaks, or formatting markers (e.g., no ```json).\n'
        '- Use only the information present in the provided JSON; do not assume or invent details.\n'
        '- For "href" properties, utilize the object\'s key or _id as the URL for corresponding events, actions, or properties.\n'
        '- Categorize elements into three lists:\n'
        '    - "properties" for read/write elements\n'
        '    - "events" for read-only elements\n'
        '    - "actions" for write-only elements\n'
        '- It\'s mandatory to sort elements as specified.\n'
        '- Avoid using tabs, line breaks, carriage returns, or any form of whitespace formatting.\n'
        'When the response is running into token limit, end your response with "TOKEN LIMIT REACHED"\n\
        JSON Object to translate:\n\n')

    V3 = (
        'Translate the provided JSON object properties of an IoT device into a valid Web of Things "Thing Description":\n'
        'Instructions:\n'
        '- Accurately derive an appropriate "title" for the Thing based exclusively on the data provided. '
        'Assumptions or additional context should not be introduced.\n'
        '- Your output must consist solely of valid JSON without any supplementary text, commentary, '
        'formatting artifacts (such as ```json), or extraneous characters like indents, newlines, tabs, or spaces.\n'
        '- No assumptions or guesswork about data types, URLs, or semantics. Only use explicitly provided information from the JSON.\n'
        '- For "href" properties, strictly derive the URL using the object\'s key or _id as the base reference.\n'
        '- Organize properties into the required three categories:\n'
        ' - "properties": These must be read/write properties.\n'
        ' - "events": These must be strictly read-only.\n'
        ' - "actions": These must be strictly write-only.\n'
        '- Properties must adhere exactly to parameter specifications (e.g., min/max values, units, data types) as provided in the JSON schema.\n'
        '- There must be no formatting irregularities such as unnecessary whitespace, line breaks, or missing fields in the JSON response.\n'
        '- Do not abbreviate or truncate any parts of the output, including with ellipses ("..."). Ensure full, continuous output.\n'
        '- If the response is nearing token capacity, halt and finalize your response with the explicit text "TOKEN LIMIT REACHED".\n'
        'JSON Object to translate:\n\n')
