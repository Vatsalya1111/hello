# requests/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UpcyclingRequestForm, UserRegisterForm, OfferForm, MessageForm
from .models import UpcyclingRequest, ArtisanProfile, Offer, Conversation, Message
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q

# A simple home page view (optional, but good to have)
def home_page(request):
    return render(request, 'requests/home_page.html')

def is_active_artisan(user):
    return user.is_authenticated and hasattr(user, 'artisan_profile') and user.artisan_profile.is_active_artisan

# View to handle creating an upcycling request
@login_required
def create_upcycling_request(request):
    if request.method == 'POST':
        form = UpcyclingRequestForm(request.POST, request.FILES)
        if form.is_valid():
            upcycling_request = form.save(commit=False)
            upcycling_request.user = request.user
            upcycling_request.save()
            messages.success(request, 'Your upcycling request has been submitted successfully!')
            return redirect('my_requests')
        else:
            pass # Form will be rendered again with errors if invalid
    else:
        form = UpcyclingRequestForm()

    context = {
        'form': form
    }
    return render(request, 'requests/create_upcycling_request.html', context)

# A simple success page view (this is currently not used by create_upcycling_request, can be removed if not needed elsewhere)
def request_success(request):
    return render(request, 'requests/request_success.html')


@login_required
def request_detail(request, request_id):
    upcycling_request = get_object_or_404(UpcyclingRequest, id=request_id)

    offer_form = None
    has_made_offer = False # Flag to track if the current artisan has an offer

    if request.user.is_authenticated:
        # Check if the logged-in user is an active artisan AND not the owner of the request
        if hasattr(request.user, 'artisan_profile') and \
           request.user.artisan_profile.is_active_artisan and \
           request.user != upcycling_request.user:

            # Check if this artisan has already made an offer for this request
            if Offer.objects.filter(request=upcycling_request, artisan=request.user.artisan_profile).exists():
                has_made_offer = True
            else:
                # Only initialize the form if no offer has been made by this artisan
                offer_form = OfferForm()
                print("DEBUG: offer_form initialized successfully!")
        else:
            # If the user is the owner or not an active artisan, ensure offer_form is None
            offer_form = None
            print("DEBUG: Offer form not initialized (user is owner or not active artisan).")

    print(f"DEBUG: Viewing request {upcycling_request.id}, Status: {upcycling_request.status}")
    print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        print(f"DEBUG: User is owner of request: {request.user == upcycling_request.user}")
        if hasattr(request.user, 'artisan_profile'):
            print(f"DEBUG: User has artisan_profile attribute: True")
            print(f"DEBUG: Artisan profile active: {request.user.artisan_profile.is_active_artisan}")
            if request.user.artisan_profile.is_active_artisan:
                print(f"DEBUG: Current artisan has already made offer: {has_made_offer}") # New debug line


    context = {
        'request': upcycling_request,
        'offer_form': offer_form, # This will be None if offer already made or not artisan
        'has_made_offer': has_made_offer, # Pass the flag to the template
    }
    return render(request, 'requests/request_detail.html', context)

