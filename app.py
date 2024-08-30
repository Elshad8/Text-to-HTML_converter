from quart import Quart, request, jsonify, render_template
from generators import generate_html, apply_html_changes, generate_and_add_image, generate_html_from_image

app = Quart(__name__)
conversations = {}

@app.route('/')
async def index():
    return await render_template('index.html')

@app.route('/generate-html', methods=['POST'])
async def generate_html_endpoint():
    data = await request.get_json()
    prompt = data.get('instruction')
    add_image = data.get('addImage', False)  # Default to False if not provided
    conversation_id = data.get('conversation_id')
    
    if conversation_id not in conversations:
        html_content = await generate_html(prompt)
        if add_image:
            html_content = await generate_and_add_image(html_content, prompt)
        conversations[conversation_id] = {
            'name': prompt.split('.')[0][:50],
            'original_prompt': prompt,  # Store the original prompt here
            'content': [html_content]
        }
    else:
        # Existing conversation, apply changes
        change_instruction = prompt
        current_html = conversations[conversation_id]['content'][-1]
        html_content = await apply_html_changes(current_html, change_instruction)
        conversations[conversation_id]['content'].append(html_content)
    
    return jsonify({'html': html_content})

@app.route('/save-html', methods=['POST'])
async def save_html():
    data = await request.get_json()
    html_content = data.get('html_content')
    conversation_id = data.get('conversation_id')
    
    if conversation_id in conversations:
        conversations[conversation_id]['content'].append(html_content)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'failed', 'reason': 'Invalid conversation ID'})

@app.route('/get-conversation', methods=['GET'])
async def get_conversation():
    conversation_id = request.args.get('conversation_id')
    html_content = conversations.get(conversation_id, {}).get('content', [])
    return jsonify({'html': "".join(html_content)})

@app.route('/get-conversations', methods=['GET'])
async def get_conversations():
    return jsonify({
        'conversations': [
            {'id': convo_id, 'name': convo['name']}
            for convo_id, convo in conversations.items()
        ]
    })

@app.route('/reset-template', methods=['POST'])
async def reset_template():
    # Clear any server-side conversation or state if needed
    # This might involve clearing some session or in-memory state
    return jsonify({"status": "reset successful"})

@app.route('/undo', methods=['POST'])
async def undo():
    data = await request.get_json()
    conversation_id = data.get('conversation_id')
    
    if conversation_id in conversations and len(conversations[conversation_id]['content']) > 1:
        conversations[conversation_id]['content'].pop()
        html_content = conversations[conversation_id]['content'][-1]
    else:
        html_content = ''
        conversations.pop(conversation_id, None)
    
    return jsonify({'html': html_content})

@app.route('/image-to-html', methods=['POST'])
async def image_to_html():
    data = await request.get_json()
    image_data = data.get('image')  # Assuming the image is sent as a base64 string
    conversation_id = data.get('conversation_id')  # You need to ensure the front end sends this ID
    
    # Generate HTML from the image data
    html_content = await generate_html_from_image(image_data)
    
    if conversation_id not in conversations:
        # Start a new conversation if it doesn't exist
        conversations[conversation_id] = {
            'name': 'Generated from image',
            'content': [html_content]
        }
    else:
        # If conversation already exists, this is treated as a change request
        current_html = conversations[conversation_id]['content'][-1]
        html_content = await apply_html_changes(current_html, html_content)  # Optionally handle changes if needed
        conversations[conversation_id]['content'].append(html_content)
    
    return jsonify({'html': html_content})



@app.route('/regenerate-image', methods=['POST'])
async def regenerate_image():
    data = await request.get_json()
    add_image = data.get('addImage', True)
    conversation_id = data.get('conversation_id')

    if conversation_id in conversations:
        current_html = conversations[conversation_id]['content'][-1]
        original_prompt = conversations[conversation_id]['original_prompt']
        if add_image:
            # Re-generate and replace the background image
            current_html = await generate_and_add_image(current_html, original_prompt)
        conversations[conversation_id]['content'][-1] = current_html  # Replace the last entry
        return jsonify({'html': current_html})
    return jsonify({'status': 'failed', 'reason': 'No existing template to modify'})



if __name__ == '__main__':
    from hypercorn.config import Config
    from hypercorn.asyncio import serve

    config = Config()
    config.bind = ["127.0.0.1:5000"]

    import asyncio
    asyncio.run(serve(app, config))