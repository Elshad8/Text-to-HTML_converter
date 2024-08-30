import openai
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv
import os
import base64
from PIL import Image
import io
import requests 

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
openai.api_key = os.getenv('API_KEY')

async def generate_and_add_image(html_content, description):
    # Refine the description to ensure it's a background image without text
    refined_description = f"{description}, abstract, pattern, or nature-inspired background, without any text, buttons, or logos"
    try:
        # Generate an image using OpenAI's DALL-E 3
        response = openai.Image.create(
            model="dall-e-3",
            prompt=refined_description,
            size="1024x1792",
            n=1
        )
        image_url = response['data'][0]['url']  # Adjust based on actual API response

        # Embed the image into the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        if soup.body:
            style_tag = soup.new_tag('style')
            style_tag.string = f'body {{ background-image: url("{image_url}"); background-size: cover; background-repeat: no-repeat; }}'
            soup.head.append(style_tag)
        return str(soup)
    except Exception as e:
        print(f"Failed to generate image: {str(e)}")
        # Return original HTML if image generation fails
        return html_content

def make_elements_editable(soup):
    # Apply contenteditable to standard editable elements
    for element in soup.find_all(['td', 'th','label', 'button', 'select', 'option', 'textarea','table']):
        element['contenteditable'] = "true"
    
    # For inputs, wrap them in a div with contenteditable
    for input_elem in soup.find_all(['input', 'select', 'button']):
        wrapper = soup.new_tag('div', contenteditable="true")
        input_elem.wrap(wrapper)

async def generate_html(prompt):
    try:

        modified_prompt = (
            f"{prompt}\n\n"
            "Please ensure that the generated HTML structure has a single wrapper div with the class generated-content "
            "that covers the full width and height of the viewport, with no gaps on the sides or top and bottom. Inside this wrapper, one more generated-content div class should not exist. "
            "Avoid adding extra unnecessary wrapper divs."
        )
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that generates clean, well-structured HTML code based on user instructions."},
                {"role": "user", "content": modified_prompt},
            ],
            max_tokens=3000,
            temperature=0.8
        )
        html_content = response['choices'][0]['message']['content']
        
        # Parse and prettify HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        make_elements_editable(soup)

        # Add responsive CSS
        style_tag = soup.new_tag('style')
        style_tag.string = """
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
            }
            .generated-content {
                width: 100%;
                height: 100%;
                box-sizing: border-box;
                background-color: rgba(255, 255, 255, 0.2);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 20px;
                margin: 0;
                text-align: center;
                position: relative;
                flex-grow: 1;
            }
            .generated-content img {
                max-width: 100%;
                height: auto;
            }
            .generated-content select, .generated-content input, .generated-content button {
                pointer-events: auto; /* Ensure elements remain interactive */
            }
        """

        

        if soup.head:
            soup.head.append(style_tag)
        else:
            head_tag = soup.new_tag('head')
            head_tag.append(style_tag)
            soup.insert(0, head_tag)
        
        
        
       # Wrap content in a div with the class generated-content
        if soup.body:
            wrapper = soup.new_tag('div', **{'class': 'generated-content'})
            for element in soup.body.contents:
                wrapper.append(element.extract())
            soup.body.append(wrapper)
        
        pretty_html = soup.prettify()
        
        return pretty_html
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        raise


async def apply_html_changes(html_content, change_instruction):
    try:
        # Construct the prompt for making changes
        prompt = f"""
Here is the HTML content:
{html_content}

Note: The HTML contains a background image set via CSS in the <head> tag. Please ignore any styles related to the background image and focus on modifying the content within the body as specified below.

Example changes:
- "Change the color of the RSVP button to blue" should change the color attribute of the button to blue.
- "Add a new checkbox labeled 'I agree' below the last paragraph" should add a checkbox without removing any elements.

Requested change:
{change_instruction}
"""


        # Request the modification
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that modifies HTML code based on user instructions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=2000,
        )
        modified_html = response['choices'][0]['message']['content']
        
        # Parse and prettify HTML
        soup = BeautifulSoup(modified_html, 'html.parser')

        make_elements_editable(soup)
        
        pretty_html = soup.prettify()
        
        return pretty_html
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        raise



