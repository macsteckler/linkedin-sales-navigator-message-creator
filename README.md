# LinkedIn Sales Navigator Message Creator + HubSpot CRM

A Streamlit web application that generates personalized LinkedIn messages using OpenAI's GPT API and automatically manages prospects in HubSpot CRM. Input prospect information from LinkedIn Sales Navigator, get professionally crafted messages, and seamlessly track your outreach in your CRM.

## Features

- 🔐 **Password Protection**: Secure access with SHA256 hashed passwords
- 👤 **Prospect Input**: Easy form to input name, title, and company information
- 🎯 **Multiple Pitch Types**: 4 different message types (Cold Outreach, Follow-up, Product Demo, Partnership)
- 🤖 **AI-Powered**: Uses OpenAI GPT-3.5-turbo for personalized message generation
- 📋 **Copy Functionality**: Easy copy-to-clipboard for subject lines and message bodies
- 💼 **HubSpot CRM Integration**: Automatically adds prospects to your CRM
- 📝 **CRM Management**: View all contacts and add notes directly from the app
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/linkedin-sales-navigator-message-creator.git
cd linkedin-sales-navigator-message-creator
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

#### OpenAI API Key
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Copy the key (starts with `sk-`)

#### HubSpot API Key
1. Log into your HubSpot account
2. Go to **Settings** → **Integrations** → **Private Apps**
3. Click **Create a private app**
4. Give it a name like "LinkedIn Message Creator"
5. Under **Scopes**, select:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.leads.read`
   - `crm.objects.leads.write`
   - `crm.objects.notes.read`
   - `crm.objects.notes.write`
6. Click **Create app** and copy the access token

### 4. Configure Secrets

Edit `.streamlit/secrets.toml` and replace the placeholder values:

```toml
# OpenAI API Key (get from https://platform.openai.com/api-keys)
openai_api_key = "sk-your-actual-openai-api-key"

# HubSpot API Key (get from HubSpot Settings > Integrations > Private Apps)
hubspot_api_key = "your-hubspot-api-key"

# Password hash for app access
password_hash = "your-sha256-password-hash"
```

**To generate a password hash:**
```bash
# Replace "your_password" with your desired password
echo -n "your_password" | shasum -a 256
```

### 5. Run Locally

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Deployment

### Deploy to Streamlit Cloud

1. **Push to GitHub**: Ensure your code is pushed to a GitHub repository

2. **Connect to Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub
   - Click "New app"
   - Select your repository and branch
   - Set main file path: `app.py`

3. **Configure Secrets**:
   - In your Streamlit Cloud app settings, go to "Secrets"
   - Add your secrets in TOML format:
   ```toml
   openai_api_key = "sk-your-actual-openai-api-key"
   hubspot_api_key = "your-hubspot-api-key"
   password_hash = "your-sha256-password-hash"
   ```

4. **Deploy**: Click "Deploy!" and your app will be live

### Deploy to Other Platforms

The app can also be deployed to:
- **Heroku**: Add a `Procfile` with `web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
- **Railway**: Direct deployment from GitHub
- **AWS/Google Cloud**: Using container services

## Usage

### Message Generation
1. **Access the App**: Navigate to your deployed URL or local instance
2. **Enter Password**: Use the password you set in the configuration
3. **Fill Prospect Information**:
   - Full Name (from LinkedIn profile)
   - Job Title (current position)
   - Company (current workplace)
4. **Select Pitch Type**: Choose from 4 available message types
5. **Generate Message**: Click "Generate LinkedIn Message & Add to CRM"
6. **Copy and Use**: Copy the generated subject line and message body to LinkedIn

### CRM Management
1. **View Records**: Click the "CRM Records" tab to see all your prospects
2. **Add Notes**: Use the note field in each contact's section to add follow-up notes
3. **Track Progress**: See when contacts were added and when notes were last updated

## Pitch Types

