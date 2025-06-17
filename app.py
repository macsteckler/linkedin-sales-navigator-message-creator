import streamlit as st
import openai
import os
from typing import Dict, Any, List
import hashlib
from datetime import datetime
import hubspot
from hubspot.crm.contacts import SimplePublicObjectInputForCreate, ApiException
from hubspot.crm.contacts.models import SimplePublicObjectInput
from hubspot.crm.objects.notes import SimplePublicObjectInputForCreate as NotesSimplePublicObjectInputForCreate
from hubspot.crm.objects.notes.models import SimplePublicObjectInput as NotesSimplePublicObjectInput
import requests

# Set page config
st.set_page_config(
    page_title="LinkedIn Sales Navigator Message Creator",
    page_icon="📧",
    layout="wide"
)

# Initialize session state for prompts if not exists
def initialize_prompts():
    """Initialize prompts in session state if they don't exist"""
    if "prompts" not in st.session_state:
        st.session_state.prompts = {
            "Cold Outreach": {
                "system_prompt": "You are a sales expert creating personalized cold outreach messages for LinkedIn Sales Navigator. Create engaging, professional messages that grab attention.",
                "user_prompt": """Create a LinkedIn message for:
Name: {name}
Title: {title}
Company: {company}

Generate:
1. A compelling subject line (5-8 words)
2. A personalized message body (2-3 sentences, professional but friendly)

Focus on: Building initial connection and sparking interest.""",
                "model": "gpt-3.5-turbo"
            },
            
            "Follow-up": {
                "system_prompt": "You are a sales expert creating follow-up messages for LinkedIn Sales Navigator. Create messages that re-engage prospects professionally.",
                "user_prompt": """Create a LinkedIn follow-up message for:
Name: {name}
Title: {title}
Company: {company}

Generate:
1. A compelling subject line (5-8 words)
2. A follow-up message body (2-3 sentences, acknowledging previous contact)

Focus on: Re-engaging and providing value.""",
                "model": "gpt-3.5-turbo"
            },
            
            "Product Demo": {
                "system_prompt": "You are a sales expert creating product demonstration invitation messages for LinkedIn Sales Navigator. Create messages that showcase value proposition.",
                "user_prompt": """Create a LinkedIn product demo invitation for:
Name: {name}
Title: {title}
Company: {company}

Generate:
1. A compelling subject line (5-8 words)
2. A demo invitation message body (2-3 sentences, highlighting benefits)

Focus on: Demonstrating product value and scheduling demo.""",
                "model": "gpt-3.5-turbo"
            },
            
            "Partnership": {
                "system_prompt": "You are a sales expert creating partnership opportunity messages for LinkedIn Sales Navigator. Create messages that propose mutual business benefits.",
                "user_prompt": """Create a LinkedIn partnership message for:
Name: {name}
Title: {title}
Company: {company}

Generate:
1. A compelling subject line (5-8 words)
2. A partnership proposal message body (2-3 sentences, highlighting mutual benefits)

Focus on: Proposing strategic partnership opportunities.""",
                "model": "gpt-3.5-turbo"
            }
        }

# Initialize prompts on app start
initialize_prompts()

# Available OpenAI models
AVAILABLE_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo-preview",
    "gpt-4o",
    "gpt-4o-mini"
]

# Initialize HubSpot client
@st.cache_resource
def get_hubspot_client():
    """Initialize and cache HubSpot client"""
    try:
        api_key = st.secrets.get("hubspot_api_key", "")
        if not api_key or api_key == "your-hubspot-api-key-here":
            return None
        return hubspot.Client.create(access_token=api_key)
    except Exception as e:
        st.error(f"HubSpot connection error: {str(e)}")
        return None