@login_required
def my_requests(request):
    user_requests = UpcyclingRequest.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'requests': user_requests
    }
    return render(request, 'requests/my_requests.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = UserRegisterForm()

    context = {
        'form': form
    }
    return render(request, 'requests/register.html', context)

@login_required
@user_passes_test(is_active_artisan, login_url='/accounts/login/')
def artisan_available_requests(request):
    available_requests = UpcyclingRequest.objects.filter(
        status='Request Received',
        accepted_artisan__isnull=True
    ).order_by('-created_at')

    context = {
        'available_requests': available_requests
    }
    return render(request, 'requests/artisan_available_requests.html', context)

@login_required
@user_passes_test(is_active_artisan, login_url='/accounts/login/') # Only active artisans can make offers
@login_required
@user_passes_test(is_active_artisan, login_url='/accounts/login/') # Only active artisans can make offers
def make_offer(request, request_id):
    upcycling_request = get_object_or_404(UpcyclingRequest, id=request_id)

    # Prevent request owner from making an offer on their own request
    if request.user == upcycling_request.user:
        messages.error(request, "You cannot make an offer on your own upcycling request.")
        return redirect('request_detail', request_id=upcycling_request.id)

    print(f"DEBUG (make_offer): Request method: {request.method}") # ADD THIS LINE
    if request.method == 'POST':
        print(f"DEBUG (make_offer): Processing POST request for offer on request ID: {request_id}") # ADD THIS LINE
        form = OfferForm(request.POST)
        if form.is_valid():
            print("DEBUG (make_offer): Form is VALID.") # ADD THIS LINE
            offer = form.save(commit=False)
            offer.request = upcycling_request
            offer.artisan = request.user.artisan_profile # Link to the artisan profile
            offer.status = 'Pending' # Default status for new offers
            offer.save()
            messages.success(request, "Your offer has been submitted successfully!")
            return redirect('request_detail', request_id=upcycling_request.id)
        else:
            print("DEBUG (make_offer): Form is INVALID.") # ADD THIS LINE
            print(f"DEBUG (make_offer): Form errors: {form.errors}") # ADD THIS LINE
            # If form is invalid, re-render the detail page with the form and errors
            offer_form = form # Pass the form with errors
            context = {
                'request': upcycling_request,
                'offer_form': offer_form,
            }
            messages.error(request, "There was an error with your offer submission. Please check the details.")
            return render(request, 'requests/request_detail.html', context)
    # If it's not a POST request to make an offer, it shouldn't hit this view directly
    # It's intended for form submission from request_detail.html
    return redirect('request_detail', request_id=upcycling_request.id)


@login_required
def accept_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    upcycling_request = offer.request

    # Ensure the logged-in user is the owner of the request
    if request.user != upcycling_request.user:
        messages.error(request, "You are not authorized to accept this offer.")
        return redirect('request_detail', request_id=upcycling_request.id)

    # Prevent accepting offers if the request is already accepted/completed
    if upcycling_request.status not in ['Request Received', 'Offer Made', 'Open']: # Added 'Open' to allowed statuses
        messages.error(request, f"This request (status: {upcycling_request.status}) can no longer accept offers.")
        return redirect('request_detail', request_id=upcycling_request.id)

    # Check if the offer is still pending
    if offer.status != 'Pending':
        messages.error(request, "This offer is no longer pending.")
        return redirect('request_detail', request_id=upcycling_request.id)

    # Start a database transaction for atomicity
    with transaction.atomic():
        # 1. Mark the accepted offer as 'Accepted'
        offer.status = 'Accepted'
        offer.save()

        # 2. Update the UpcyclingRequest status and assign the artisan
        upcycling_request.status = 'Offer Accepted'
        upcycling_request.accepted_artisan = offer.artisan.user
        upcycling_request.save()

        # 3. Reject all other pending offers for this request
        Offer.objects.filter(request=upcycling_request, status='Pending').exclude(id=offer.id).update(status='Rejected')

        # Robustly create or get conversation: enforce participant order
        participant1_user, participant2_user = sorted(
            [upcycling_request.user, offer.artisan.user],
            key=lambda u: u.pk # Sort by primary key to ensure consistent order
        )

        conversation, created = Conversation.objects.get_or_create(
            upcycling_request=upcycling_request,
            participant1=participant1_user,
            participant2=participant2_user,
            defaults={} # No extra defaults needed if all fields are part of the lookup
        )

        print(f"DEBUG: Conversation retrieved/created. ID: {conversation.id}, Created: {created}")

        # Add an initial message to the conversation
        initial_message_content = f"Your offer for '{upcycling_request.product_type}' has been accepted! Let's discuss details."
        try:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=initial_message_content
            )
            print(f"DEBUG: Initial message created successfully for conversation ID: {conversation.id}")
        except Exception as e:
            print(f"ERROR: Failed to create initial message: {e}")

    messages.success(request, f"Offer from {offer.artisan.user.username} has been accepted! Request status updated.")
    return redirect('request_detail', request_id=upcycling_request.id)


@login_required
def reject_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    upcycling_request = offer.request

    # Ensure the logged-in user is the owner of the request
    if request.user != upcycling_request.user:
        messages.error(request, "You are not authorized to reject this offer.")
        return redirect('request_detail', request_id=upcycling_request.id)

    # Only allow rejection of pending offers
    if offer.status != 'Pending':
        messages.error(request, "This offer is not pending and cannot be rejected.")
        return redirect('request_detail', request_id=upcycling_request.id)

    # Mark the offer as 'Rejected'
    offer.status = 'Rejected'
    offer.save()
    messages.info(request, f"Offer from {offer.artisan.user.username} has been rejected.")
    return redirect('request_detail', request_id=upcycling_request.id)

# NEW: View to list all conversations for the logged-in user
@login_required
def conversation_list(request):
    # Fetch conversations where the current user is either participant1 or participant2
    conversations = Conversation.objects.filter(
        Q(participant1=request.user) | Q(participant2=request.user)
    ).order_by('-updated_at')

    context = {
        'conversations': conversations
    }
    return render(request, 'requests/conversation_list.html', context)

# NEW: View to display a specific conversation and allow sending messages
@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)
    print(f"DEBUG: Viewing conversation ID: {conversation.id}")

    # Ensure the logged-in user is a participant in this conversation
    if request.user not in [conversation.participant1, conversation.participant2]:
        messages.error(request, "You are not authorized to view this conversation.")
        return redirect('conversation_list')

    # Mark all messages in this conversation sent by the *other* participant as read
    Message.objects.filter(conversation=conversation, is_read=False).exclude(sender=request.user).update(is_read=True)
    print(f"DEBUG: Marked messages as read for conversation ID: {conversation.id}")

    messages_in_conversation = conversation.messages.all().order_by('timestamp') # Fetch and order messages
    print(f"DEBUG: Fetched {messages_in_conversation.count()} messages for conversation ID: {conversation.id}")
    for msg in messages_in_conversation:
        print(f"   DEBUG MESSAGE: Sender: {msg.sender.username}, Content: '{msg.content[:50]}...'")

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            print(f"DEBUG: New message saved! Content: '{message.content[:50]}...'")
            # Update conversation's 'updated_at' timestamp
            conversation.save()
            return redirect('conversation_detail', conversation_id=conversation.id)
        else:
            print(f"ERROR: Message form not valid: {form.errors}")
    else:
        form = MessageForm()

    context = {
        'conversation': conversation,
        'messages_in_conversation': messages_in_conversation,
        'form': form,
        'other_participant': conversation.participant1 if request.user == conversation.participant2 else conversation.participant2
    }
    return render(request, 'requests/conversation_detail.html', context)