async def analyze_image_with_gpt4o(image_bytes):
    try:
        # Convert image bytes to a base64 encoded string
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Setup the request to OpenAI's GPT model with vision capabilities
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What’s in this image?"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }
        
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            raise Exception("Failed to analyze image: " + response.text)
    except Exception as e:
        print(f"Failed to analyze image with GPT-4o: {str(e)}")
        return None



async def generate_html_from_description(description):
    try:
        # Enhanced prompt for detailed HTML generation
        prompt = (
            "You are an assistant that generates HTML code based on image descriptions. "
            "Please create a visually appealing HTML template that closely matches the style (most importantly colors of the elements) and elements described. "
            "The template should use a full-width layout, include prominent use of the dominant colors, "
            "and feature any specific elements like borders or icons as described in: {description}"
            "Please ensure that the generated HTML structure has a single wrapper div with the class generated-content "
            "that covers the full width and height of the viewport, with no gaps on the sides or top and bottom. Inside this wrapper, one more generated-content div class should not exist. "
            "Avoid adding extra unnecessary wrapper divs."
        ).format(description=description)  # Dynamically inserting the description

        # Making the API call to OpenAI's GPT model
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an assistant that generates responsive HTML code."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.8
        )
        
        # Extracting the generated HTML content
        html_content = response['choices'][0]['message']['content']
        
        # Parse and prettify HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        make_elements_editable(soup)

        # Add responsive CSS
        style_tag = soup.new_tag('style')
        style_tag.string = """
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
                display: flex;
                justify-content: center;
                align-items: center;
                flex-direction: column;
            }
            .generated-content {
                width: 100%;
                height: 100%;
                box-sizing: border-box;
                background-color: rgba(255, 255, 255, 0.2);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 20px;
                margin: 0;
                text-align: center;
                position: relative;
                flex-grow: 1;
            }
            .generated-content img {
                max-width: 100%;
                height: auto;
            }
            .generated-content select, .generated-content input, .generated-content button {
                pointer-events: auto; /* Ensure elements remain interactive */
            }
        """

        

        if soup.head:
            soup.head.append(style_tag)
        else:
            head_tag = soup.new_tag('head')
            head_tag.append(style_tag)
            soup.insert(0, head_tag)
        
        
        
       # Wrap content in a div with the class generated-content
        if soup.body:
            wrapper = soup.new_tag('div', **{'class': 'generated-content'})
            for element in soup.body.contents:
                wrapper.append(element.extract())
            soup.body.append(wrapper)
        
        pretty_html = soup.prettify()
        
        return pretty_html
    except openai.error.OpenAIError as e:
        logging.error(f"OpenAI API error: {e}")
        raise

def add_custom_styling(soup):
    # Adding custom styles to enhance the appearance and layout of the generated HTML
    style_tag = soup.new_tag('style')
    style_tag.string = """
        html, body { height: 100%; margin: 0; padding: 0; overflow: hidden; }
        .generated-content { 
            width: 100%; 
            height: 100%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            flex-direction: column;
        }
    """
    if soup.head:
        soup.head.append(style_tag)
    else:
        head_tag = soup.new_tag('head')
        head_tag.append(style_tag)
        soup.insert(0, head_tag)
    # Additional CSS rules can be added here as necessary
    



async def generate_html_from_image(image_data):
    # Decode the base64 image data to bytes
    image_bytes = base64.b64decode(image_data)

    # Step 1: Use GPT-4o to analyze the image and get a description
    description = await analyze_image_with_gpt4o(image_bytes)
    if description:
        # Step 2: Use GPT-4 to generate HTML from the description
        html_content = await generate_html(description)
        return html_content
    else:
        return "<div>Failed to generate HTML: Image analysis failed.</div>"
