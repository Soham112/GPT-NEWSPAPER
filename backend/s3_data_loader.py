"""
S3 Data Loader for Outreach Agent
Fetches marketing campaign data from S3 and provides client-specific views.
"""
import os
import csv
import json
import io
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

# S3 Configuration
S3_BUCKET = os.getenv('S3_BUCKET', 'project-xlr8')
S3_PREFIX = os.getenv('S3_OUTREACH_PREFIX', 'outreach-agent/')

# Initialize S3 client
s3_client = None

def get_s3_client():
    """Get or create S3 client."""
    global s3_client
    if s3_client is None:
        s3_client = boto3.client('s3')
    return s3_client


def load_csv_from_s3(filename: str) -> List[Dict]:
    """
    Load a CSV file from S3 and return as list of dictionaries.
    Tries _v2.csv version first, then falls back to original.
    
    Args:
        filename: Name of the CSV file (e.g., 'client_metrics.csv')
    
    Returns:
        List of dictionaries, one per row
    """
    try:
        client = get_s3_client()
        
        # Try _v2 version first, then fallback to original
        filenames_to_try = [
            filename.replace('.csv', '_v2.csv') if not filename.endswith('_v2.csv') else filename,
            filename
        ]
        
        for fname in filenames_to_try:
            key = f"{S3_PREFIX}{fname}"
            try:
                response = client.get_object(Bucket=S3_BUCKET, Key=key)
                csv_content = response['Body'].read().decode('utf-8')
                
                # Parse CSV
                reader = csv.DictReader(io.StringIO(csv_content))
                return list(reader)
            except ClientError as e:
                if 'NoSuchKey' in str(e) and fname != filenames_to_try[-1]:
                    continue  # Try next filename
                raise
        
        return []
    except ClientError as e:
        print(f"Error loading {filename} from S3: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error loading {filename}: {e}")
        return []


def get_all_clients() -> List[Dict]:
    """
    Get list of all clients from companies.csv.
    
    Returns:
        List of client dictionaries with company_id and name
    """
    companies = load_csv_from_s3('companies.csv')
    return [
        {
            'company_id': company.get('company_id', ''),
            'name': company.get('name', ''),
            'industry': company.get('industry', ''),
            'employees': company.get('employees', ''),
            'hq': company.get('hq', '')
        }
        for company in companies
    ]


def get_client_metrics(client_id: str) -> Optional[Dict]:
    """
    Get metrics for a specific client, including trend data.
    
    Args:
        client_id: Company ID (e.g., 'C001')
    
    Returns:
        Dictionary with client metrics, trends, and previous month data
    """
    metrics = load_csv_from_s3('client_metrics.csv')
    current_metric = None
    previous_metric = None
    
    # Find current month (most recent) and previous month
    for metric in metrics:
        if metric.get('client_id') == client_id:
            if not current_metric or metric.get('month', '') > current_metric.get('month', ''):
                if current_metric:
                    previous_metric = current_metric
                current_metric = metric
            elif not previous_metric:
                previous_metric = metric
    
    if not current_metric:
        return None
    
    # Build current metrics
    result = {
        'client_id': current_metric.get('client_id', ''),
        'client_name': current_metric.get('client_name', ''),
        'month': current_metric.get('month', ''),
        'linkedin_outreach': int(current_metric.get('linkedin_outreach', 0)),
        'email_sends': int(current_metric.get('email_sends', 0)),
        'email_opens': int(current_metric.get('email_opens', 0)),
        'email_replies': int(current_metric.get('email_replies', 0)),
        'calls_placed': int(current_metric.get('calls_placed', 0)),
        'meetings_booked': int(current_metric.get('meetings_booked', 0)),
        'hubspot_activities': int(current_metric.get('hubspot_activities', 0)),
        'engagement_score': int(current_metric.get('engagement_score', 0))
    }
    
    # Calculate trends if previous month exists
    if previous_metric:
        trends = {}
        for key in ['linkedin_outreach', 'email_sends', 'email_replies', 'calls_placed', 'hubspot_activities']:
            current_val = result.get(key, 0)
            prev_val = int(previous_metric.get(key, 0))
            if prev_val > 0:
                change = ((current_val - prev_val) / prev_val) * 100
                trends[key] = {
                    'change_percent': round(change, 1),
                    'change_absolute': current_val - prev_val,
                    'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
                }
            else:
                trends[key] = {
                    'change_percent': 0,
                    'change_absolute': current_val,
                    'direction': 'up' if current_val > 0 else 'neutral'
                }
        result['trends'] = trends
    
    return result


