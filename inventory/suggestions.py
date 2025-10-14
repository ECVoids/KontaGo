import os
from openai import OpenAI
import json
from dotenv import load_dotenv, find_dotenv

_ = load_dotenv('openAI.env')
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get('openAI_api_key'),
)

def assign_suggestions(product_name, product_category, product_description, model="gpt-4o-mini"):
    
    prompt = f"""Given the product information below, provide detailed suggestions for proper handling, storage, and maintenance. Include recommendations for packaging, transportation, safety precautions, and any other relevant handling procedures.

        Product Name: {product_name}
        Category: {product_category}
        Description: {product_description}
                
    Please focus on ensuring product integrity during handling, complying with relevant safety standards, and optimizing efficiency in logistics and storage. The answer must not have more than 300 words."""
    
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature = 0,
        max_tokens = 500,
    )
    return response.choices[0].message.content
    
def suggest_price(product_name, product_category, product_description, model="gpt-4o-mini"):
    
    prompt = f"""Given the product information below, provide a price suggestion in COP as the currency, consider similar products in this category and description to suggest a price. The suggested price should reflect current market conditions in Colombia while remaining logical for the product's characteristics.

        Product Name: {product_name}
        Category: {product_category}
        Description: {product_description}
                
        Please consider factors such as brand reputation, quality, and product features when suggesting a price. The answer must be just the price suggested without symbols or another information."""
    
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature = 0.6,
        max_tokens = 500,
    )
    return response.choices[0].message.content