# HubSpot CRM Functions
def create_hubspot_contact(name: str, title: str, company: str, pitch_type: str, message_subject: str, message_body: str):
    """Create a contact and lead in HubSpot CRM with association"""
    client = get_hubspot_client()
    if not client:
        return None
    
    try:
        # Parse first and last name
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Create contact properties - using only standard HubSpot properties
        contact_properties = {
            "firstname": first_name,
            "lastname": last_name,
            "jobtitle": title,
            "company": company,
            "lifecyclestage": "lead",
            "hs_lead_status": "NEW"  # Standard HubSpot lead status property
        }
        
        # Create the contact first
        simple_public_object_input_for_create = SimplePublicObjectInputForCreate(properties=contact_properties)
        contact_response = client.crm.contacts.basic_api.create(simple_public_object_input_for_create=simple_public_object_input_for_create)
        contact_id = contact_response.id
        
        # Create lead properties - using only standard properties
        lead_properties = {
            "firstname": first_name,
            "lastname": last_name,
            "jobtitle": title,
            "company": company,
            "hs_lead_status": "NEW"  # Standard property
        }
        
        # Add custom properties only if they might exist (with error handling)
        try:
            lead_properties.update({
                "pitch_type": pitch_type,
                "last_message_subject": message_subject,
                "last_message_body": message_body
            })
        except:
            # If custom properties fail, continue without them
            pass
        
        # Create the lead using direct API call
        lead_url = "https://api.hubapi.com/crm/v3/objects/leads"
        headers = {
            "Authorization": f"Bearer {st.secrets.get('hubspot_api_key')}",
            "Content-Type": "application/json"
        }
        
        lead_payload = {
            "properties": lead_properties
        }
        
        lead_response = requests.post(lead_url, json=lead_payload, headers=headers)
        
        if lead_response.status_code == 201:
            lead_id = lead_response.json().get('id')
            
            # Associate lead with contact
            association_url = f"https://api.hubapi.com/crm/v3/objects/leads/{lead_id}/associations/contacts/{contact_id}/lead_to_contact"
            association_response = requests.put(association_url, headers=headers)
            
            if association_response.status_code == 200:
                return {
                    "contact_id": contact_id,
                    "lead_id": lead_id,
                    "status": "success"
                }
            else:
                # Contact and lead created but association failed
                return {
                    "contact_id": contact_id,
                    "lead_id": lead_id,
                    "status": "association_failed"
                }
        else:
            # Contact created but lead creation failed
            st.warning(f"Lead creation failed: {lead_response.text}")
            return {
                "contact_id": contact_id,
                "lead_id": None,
                "status": "lead_creation_failed"
            }
        
    except ApiException as e:
        if "Contact already exists" in str(e) or "DUPLICATE_VALUE" in str(e):
            # Try to find and update existing contact
            return update_existing_contact(name, title, company, pitch_type, message_subject, message_body)
        else:
            st.error(f"Error creating HubSpot contact: {str(e)}")
            return None
    except Exception as e:
        st.error(f"Error creating HubSpot records: {str(e)}")
        return None