def get_client_activities(client_id: str, limit: int = 50, filters: Dict = None) -> List[Dict]:
    """
    Get activities for a specific client with optional filters.
    
    Args:
        client_id: Company ID (e.g., 'C001')
        limit: Maximum number of activities to return
        filters: Optional dict with 'channel', 'status', 'days' filters
    
    Returns:
        List of activity dictionaries
    """
    activities = load_csv_from_s3('activities.csv')
    
    # Filter by client_id (handle both company_id and client_id)
    client_activities = []
    for act in activities:
        if act.get('company_id') == client_id or act.get('client_id') == client_id:
            # Handle both old and new CSV formats
            activity = {
                'activity_id': act.get('activity_id', ''),
                'timestamp': act.get('timestamp') or act.get('datetime', ''),
                'contact_id': act.get('contact_id', ''),
                'company_id': act.get('company_id') or act.get('client_id', ''),
                'client_id': act.get('client_id') or act.get('company_id', ''),
                'campaign_id': act.get('campaign_id', ''),
                'channel': act.get('channel', ''),
                'type': act.get('type', ''),
                'status': act.get('status', ''),  # Activity-level status (success, failed, pending, etc.)
                'contact_status': act.get('contact_status', ''),  # Contact-level status (from activities_v2.csv)
                'summary': act.get('summary') or act.get('notes', ''),
                'direction': act.get('direction', 'outbound'),
                'engagement_weight': int(act.get('engagement_weight', 0))
            }
            client_activities.append(activity)
    
    # Apply filters
    if filters:
        from datetime import datetime, timedelta
        
        if filters.get('channel'):
            client_activities = [a for a in client_activities if a['channel'] == filters['channel']]
        
        if filters.get('status'):
            client_activities = [a for a in client_activities if a['status'].lower() == filters['status'].lower()]
        
        if filters.get('days'):
            cutoff_date = datetime.now() - timedelta(days=filters['days'])
            client_activities = [
                a for a in client_activities
                if a.get('timestamp') and datetime.fromisoformat(a['timestamp'].replace('T', ' ').split('.')[0]) >= cutoff_date
            ]
    
    # Sort by timestamp (most recent first) and limit
    client_activities.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return client_activities[:limit]


def get_client_contacts(client_id: str) -> List[Dict]:
    """
    Get contacts for a specific client.
    
    Args:
        client_id: Company ID (e.g., 'C001')
    
    Returns:
        List of contact dictionaries
    """
    contacts = load_csv_from_s3('contacts.csv')
    return [
        {
            'contact_id': contact.get('contact_id', ''),
            'name': contact.get('name', ''),
            'title': contact.get('title', ''),
            'company_id': contact.get('company_id') or contact.get('client_id', ''),
            'client_id': contact.get('client_id') or contact.get('company_id', ''),
            'location': contact.get('location', ''),
            'email': contact.get('email', ''),
            'phone': contact.get('phone', ''),
            'linkedin': contact.get('linkedin') or contact.get('linkedin_url', ''),
            'status': contact.get('status', ''),
            'last_contacted_days': int(contact.get('last_contacted_days', 0)),
            'role_type': contact.get('role_type', ''),
            'seniority': contact.get('seniority', ''),
            'persona_score': int(contact.get('persona_score', 0))
        }
        for contact in contacts
        if (contact.get('company_id') == client_id or contact.get('client_id') == client_id)
    ]


