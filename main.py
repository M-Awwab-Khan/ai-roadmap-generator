import streamlit as st
from groq import Groq
from markdown_pdf import MarkdownPdf, Section
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit_authenticator as stauth

if not firebase_admin._apps:
    cred = credentials.Certificate("ai-roadmap-generator-f6570-firebase-adminsdk-kaovf-55e381062a.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Initialize the Groq client
client = Groq(
    api_key=st.secrets["GROQ_API_KEY"],
)

hashed_passwords = stauth.Hasher.hash_passwords({
            "usernames": {
                "admin": {
                    "name": "Admin User",
                    "password": "admin",
                    "email": "admin@example.com"
                }
            },
            "cookie": {
                "expiry_days": 1,
                "key": "asdfjksdf"
            },
            "preauthorized": {
                "emails": ["admin@example.com"]
            }
})


authenticator = stauth.Authenticate(hashed_passwords, "aksjdfl;", "aksjdfkla")

def generate_roadmap(user_input):
    prompt = f"Generate a comprehensive roadmap for learning {user_input['skill']} in {user_input['duration']} months. Divide the topics in weeks. Make sure you include projects."
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gemma2-9b-it",
    )
    return chat_completion.choices[0].message.content

def save_to_pdf(content):
    pdf = MarkdownPdf(toc_level=1)
    pdf.add_section(Section(content))

    pdf.save("roadmap.pdf")


    # Read the file into a BytesIO buffer
    buffer = BytesIO()
    with open("roadmap.pdf", "rb") as f:
        buffer.write(f.read())

    buffer.seek(0)
    return buffer

def save_roadmap_to_db(user_email, skill, roadmap):
    doc_ref = db.collection('users').document(user_email).collection('roadmaps').document()
    doc_ref.set({
        'skill': skill,
        'roadmap': roadmap,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

def load_roadmaps(user_email):
    roadmaps = []
    docs = db.collection('users').document(user_email).collection('roadmaps').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    for doc in docs:
        roadmaps.append({
            'id': doc.id,
            'skill': doc.get('skill'),
            'roadmap': doc.get('roadmap'),
            'timestamp': doc.get('timestamp').strftime("%Y-%m-%d %H:%M:%S")
        })
    return roadmaps

name, authentication_status, username = authenticator.login("main")



if authentication_status:
    st.sidebar.title('AI Roadmap Generator')
    skill = st.sidebar.text_input("Which skill do you want to learn? ")
    duration = st.sidebar.number_input("Months", step = 1)

    if st.sidebar.button("Generate Roadmap"):
        user_input = {
            "skill": skill,
            "duration": int(duration)
        }
        roadmap = generate_roadmap(user_input)
        # st.markdown(roadmap)

        # Save the roadmap to PDF
        pdf_buffer = save_to_pdf(roadmap)

        st.download_button(
            label="Download Roadmap as PDF",
            data=pdf_buffer,
            file_name=f"{skill}_roadmap.pdf",
            mime="application/pdf"
        )

        # Save roadmap to Firestore
        save_roadmap_to_db(username, skill, roadmap)

    roadmaps = load_roadmaps(username)

    roadmap_options = {f"{rm['timestamp']} - {rm['skill']}": rm['id'] for rm in roadmaps}
    selected_roadmap_id = st.sidebar.selectbox("Select a roadmap to view", options=list(roadmap_options.keys()))

    if selected_roadmap_id:
        selected_roadmap = next(rm for rm in roadmaps if rm['id'] == roadmap_options[selected_roadmap_id])

        # Save the roadmap to PDF
        pdf_buffer = save_to_pdf(selected_roadmap['roadmap'])

        st.download_button(
            label="Download Roadmap as PDF",
            data=pdf_buffer,
            file_name=f"{selected_roadmap['skill']}_roadmap.pdf",
            mime="application/pdf"
        )
        st.markdown(selected_roadmap['roadmap'])

    authenticator.logout("Logout", "sidebar")

elif authentication_status == False:
    st.error("Username/password is incorrect")

elif authentication_status == None:
    st.warning("Please enter your username and password")