### 1. Cold Outreach
Initial contact messages to introduce yourself and spark interest with new prospects.

### 2. Follow-up
Re-engagement messages for prospects who haven't responded to previous outreach.

### 3. Product Demo
Invitation messages to showcase your product's value proposition and schedule demonstrations.

### 4. Partnership
Messages proposing mutually beneficial business partnerships and collaboration opportunities.

## HubSpot Integration Details

### What Gets Added to HubSpot
When you generate a message, the app automatically creates a contact with:
- **Name**: First and last name
- **Company**: Company name
- **Job Title**: Current position
- **Pitch Type**: Type of message generated
- **Last Message Subject**: Generated subject line
- **Last Message Body**: Generated message content
- **Lead Source**: "LinkedIn Sales Navigator"
- **Lifecycle Stage**: "Lead"

### Custom Properties
The app uses these custom HubSpot properties (created automatically):
- `pitch_type`: Type of outreach message
- `last_message_subject`: Most recent message subject
- `last_message_body`: Most recent message content
- `notes_last_updated`: When notes were last added

### Duplicate Handling
If a contact already exists, the app will update their information with the new message details instead of creating a duplicate.

## Security

- **Password Protection**: App requires password authentication before access
- **API Key Security**: OpenAI and HubSpot API keys are stored securely in Streamlit secrets
- **No Data Storage**: No prospect information is stored locally or logged
- **HTTPS**: Use HTTPS in production for secure data transmission

## Configuration

### Default Password

The default password is `linkedin2024` (hash: `8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918`)

### API Settings

**OpenAI Settings:**
- **Model**: GPT-3.5-turbo (cost-effective and fast)
- **Max Tokens**: 300 (sufficient for LinkedIn messages)
- **Temperature**: 0.7 (balanced creativity and consistency)

**HubSpot Settings:**
- **Contact Limit**: 50 recent contacts displayed
- **Auto-sync**: Real-time contact creation and updates

## Customization

### Adding New Pitch Types

Edit the `PITCH_PROMPTS` dictionary in `app.py`:

```python
PITCH_PROMPTS["New Pitch Type"] = {
    "system_prompt": "Your system prompt here...",
    "user_prompt": "Your user prompt template with {name}, {title}, {company}..."
}
```

### Modifying Existing Prompts

Update the prompts in the `PITCH_PROMPTS` dictionary to match your specific use cases and messaging style.

### HubSpot Custom Properties

To add more custom properties, modify the `properties` dictionary in the `create_hubspot_contact` function.

## Troubleshooting

### Common Issues

1. **"OpenAI API Error"**: Check that your API key is valid and has credits
2. **"HubSpot not connected"**: Verify your HubSpot API key and permissions
3. **"Password Incorrect"**: Verify your password hash is correct
4. **"Module Not Found"**: Run `pip install -r requirements.txt`
5. **"Contact already exists"**: Normal behavior - contact will be updated instead

### API Limits

**OpenAI:**
- Rate limits and costs per API call
- Monitor usage at [platform.openai.com](https://platform.openai.com/usage)

**HubSpot:**
- Free tier: 10,000 API calls per day
- Monitor usage in HubSpot → Settings → Integrations → Private Apps

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review OpenAI API documentation
3. Review HubSpot API documentation
4. Check Streamlit documentation for deployment issues

## License

This project is provided as-is for business use. Ensure compliance with:
- OpenAI's usage policies
- HubSpot's API terms of service
- LinkedIn's messaging policies and terms of service

---

**Note**: This application is designed to assist with LinkedIn outreach and CRM management. Always ensure your messages comply with LinkedIn's messaging policies and best practices for professional networking.

### **🔧 Required HubSpot Permissions:**

Make sure your HubSpot private app has these scopes:
- `crm.objects.contacts.read`
- `crm.objects.contacts.write`
- `crm.objects.leads.read`
- `crm.objects.leads.write`
- `crm.objects.notes.read`
- `crm.objects.notes.write` 