def get_client_campaigns(client_id: str) -> List[Dict]:
    """
    Get campaigns for a specific client.
    
    Args:
        client_id: Company ID (e.g., 'C001')
    
    Returns:
        List of campaign dictionaries
    """
    campaigns = load_csv_from_s3('campaigns.csv')
    
    return [
        {
            'campaign_id': camp.get('campaign_id', ''),
            'name': camp.get('name', ''),
            'type': camp.get('type') or camp.get('channel_primary', ''),
            'channel_primary': camp.get('channel_primary', ''),
            'start_date': camp.get('start_date', ''),
            'end_date': camp.get('end_date', ''),
            'objective': camp.get('objective', ''),
            'status': camp.get('status', '')
        }
        for camp in campaigns
        if camp.get('client_id') == client_id
    ]


def get_client_summary(client_id: str) -> Dict:
    """
    Generate client summary snapshot.
    
    Args:
        client_id: Company ID (e.g., 'C001')
    
    Returns:
        Dictionary with summary statistics
    """
    contacts = get_client_contacts(client_id)
    activities = get_client_activities(client_id, limit=1000)
    metrics = get_client_metrics(client_id)
    
    from datetime import datetime, timedelta
    
    # Count decision makers
    decision_makers = [c for c in contacts if c.get('role_type') == 'decision_maker']
    
    # Activities this week
    week_ago = datetime.now() - timedelta(days=7)
    recent_activities = [
        a for a in activities
        if a.get('timestamp') and datetime.fromisoformat(a['timestamp'].replace('T', ' ').split('.')[0]) >= week_ago
    ]
    
    # Pending follow-ups
    pending_followups = [a for a in activities if a.get('status', '').lower() == 'pending']
    
    # Cold leads revived (contacts with recent activity after long gap)
    # Simplified: contacts with activity in last 7 days but last_contacted_days > 30
    revived_leads = len([
        c for c in contacts
        if c.get('last_contacted_days', 0) > 30 and any(
            a.get('contact_id') == c.get('contact_id')
            for a in recent_activities
        )
    ])
    
    return {
        'decision_makers_engaged': len(decision_makers),
        'activities_this_week': len(recent_activities),
        'pending_followups': len(pending_followups),
        'cold_leads_revived': revived_leads,
        'engagement_score': metrics.get('engagement_score', 0) if metrics else 0
    }


