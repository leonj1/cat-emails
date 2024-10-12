import ell
import openai

ell.init(verbose=True, store='./logdir')

client = openai.Client(
    base_url="http://10.1.1.144:11434/v1", api_key="ollama"  # required but not used
)

@ell.simple(model="llama3.2:latest", temperature=0.5, client=client)
def categorize_email(contents: str):
    """
    You do not want people trying to sell you things.
    You do not want to spend money.
    You categorize emails into one of the following categories: 
    'Wants-Money', 'Marketing', 'Personal', 'Financial-Notification', 'Appointment-Reminder', 'Service-Updates', 'Work-related'.
    """
    return f"Categorize this email. You are limited into one of the categories. Maximum length of response is 2 words: {contents}"

contents = """

Your next adventure is waiting, and Hemispheres can help you make it happen.
 
With Hemispheres®, get expert travel advice and insider recommendations for hotels, food, activities and more at your favorite United destinations. Our Three Perfect Days® feature even offers curated itineraries to make the most of your trip, no matter how much time you have.

Once you’ve imagined the perfect trip, book your flight on United and make it a reality.
"""

category = categorize_email(contents)
print(category)