def update_existing_contact(name: str, title: str, company: str, pitch_type: str, message_subject: str, message_body: str):
    """Update existing contact and create/update associated lead"""
    client = get_hubspot_client()
    if not client:
        return None
        
    try:
        # Search for existing contact by name
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Search contacts
        search_request = {
            "query": f"{first_name} {last_name}",
            "limit": 10,
            "after": 0,
            "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
            "properties": ["firstname", "lastname", "company", "jobtitle"],
            "filterGroups": []
        }
        
        search_response = client.crm.contacts.search_api.do_search(public_object_search_request=search_request)
        
        if search_response.results:
            contact_id = search_response.results[0].id
            
            # Update contact with new info - using only standard properties
            contact_properties = {
                "jobtitle": title,
                "company": company,
                "hs_lead_status": "CONTACTED",
                "last_contact_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            simple_public_object_input = SimplePublicObjectInput(properties=contact_properties)
            client.crm.contacts.basic_api.update(contact_id=contact_id, simple_public_object_input=simple_public_object_input)
            
            # Create or update lead - using only standard properties
            lead_properties = {
                "firstname": first_name,
                "lastname": last_name,
                "jobtitle": title,
                "company": company,
                "hs_lead_status": "CONTACTED"
            }
            
            # Add custom properties with error handling
            try:
                lead_properties.update({
                    "pitch_type": pitch_type,
                    "last_message_subject": message_subject,
                    "last_message_body": message_body
                })
            except:
                pass
            
            # Create new lead for this contact interaction
            lead_url = "https://api.hubapi.com/crm/v3/objects/leads"
            headers = {
                "Authorization": f"Bearer {st.secrets.get('hubspot_api_key')}",
                "Content-Type": "application/json"
            }
            
            lead_payload = {
                "properties": lead_properties
            }
            
            lead_response = requests.post(lead_url, json=lead_payload, headers=headers)
            
            if lead_response.status_code == 201:
                lead_id = lead_response.json().get('id')
                
                # Associate lead with contact
                association_url = f"https://api.hubapi.com/crm/v3/objects/leads/{lead_id}/associations/contacts/{contact_id}/lead_to_contact"
                association_response = requests.put(association_url, headers=headers)
                
                return {
                    "contact_id": contact_id,
                    "lead_id": lead_id,
                    "status": "updated"
                }
            else:
                return {
                    "contact_id": contact_id,
                    "lead_id": None,
                    "status": "contact_updated_lead_failed"
                }
            
    except Exception as e:
        st.error(f"Error updating contact: {str(e)}")
        return None

def get_hubspot_contacts(limit: int = 50) -> List[Dict]:
    """Retrieve contacts from HubSpot CRM"""
    client = get_hubspot_client()
    if not client:
        return []
    
    try:
        properties = ["firstname", "lastname", "company", "jobtitle", "createdate", "notes_last_updated", "last_contact_date"]
        api_response = client.crm.contacts.basic_api.get_page(
            limit=limit,
            properties=properties
        )
        
        contacts = []
        for contact in api_response.results:
            props = contact.properties
            contacts.append({
                "id": contact.id,
                "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                "company": props.get('company', ''),
                "title": props.get('jobtitle', ''),
                "created_date": props.get('createdate', ''),
                "notes_updated": props.get('notes_last_updated', ''),
                "last_contact": props.get('last_contact_date', '')
            })
        
        # Sort by creation date manually (newest first)
        contacts.sort(key=lambda x: x.get('created_date', ''), reverse=True)
        
        return contacts
        
    except Exception as e:
        st.error(f"Error retrieving contacts: {str(e)}")
        return []

def get_hubspot_leads(limit: int = 50) -> List[Dict]:
    """Retrieve leads from HubSpot CRM"""
    try:
        # Get leads using direct API call
        leads_url = f"https://api.hubapi.com/crm/v3/objects/leads"
        headers = {
            "Authorization": f"Bearer {st.secrets.get('hubspot_api_key')}",
            "Content-Type": "application/json"
        }
        
        params = {
            "limit": limit,
            "properties": "firstname,lastname,company,jobtitle,pitch_type,last_message_subject,lead_status,createdate",
            "sorts": "createdate:desc"
        }
        
        response = requests.get(leads_url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            leads = []
            
            for lead in data.get('results', []):
                props = lead.get('properties', {})
                leads.append({
                    "id": lead.get('id'),
                    "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                    "company": props.get('company', ''),
                    "title": props.get('jobtitle', ''),
                    "pitch_type": props.get('pitch_type', ''),
                    "last_message": props.get('last_message_subject', ''),
                    "lead_status": props.get('lead_status', ''),
                    "created_date": props.get('createdate', '')
                })
            
            return leads
        else:
            st.error(f"Error retrieving leads: {response.text}")
            return []
            
    except Exception as e:
        st.error(f"Error retrieving leads: {str(e)}")
        return []

def add_note_to_contact(contact_id: str, note: str):
    """Add a note to a HubSpot contact using the proper client library"""
    client = get_hubspot_client()
    if not client:
        return False
    
    try:
        # Note properties - using the standard HubSpot note properties
        properties = {
            "hs_note_body": note,
            "hs_timestamp": str(int(datetime.now().timestamp() * 1000))
        }
        
        # Association to link the note with the contact
        associations = [{
            "types": [{
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": 202  # Note to Contact association type
            }],
            "to": {
                "id": contact_id
            }
        }]
        
        # Create the note with association
        simple_public_object_input_for_create = NotesSimplePublicObjectInputForCreate(
            properties=properties,
            associations=associations
        )
        
        # Create the note using HubSpot client
        api_response = client.crm.objects.notes.basic_api.create(
            simple_public_object_input_for_create=simple_public_object_input_for_create
        )
        
        if api_response.id:
            # Update contact with last note date
            contact_update_properties = {
                "notes_last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            simple_public_object_input = SimplePublicObjectInput(properties=contact_update_properties)
            client.crm.contacts.basic_api.update(contact_id=contact_id, simple_public_object_input=simple_public_object_input)
            
            return True
        else:
            return False
            
    except ApiException as e:
        st.error(f"HubSpot API error adding note: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Error adding note: {str(e)}")
        return False

# Password protection
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hashlib.sha256(st.session_state["password"].encode()).hexdigest() == st.secrets.get("password_hash", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password
    st.text_input(
        "Password", 
        type="password", 
        on_change=password_entered, 
        key="password"
    )
    
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    
    return False

def generate_message(name: str, title: str, company: str, pitch_type: str) -> Dict[str, str]:
    """Generate LinkedIn message using OpenAI API"""
    
    try:
        # Get the appropriate prompt from session state
        prompt_config = st.session_state.prompts[pitch_type]
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=st.secrets["openai_api_key"])
        
        # Format the user prompt with the provided information
        formatted_prompt = prompt_config["user_prompt"].format(
            name=name,
            title=title,
            company=company
        )
        
        # Make API call with the model specified for this prompt type
        response = client.chat.completions.create(
            model=prompt_config.get("model", "gpt-3.5-turbo"),
            messages=[
                {"role": "system", "content": prompt_config["system_prompt"]},
                {"role": "user", "content": formatted_prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Parse the response
        content = response.choices[0].message.content.strip()
        
        # Try to extract subject and body (basic parsing)
        lines = content.split('\n')
        subject = ""
        body = ""
        
        # Look for subject line patterns
        for i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ["subject", "1.", "subject line"]):
                subject = line.split(":", 1)[-1].strip()
                if subject.startswith('"') and subject.endswith('"'):
                    subject = subject[1:-1]
                # Get the rest as body
                body_lines = []
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not any(keyword in lines[j].lower() for keyword in ["2.", "message", "body"]):
                        body_lines.append(lines[j].strip())
                    elif lines[j].strip() and any(keyword in lines[j].lower() for keyword in ["2.", "message", "body"]):
                        continue
                    elif lines[j].strip():
                        body_lines.append(lines[j].strip())
                body = " ".join(body_lines)
                break
        
        # Fallback parsing if structured parsing fails
        if not subject or not body:
            # Split by common patterns
            if "subject" in content.lower() and "message" in content.lower():
                parts = content.split("2.", 1)
                if len(parts) == 2:
                    subject_part = parts[0].replace("1.", "").replace("Subject:", "").replace("subject line:", "").strip()
                    if subject_part.startswith('"') and subject_part.endswith('"'):
                        subject_part = subject_part[1:-1]
                    subject = subject_part
                    body = parts[1].replace("Message:", "").replace("message body:", "").strip()
            else:
                # Simple fallback
                subject = "Follow up on LinkedIn"
                body = content
        
        return {
            "subject": subject,
            "body": body,
            "raw_response": content,
            "model_used": prompt_config.get("model", "gpt-3.5-turbo")
        }
        
    except Exception as e:
        st.error(f"Error generating message: {str(e)}")
        return {
            "subject": "Error generating subject",
            "body": "Error generating message body",
            "raw_response": str(e),
            "model_used": "error"
        }

def main():
    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📧 Message Generator", "👥 CRM Records", "⚙️ Prompt Management"])
    
    with tab1:
        st.title("📧 LinkedIn Sales Navigator Message Creator")
        st.markdown("---")
        
        # Create two columns for input
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.header("👤 Prospect Information")
            
            # Input fields for prospect info
            name = st.text_input(
                "Full Name*",
                placeholder="John Smith",
                help="Enter the prospect's full name from LinkedIn"
            )
            
            title = st.text_input(
                "Job Title*",
                placeholder="VP of Sales",
                help="Enter their current job title"
            )
            
            company = st.text_input(
                "Company*",
                placeholder="Acme Corporation",
                help="Enter their company name"
            )
        
        with col2:
            st.header("🎯 Pitch Configuration")
            
            # Pitch type selection from session state prompts
            pitch_type = st.selectbox(
                "Select Pitch Type*",
                options=list(st.session_state.prompts.keys()),
                help="Choose the type of outreach message"
            )
            
            # Show pitch description and model info
            pitch_descriptions = {
                "Cold Outreach": "Initial contact to introduce yourself and spark interest",
                "Follow-up": "Re-engage prospects who haven't responded to previous messages",
                "Product Demo": "Invite prospects to see your product in action",
                "Partnership": "Propose mutually beneficial business partnerships"
            }
            
            selected_prompt = st.session_state.prompts.get(pitch_type, {})
            model_info = selected_prompt.get("model", "gpt-3.5-turbo")
            
            st.info(f"**{pitch_type}:** {pitch_descriptions.get(pitch_type, 'Custom pitch type')}")
            st.info(f"🤖 **Model:** {model_info}")
        
        st.markdown("---")
        
        # Generate button
        if st.button("🚀 Generate LinkedIn Message & Add to CRM", type="primary", use_container_width=True):
            # Validation
            if not all([name, title, company]):
                st.error("⚠️ Please fill in all required fields (Name, Title, Company)")
                return
            
            # Show loading spinner
            with st.spinner("🤖 Generating personalized message..."):
                result = generate_message(name, title, company, pitch_type)
            
            # Display results
            if result["subject"] != "Error generating subject":
                st.success("✅ Message generated successfully!")
                
                # Add to HubSpot CRM
                with st.spinner("💼 Adding to HubSpot CRM..."):
                    result_crm = create_hubspot_contact(name, title, company, pitch_type, result["subject"], result["body"])
                    if result_crm:
                        if result_crm["status"] == "success":
                            st.success(f"✅ Added to HubSpot CRM (Contact: {result_crm['contact_id']}, Lead: {result_crm['lead_id']})")
                        elif result_crm["status"] == "updated":
                            st.success(f"✅ Updated existing contact and created new lead (Contact: {result_crm['contact_id']}, Lead: {result_crm['lead_id']})")
                        elif result_crm["status"] == "association_failed":
                            st.warning(f"⚠️ Contact and lead created but association failed (Contact: {result_crm['contact_id']}, Lead: {result_crm['lead_id']})")
                        elif result_crm["status"] == "lead_creation_failed":
                            st.warning(f"⚠️ Contact created but lead creation failed (Contact: {result_crm['contact_id']})")
                        else:
                            st.warning("⚠️ Partial success - check HubSpot for details")
                    else:
                        st.warning("⚠️ Message generated but couldn't add to CRM. Check HubSpot configuration.")
                
                # Create columns for results
                result_col1, result_col2 = st.columns([1, 1])
                
                with result_col1:
                    st.subheader("📝 Subject Line")
                    st.text_area(
                        "Subject",
                        value=result["subject"],
                        height=80,
                        key="subject_output",
                        help="Copy this subject line"
                    )
                    
                    if st.button("📋 Copy Subject", key="copy_subject"):
                        st.write("Subject copied to clipboard! (Use Ctrl+C)")
                
                with result_col2:
                    st.subheader("💬 Message Body")
                    st.text_area(
                        "Message",
                        value=result["body"],
                        height=150,
                        key="body_output",
                        help="Copy this message body"
                    )
                    
                    if st.button("📋 Copy Message Body", key="copy_body"):
                        st.write("Message body copied to clipboard! (Use Ctrl+C)")
                
                # Full message preview
                st.markdown("---")
                st.subheader("📧 Complete Message Preview")
                
                full_message = f"**Subject:** {result['subject']}\n\n**Message:**\n{result['body']}"
                st.markdown(full_message)
                
                # Copy full message button
                col_center = st.columns([1, 2, 1])[1]
                with col_center:
                    if st.button("📋 Copy Complete Message", type="secondary", use_container_width=True):
                        st.write("Complete message copied! (Use Ctrl+C)")
                
                # Show model used
                st.info(f"🤖 Generated using: {result['model_used']}")
                
                # Debug info (can be removed in production)
                with st.expander("🔍 Debug Information (Raw API Response)"):
                    st.text(result["raw_response"])
            
            else:
                st.error("❌ Failed to generate message. Please try again.")
    
    with tab2:
        st.title("👥 HubSpot CRM Records")
        st.markdown("---")
        
        # Check HubSpot connection
        hubspot_client = get_hubspot_client()
        if not hubspot_client:
            st.error("❌ HubSpot not connected. Please configure your HubSpot API key in secrets.")
            st.info("💡 Go to HubSpot → Settings → Integrations → Private Apps to create an API key")
            return
        
        # Refresh button
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.subheader("Recent Records")
        with col2:
            show_leads = st.checkbox("Show Leads", value=False, key="show_leads_checkbox")
        with col3:
            if st.button("🔄 Refresh", key="refresh_contacts"):
                st.cache_data.clear()
        
        # Get contacts and optionally leads from HubSpot
        with st.spinner("📥 Loading records from HubSpot..."):
            contacts = get_hubspot_contacts(50)
            leads = get_hubspot_leads(50) if show_leads else []
        
        if not contacts and not leads:
            st.info("📝 No records found in HubSpot CRM")
            return
        
        # Display contacts
        if contacts:
            st.subheader("👤 Contacts")
            for i, contact in enumerate(contacts):
                with st.expander(f"👤 {contact['name']} - {contact['company']}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Title:** {contact['title']}")
                        st.write(f"**Company:** {contact['company']}")
                        if contact['created_date']:
                            created_date = contact['created_date'][:10] if len(contact['created_date']) > 10 else contact['created_date']
                            st.write(f"**Created:** {created_date}")
                        if contact['last_contact']:
                            st.write(f"**Last Contact:** {contact['last_contact']}")
                        if contact['notes_updated']:
                            st.write(f"**Last Note:** {contact['notes_updated']}")
                    
                    with col2:
                        # Add note functionality
                        note_key = f"note_{contact['id']}_{i}"
                        note_text = st.text_area(
                            "Add Note:",
                            key=note_key,
                            height=100,
                            placeholder="Enter a note about this contact..."
                        )
                        
                        if st.button(f"💾 Add Note", key=f"add_note_{contact['id']}_{i}"):
                            if note_text.strip():
                                with st.spinner("Adding note..."):
                                    success = add_note_to_contact(contact['id'], note_text.strip())
                                    if success:
                                        st.success("✅ Note added successfully!")
                                        st.cache_data.clear()  # Clear cache to refresh data
                                        st.rerun()
                                    else:
                                        st.error("❌ Failed to add note")
                            else:
                                st.warning("⚠️ Please enter a note before saving")
        
        # Display leads if requested
        if show_leads and leads:
            st.markdown("---")
            st.subheader("🎯 Leads")
            for i, lead in enumerate(leads):
                with st.expander(f"🎯 {lead['name']} - {lead['company']} ({lead['lead_status']})", expanded=False):
                    st.write(f"**Title:** {lead['title']}")
                    st.write(f"**Company:** {lead['company']}")
                    st.write(f"**Pitch Type:** {lead['pitch_type']}")
                    st.write(f"**Last Message:** {lead['last_message']}")
                    st.write(f"**Lead Status:** {lead['lead_status']}")
                    if lead['created_date']:
                        created_date = lead['created_date'][:10] if len(lead['created_date']) > 10 else lead['created_date']
                        st.write(f"**Created:** {created_date}")
    
    with tab3:
        st.title("⚙️ Prompt Management")
        st.markdown("---")
        
        # Debug: Show current prompts count
        st.write(f"📊 **Current prompts loaded:** {len(st.session_state.prompts)}")
        
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("➕ Add New Prompt", type="secondary"):
                st.session_state.show_add_prompt = True
        
        with col2:
            if st.button("🔄 Reset to Defaults", type="secondary"):
                if st.button("⚠️ Confirm Reset", key="confirm_reset"):
                    # Clear session state to reinitialize with defaults
                    if "prompts" in st.session_state:
                        del st.session_state.prompts
                    initialize_prompts()
                    st.success("✅ Prompts reset to defaults!")
                    st.rerun()
        
        # Add new prompt form
        if st.session_state.get("show_add_prompt", False):
            st.markdown("---")
            st.subheader("➕ Add New Prompt")
            
            with st.form("add_prompt_form"):
                new_prompt_name = st.text_input("Prompt Name*", placeholder="e.g., Event Invitation", key="new_prompt_name")
                new_system_prompt = st.text_area("System Prompt*", height=100, placeholder="You are a sales expert...", key="new_system_prompt")
                new_user_prompt = st.text_area("User Prompt*", height=150, placeholder="Create a LinkedIn message for:\nName: {name}\nTitle: {title}\nCompany: {company}\n\nGenerate:\n1. A compelling subject line\n2. A personalized message body", key="new_user_prompt")
                new_model = st.selectbox("Select Model*", AVAILABLE_MODELS, key="new_model")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    add_submitted = st.form_submit_button("💾 Add Prompt", type="primary")
                with col2:
                    cancel_add = st.form_submit_button("❌ Cancel")
                
                if add_submitted:
                    if new_prompt_name and new_system_prompt and new_user_prompt:
                        if new_prompt_name not in st.session_state.prompts:
                            st.session_state.prompts[new_prompt_name] = {
                                "system_prompt": new_system_prompt,
                                "user_prompt": new_user_prompt,
                                "model": new_model
                            }
                            st.success(f"✅ Added new prompt: {new_prompt_name}")
                            st.session_state.show_add_prompt = False
                            st.rerun()
                        else:
                            st.error("❌ Prompt name already exists!")
                    else:
                        st.error("⚠️ Please fill in all required fields")
                
                if cancel_add:
                    st.session_state.show_add_prompt = False
                    st.rerun()
        
        # Display and edit existing prompts
        st.markdown("---")
        st.subheader("📝 Current Prompts")
        
        # Check if prompts exist and display them
        if not st.session_state.prompts:
            st.warning("⚠️ No prompts found! Click 'Reset to Defaults' to restore default prompts.")
        else:
            for prompt_name in list(st.session_state.prompts.keys()):
                with st.expander(f"✏️ {prompt_name}", expanded=False):
                    prompt_data = st.session_state.prompts[prompt_name]
                    
                    # Edit form for each prompt
                    with st.form(f"edit_form_{prompt_name}"):
                        st.write(f"**Editing: {prompt_name}**")
                        
                        # Prompt Name (editable)
                        new_prompt_name = st.text_input(
                            "Prompt Name*", 
                            value=prompt_name,
                            key=f"name_{prompt_name}",
                            help="Change the name of this prompt"
                        )
                        
                        # Model selection
                        current_model = prompt_data.get("model", "gpt-3.5-turbo")
                        selected_model = st.selectbox(
                            "OpenAI Model", 
                            AVAILABLE_MODELS, 
                            index=AVAILABLE_MODELS.index(current_model) if current_model in AVAILABLE_MODELS else 0,
                            key=f"model_{prompt_name}"
                        )
                        
                        # System prompt
                        system_prompt = st.text_area(
                            "System Prompt", 
                            value=prompt_data["system_prompt"], 
                            height=100,
                            key=f"system_{prompt_name}"
                        )
                        
                        # User prompt
                        user_prompt = st.text_area(
                            "User Prompt", 
                            value=prompt_data["user_prompt"], 
                            height=200,
                            help="Use {name}, {title}, {company} as placeholders",
                            key=f"user_{prompt_name}"
                        )
                        
                        # Buttons
                        col1, col2, col3 = st.columns([1, 1, 2])
                        
                        with col1:
                            save_changes = st.form_submit_button("💾 Save Changes", type="primary")
                        
                        with col2:
                            delete_prompt = st.form_submit_button("🗑️ Delete", type="secondary")
                        
                        if save_changes:
                            # Validate new prompt name
                            if not new_prompt_name.strip():
                                st.error("❌ Prompt name cannot be empty!")
                            elif new_prompt_name != prompt_name and new_prompt_name in st.session_state.prompts:
                                st.error(f"❌ Prompt name '{new_prompt_name}' already exists!")
                            else:
                                # Update prompt data
                                updated_prompt = {
                                    "system_prompt": system_prompt,
                                    "user_prompt": user_prompt,
                                    "model": selected_model
                                }
                                
                                # If name changed, create new entry and delete old one
                                if new_prompt_name != prompt_name:
                                    st.session_state.prompts[new_prompt_name] = updated_prompt
                                    del st.session_state.prompts[prompt_name]
                                    st.success(f"✅ Renamed '{prompt_name}' to '{new_prompt_name}' and updated!")
                                else:
                                    st.session_state.prompts[prompt_name] = updated_prompt
                                    st.success(f"✅ Updated {prompt_name}")
                                
                                st.rerun()
                        
                        if delete_prompt:
                            if len(st.session_state.prompts) > 1:  # Keep at least one prompt
                                del st.session_state.prompts[prompt_name]
                                st.success(f"✅ Deleted {prompt_name}")
                                st.rerun()
                            else:
                                st.error("❌ Cannot delete the last prompt!")

# App entry point
if __name__ == "__main__":
    # Check password first
    if not check_password():
        st.stop()
    
    # Run main app if password is correct
    main()
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        <small>LinkedIn Sales Navigator Message Creator + HubSpot CRM | Powered by OpenAI GPT-3.5</small>
        </div>
        """,
        unsafe_allow_html=True
    ) 