def get_contact_status(contact: Dict, activities: List[Dict]) -> str:
    """
    Determine contact status based on activities.
    
    First checks if activities have a direct 'contact_status' field (from activities_v2.csv),
    otherwise calculates status from activity types and statuses.
    
    Status priority (highest to lowest):
    1. Deal Closed – Won / Lost (final states)
    2. Negotiating
    3. Meeting Completed – Positive / Negative
    4. Meeting booked
    5. In-progress
    6. Responded
    7. Engaged
    8. Not Responded
    9. Not Started
    """
    contact_id = contact.get('contact_id', '')
    contact_activities = [a for a in activities if a.get('contact_id') == contact_id]
    
    if not contact_activities:
        return 'Not Started'
    
    # Check if activities have a direct 'contact_status' field (from activities_v2.csv)
    # Use the most recent activity's contact_status if available
    valid_contact_statuses = [
        'Responded', 'Engaged', 'Not Responded', 'In-progress',
        'Meeting booked', 'Meeting Completed – Positive', 'Meeting Completed – Negative',
        'Negotiating', 'Deal Closed – Won', 'Deal Closed – Lost'
    ]
    
    # Create case-insensitive lookup for status matching
    valid_statuses_lower = {s.lower(): s for s in valid_contact_statuses}
    
    # Sort activities by timestamp (most recent first)
    from datetime import datetime
    sorted_activities = sorted(
        contact_activities,
        key=lambda x: (
            datetime.fromisoformat(x['timestamp'].replace('T', ' ').split('.')[0])
            if x.get('timestamp') else datetime.min
        ),
        reverse=True
    )
    
    # Check most recent activities for contact_status field
    for activity in sorted_activities:
        contact_status_raw = activity.get('contact_status', '').strip()
        if contact_status_raw:
            # Case-insensitive matching: normalize and look up
            contact_status_normalized = contact_status_raw.lower()
            if contact_status_normalized in valid_statuses_lower:
                # Return the properly formatted status (with correct capitalization)
                return valid_statuses_lower[contact_status_normalized]
    
    # 1. Check for Deal Closed – Won / Lost (highest priority)
    deal_closed_won = any(
        (a.get('type', '').lower() in ['deal_closed', 'deal', 'closed_won'] or
         a.get('status', '').lower() in ['won', 'closed_won', 'deal_won']) and
        a.get('status', '').lower() not in ['lost', 'closed_lost', 'deal_lost']
        for a in contact_activities
    )
    deal_closed_lost = any(
        a.get('type', '').lower() in ['deal_closed', 'deal', 'closed_lost'] or
        a.get('status', '').lower() in ['lost', 'closed_lost', 'deal_lost']
        for a in contact_activities
    )
    if deal_closed_won:
        return 'Deal Closed – Won'
    if deal_closed_lost:
        return 'Deal Closed – Lost'
    
    # 2. Check for Negotiating
    has_negotiating = any(
        a.get('type', '').lower() in ['negotiation', 'negotiating', 'proposal'] or
        a.get('status', '').lower() in ['negotiating', 'negotiation', 'in_negotiation']
        for a in contact_activities
    )
    if has_negotiating:
        return 'Negotiating'
    
    # 3. Check for Meeting Completed – Positive / Negative
    meeting_completed_positive = any(
        a.get('type', '').lower() in ['meeting', 'meeting_completed'] and
        (a.get('status', '').lower() in ['completed', 'success', 'positive'] or
         'positive' in a.get('summary', '').lower() or
         'positive' in a.get('outcome', '').lower())
        for a in contact_activities
    )
    meeting_completed_negative = any(
        a.get('type', '').lower() in ['meeting', 'meeting_completed'] and
        (a.get('status', '').lower() in ['completed_negative', 'negative'] or
         'negative' in a.get('summary', '').lower() or
         'negative' in a.get('outcome', '').lower() or
         'not interested' in a.get('summary', '').lower())
        for a in contact_activities
    )
    if meeting_completed_positive:
        return 'Meeting Completed – Positive'
    if meeting_completed_negative:
        return 'Meeting Completed – Negative'
    
    # 4. Check for Meeting booked
    meeting_booked = any(
        a.get('type', '').lower() in ['meeting', 'call', 'demo'] and
        a.get('status', '').lower() in ['scheduled', 'booked', 'pending', 'confirmed']
        for a in contact_activities
    )
    if meeting_booked:
        return 'Meeting booked'
    
    # 5. Check for In-progress
    in_progress = any(
        a.get('status', '').lower() in ['in_progress', 'in-progress', 'active', 'ongoing'] or
        a.get('type', '').lower() in ['proposal', 'quote', 'rfp']
        for a in contact_activities
    )
    if in_progress:
        return 'In-progress'
    
    # 6. Check for Responded (has successful reply/response activity)
    has_response = any(
        a.get('type', '').lower() in ['email_reply', 'reply', 'response', 'email_response'] and 
        a.get('status', '').lower() in ['success', 'responded', 'replied']
        for a in contact_activities
    )
    if has_response:
        return 'Responded'
    
    # 7. Check for Engaged (recent successful activities)
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    recent_success = any(
        a.get('status', '').lower() in ['success', 'engaged'] and
        a.get('timestamp') and
        datetime.fromisoformat(a['timestamp'].replace('T', ' ').split('.')[0]) >= week_ago
        for a in contact_activities
    )
    if recent_success:
        return 'Engaged'
    
    # 8. Not Responded (has activities but no responses)
    has_activities_no_response = not has_response and len(contact_activities) > 0
    if has_activities_no_response:
        return 'Not Responded'
    
    # 9. Default fallback (should not reach here if logic is correct)
    return 'Not Started'


def get_contact_channels(contact_id: str, activities: List[Dict]) -> List[str]:
    """Get list of channels used for a contact."""
    contact_activities = [a for a in activities if a.get('contact_id') == contact_id]
    channels = set()
    for activity in contact_activities:
        channel = activity.get('channel', '')
        if channel:
            channels.add(channel)
    return sorted(list(channels))


