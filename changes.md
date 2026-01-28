# YouTube Upload Implementation Changes

**Date:** January 28, 2026

This document outlines the refactoring and improvements made to the YouTube video upload feature in the Spoken Tutorial project. These changes aim to improve security, error handling, production readiness, and maintainability.

## 1. Configuration (`spoken/config.py`)

**Role Management:** Upload permissions are now centrally managed via a configuration setting rather than hardcoded group names in views.

```python
# spoken/config.py

YOUTUBE_UPLOAD_ROLES = [
    "YouTube Admin",
]
```

## 2. Access Control (`youtube/utils.py`, `youtube/views.py`)

**Role-Based Access:** Replaced implicit checks with a dedicated helper function.

**Helper Function (`youtube/utils.py`):**
```python
def user_can_upload_to_youtube(user):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name__in=config.YOUTUBE_UPLOAD_ROLES).exists()
```

**View Enforcement (`youtube/views.py`):**
The `add_youtube_video` view immediately checks permissions before processing any logic.
```python
@login_required
def add_youtube_video(request):
    if not user_can_upload_to_youtube(request.user):
        return HttpResponseForbidden("You are not authorized to upload videos.")
    # ...
```

## 3. Core API Logic (`youtube/core.py`)

**Standardized Return Types:** `upload_video` now consistently returns a dictionary (e.g., `{'id': 'xyz'}` or `{'error': '...'}`) instead of mixing strings and `None`.

```python
def upload_video(service, options):
    try:
        # ... upload logic ...
        response = resumable_upload(insert_request)
        return response # Returns dict
    except Exception as e:
        return {'error': str(e)}
```

**Dynamic OAuth Redirects:**
Functions now accept a `redirect_uri` argument to support dynamic host matching (fixing `redirect_uri_mismatch` on local/different environments).

```python
def get_flow(redirect_uri=None):
    flow = oauth2client.client.flow_from_clientsecrets(...)
    # Use provided URI or fallback to settings
    flow.redirect_uri = redirect_uri or settings.YOUTUBE_REDIRECT_URL
    # ...
    return flow

def get_auth_url(redirect_uri=None):
    flow = get_flow(redirect_uri)
    return flow.step1_get_authorize_url()
```

**Path Fixes:**
Corrected the client secret path reference.
```python
# was: .client_secrets.json (hidden, plural)
# now: client_secret.json (standard)
client_secrets_file = os.path.join(settings.BASE_DIR, 'youtube', 'client_secret.json')
```

## 4. Views & UX (`youtube/views.py`)

**Workflow Refactoring:** `add_youtube_video` is structured into clear blocks:

1.  **Data Extraction:** Resolves form data.
2.  **File Resolution:** Finds the video file on disk.
3.  **Authentication:** Checks credentials or prompts for auth.
4.  **Upload:** Calls API and handles errors.

**Graceful Auth Handling:**
Instead of crashing, the view generates a dynamic authorization link using the current request's host.

```python
# If not authenticated
redirect_uri = request.build_absolute_uri(reverse('youtube:auth_return'))
auth_url = get_auth_url(redirect_uri)
messages.error(request, mark_safe(f'YouTube credentials not found. <a href="{auth_url}">Click here to authorize</a>.'))
```

**Robust Response Handling:**
Handles the standardized dictionary response from `core.py`.

```python
result = upload_video(service, options)

if 'error' in result:
    raise Exception(f"YouTube API Error: {result['error']}")

if 'id' in result:
    resource.video_id = result['id']
    resource.is_on_youtube = True
    resource.save()
```

**Auth Callback (`auth_return`):**
Matches the redirect URI used during the initial request to complete the OAuth flow successfully.

```python
def auth_return(request):
    code = request.GET.get('code', '')
    if code:
        # Must match the URI used to generate the auth URL
        redirect_uri = request.build_absolute_uri(reverse('youtube:auth_return'))
        store_youtube_credential(code, redirect_uri)
        # ...
```

## 5. Forms (`youtube/forms.py`)

**Dynamic Validation:**
Overrides `__init__` to allow validation of tutorials populated via AJAX, preventing "Select a valid choice" errors during POST.

```python
def __init__(self, *args, **kwargs):
    super(YouTubeUploadForm, self).__init__(*args, **kwargs)
    if self.data.get('tutorial'):
        # Allow checking against all objects since the specific subset 
        # is only known on the frontend via AJAX
        self.fields['tutorial'].queryset = TutorialResource.objects.all()
        self.fields['tutorial'].widget.attrs.pop('disabled', None)
```

## 6. Background Tasks (`youtube/tasks.py`)

**Compatibility Update:**
Updated the legacy background task to handle the dictionary return type from `upload_video`.

```python
response = upload_video(service, options)
video_id = response.get('id') if response else None

if video_id:
    tresource.video_id = video_id
    # ...
```