def get_last_contacted(contact_id: str, activities: List[Dict]) -> Optional[datetime]:
    """Get last contacted datetime for a contact."""
    contact_activities = [a for a in activities if a.get('contact_id') == contact_id]
    if not contact_activities:
        return None
    
    from datetime import datetime
    dates = []
    for activity in contact_activities:
        if activity.get('timestamp'):
            try:
                date = datetime.fromisoformat(activity['timestamp'].replace('T', ' ').split('.')[0])
                dates.append(date)
            except:
                pass
    
    return max(dates) if dates else None


def get_top_contacts(client_id: str, limit: int = 5) -> List[Dict]:
    """
    Get top engaged contacts for a client.
    
    Args:
        client_id: Company ID (e.g., 'C001')
        limit: Maximum number of contacts to return
    
    Returns:
        List of contact dictionaries with interaction counts and engagement level
    """
    contacts = get_client_contacts(client_id)
    activities = get_client_activities(client_id, limit=1000)
    
    # Count interactions per contact
    contact_interactions = {}
    for activity in activities:
        contact_id = activity.get('contact_id', '')
        if contact_id:
            if contact_id not in contact_interactions:
                contact_interactions[contact_id] = {
                    'count': 0,
                    'recent_count': 0,
                    'last_activity': None
                }
            contact_interactions[contact_id]['count'] += 1
            
            # Check if recent (last 7 days)
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            if activity.get('timestamp'):
                try:
                    act_date = datetime.fromisoformat(activity['timestamp'].replace('T', ' ').split('.')[0])
                    if act_date >= week_ago:
                        contact_interactions[contact_id]['recent_count'] += 1
                    if not contact_interactions[contact_id]['last_activity'] or act_date > contact_interactions[contact_id]['last_activity']:
                        contact_interactions[contact_id]['last_activity'] = act_date
                except:
                    pass
    
    # Build result with engagement level
    result = []
    for contact in contacts:
        contact_id = contact.get('contact_id', '')
        interactions = contact_interactions.get(contact_id, {'count': 0, 'recent_count': 0})
        
        # Determine engagement level
        if interactions['recent_count'] >= 3:
            engagement_level = 'Hot'
        elif interactions['recent_count'] >= 1 or interactions['count'] >= 2:
            engagement_level = 'Warm'
        else:
            engagement_level = 'Cold'
        
        result.append({
            **contact,
            'interaction_count': interactions['count'],
            'recent_interaction_count': interactions['recent_count'],
            'engagement_level': engagement_level
        })
    
    # Sort by interaction count and return top N
    result.sort(key=lambda x: x['interaction_count'], reverse=True)
    return result[:limit]


def get_all_contacts_with_details(client_id: str) -> List[Dict]:
    """
    Get all contacts for a client with status, channels, and last contacted info.
    
    Args:
        client_id: Company ID (e.g., 'C001')
    
    Returns:
        List of contact dictionaries with full details
    """
    contacts = get_client_contacts(client_id)
    activities = get_client_activities(client_id, limit=1000)
    
    result = []
    for contact in contacts:
        contact_id = contact.get('contact_id', '')
        
        # Get status
        status = get_contact_status(contact, activities)
        
        # Get channels
        channels = get_contact_channels(contact_id, activities)
        
        # Get last contacted
        last_contacted = get_last_contacted(contact_id, activities)
        
        result.append({
            **contact,
            'status': status,
            'channels': channels,
            'last_contacted': last_contacted.isoformat() if last_contacted else None
        })
    
    # Sort by name
    result.sort(key=lambda x: x.get('name', '').lower())
    return result


def get_client_data(client_id: str, filters: Dict = None) -> Dict:
    """
    Get all data for a specific client.
    
    Args:
        client_id: Company ID (e.g., 'C001')
        filters: Optional filters for activities (channel, status, days)
    
    Returns:
        Dictionary containing metrics, activities, contacts, campaigns, summary, top contacts, and contacts_with_details
    """
    return {
        'client_id': client_id,
        'metrics': get_client_metrics(client_id),
        'activities': get_client_activities(client_id, filters=filters),
        'contacts': get_client_contacts(client_id),
        'contacts_with_details': get_all_contacts_with_details(client_id),
        'campaigns': get_client_campaigns(client_id),
        'summary': get_client_summary(client_id),
        'top_contacts': get_top_contacts(client_id)
    }

